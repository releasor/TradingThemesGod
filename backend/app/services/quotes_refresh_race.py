"""题材行情多源竞速：并行采集，仅胜出源落库一次。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QuotesRaceResult:
    source: str
    trade_date: date | None
    themes: list[dict[str, Any]]
    updated_count: int


async def race_theme_quotes(
    collectors: list[tuple[str, Callable[[], Awaitable[tuple[date | None, list[dict]]]]]],
    save: Callable[[list[dict]], Awaitable[None]],
    *,
    min_count: int = 1,
    cancel_event: asyncio.Event | None = None,
) -> QuotesRaceResult:
    """并行启动多源采集；首个有效结果胜出并唯一落库。

    失败 / 空结果 / 低于 ``min_count`` 的源被跳过。
    若在落库前 ``cancel_event`` 已置位，则不落库并抛出 ``CancelledError``。
    全部源失败时抛出 ``RuntimeError``。
    """
    if not collectors:
        raise RuntimeError("all quote collectors failed: no collectors")

    tasks: dict[asyncio.Task[tuple[date | None, list[dict]]], str] = {}
    for name, collector in collectors:
        task = asyncio.create_task(collector(), name=name)
        tasks[task] = name

    pending: set[asyncio.Task[tuple[date | None, list[dict]]]] = set(tasks)
    failures: list[str] = []

    try:
        while pending:
            if cancel_event is not None and cancel_event.is_set():
                raise asyncio.CancelledError()

            wait_set: set[asyncio.Future[Any]] = set(pending)
            cancel_waiter: asyncio.Task[bool] | None = None
            if cancel_event is not None:
                cancel_waiter = asyncio.create_task(cancel_event.wait())
                wait_set.add(cancel_waiter)

            done, _ = await asyncio.wait(
                wait_set, return_when=asyncio.FIRST_COMPLETED
            )

            if cancel_waiter is not None:
                if cancel_waiter in done:
                    raise asyncio.CancelledError()
                cancel_waiter.cancel()
                try:
                    await cancel_waiter
                except asyncio.CancelledError:
                    pass

            finished = {task for task in done if task in pending}
            pending -= finished

            for task in finished:
                name = tasks[task]
                try:
                    trade_date, themes = task.result()
                except Exception as exc:
                    failures.append(f"{name}: {exc}")
                    logger.warning(
                        "quotes_race_collector_failed",
                        source=name,
                        error=str(exc),
                    )
                    continue

                theme_count = len(themes) if themes else 0
                if theme_count < min_count:
                    failures.append(
                        f"{name}: empty or below min_count ({theme_count})"
                    )
                    logger.info(
                        "quotes_race_collector_skipped",
                        source=name,
                        theme_count=theme_count,
                        min_count=min_count,
                    )
                    continue

                for other in pending:
                    other.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                pending.clear()

                if cancel_event is not None and cancel_event.is_set():
                    raise asyncio.CancelledError()

                await save(themes)
                logger.info(
                    "quotes_race_winner",
                    source=name,
                    updated_count=theme_count,
                    trade_date=str(trade_date) if trade_date else None,
                )
                return QuotesRaceResult(
                    source=name,
                    trade_date=trade_date,
                    themes=themes,
                    updated_count=theme_count,
                )

        detail = "; ".join(failures) if failures else "no valid results"
        raise RuntimeError(f"all quote collectors failed: {detail}")
    finally:
        for task in pending:
            if not task.done():
                task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
