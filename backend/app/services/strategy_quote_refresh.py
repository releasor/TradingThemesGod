"""策略卡题材行情刷新：多源并行竞速，仅胜出源落库。"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import akshare as ak

from app.core.config import get_settings
from app.core.logging import get_logger
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.eastmoney import EastMoneyScraper
from app.services.quotes_refresh_race import race_theme_quotes

logger = get_logger(__name__)

EASTMONEY_QUOTE_TIMEOUT_SECONDS = 18
AKSHARE_QUOTE_TIMEOUT_SECONDS = 18
OVERALL_QUOTE_TIMEOUT_SECONDS = 22
MIN_QUOTE_SUCCESS_COUNT = 1


@dataclass(frozen=True)
class StrategyQuoteRefreshResult:
    trade_date: date
    source: str
    elapsed_ms: int
    attempts: tuple[str, ...] = field(default_factory=tuple)
    updated_count: int = 0


def _normalize_board_code(code: str) -> str:
    value = str(code).strip().upper()
    return value if value.startswith("BK") else f"BK{value}"


def _parse_akshare_themes(
    frame: Any, codes: set[str] | None = None
) -> list[dict[str, Any]]:
    """解析 AKShare 概念板块行情。

    ``codes`` 为 None 时解析全部行（全量题材）；否则仅保留指定代码子集。
    """
    normalized = (
        {_normalize_board_code(code) for code in codes} if codes is not None else None
    )
    themes: list[dict[str, Any]] = []
    code_column = "板块代码" if "板块代码" in frame.columns else None
    if code_column is None:
        return themes

    for _, row in frame.iterrows():
        code = _normalize_board_code(row[code_column])
        if normalized is not None and code not in normalized:
            continue
        name = str(row.get("板块名称", "")).strip()
        if not name:
            continue
        rise_fall_pct = row.get("涨跌幅")
        heat_index = row.get("换手率")
        up_count = row.get("上涨家数")
        stock_count = None
        if up_count is not None:
            try:
                down_count = int(row.get("下跌家数") or 0)
                stock_count = int(up_count) + down_count
            except (TypeError, ValueError):
                stock_count = None
        themes.append(
            {
                "name": name,
                "code": code,
                "heat_index": _to_optional_decimal(heat_index),
                "rise_fall_pct": _to_optional_decimal(rise_fall_pct),
                "stock_count": stock_count,
                "category": None,
                "source": "akshare",
            }
        )
    return themes


def _to_optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except Exception:
        return None


async def collect_akshare_theme_quotes(
    only_codes: set[str] | None = None,
    *,
    timeout_seconds: float = AKSHARE_QUOTE_TIMEOUT_SECONDS,
) -> tuple[date | None, list[dict[str, Any]]]:
    """仅采集 AKShare 题材行情草稿，不落库。

    ``only_codes`` 为 None 时解析接口返回的全部板块（全量题材竞速）；
    传入集合时仅保留策略卡等子集。
    """
    frame = await asyncio.wait_for(
        asyncio.to_thread(ak.stock_board_concept_name_em),
        timeout=timeout_seconds,
    )
    themes = _parse_akshare_themes(frame, only_codes)
    if not themes:
        return None, []
    return date.today(), themes


def _fetch_board_last_rise(symbol: str) -> Decimal | None:
    """拉取板块日 K 最近一根的涨跌幅（盘后列表接口常为 0 时的回退）。"""
    end = date.today()
    start = end.fromordinal(end.toordinal() - 12)
    frame = ak.stock_board_concept_hist_em(
        symbol=symbol,
        period="daily",
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        adjust="",
    )
    if frame is None or getattr(frame, "empty", True):
        return None
    if "涨跌幅" not in getattr(frame, "columns", []):
        return None
    value = frame.iloc[-1].get("涨跌幅")
    return _to_optional_decimal(value)


async def backfill_signal_board_quotes_from_hist(
    *,
    concurrency: int = 4,
) -> int:
    """为行情指标/市场表现板回填最近交易日涨跌幅（全源同 code）。

    东财概念列表盘后常返回全 0，但日 K 仍有昨收涨跌幅。
    """
    from sqlalchemy import or_, select

    from app.core.database import AsyncSessionLocal
    from app.domain.theme_classification import (
        only_indicator_signals,
        only_market_signals,
    )
    from app.models.theme import Theme
    from app.scrapers.theme_upsert import apply_theme_quotes

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(Theme.code, Theme.name)
                .where(
                    Theme.deleted_at.is_(None),
                    or_(only_market_signals(), only_indicator_signals()),
                )
                .distinct()
            )
        ).all()

    targets = [(str(code), str(name or "")) for code, name in rows if code]
    if not targets:
        return 0

    sem = asyncio.Semaphore(concurrency)
    quotes: list[dict[str, Any]] = []

    async def one(code: str, name: str) -> None:
        async with sem:
            rise = None
            for symbol in (code, name):
                if not symbol:
                    continue
                try:
                    rise = await asyncio.to_thread(_fetch_board_last_rise, symbol)
                except Exception as exc:
                    logger.warning(
                        "signal_board_hist_failed",
                        code=code,
                        symbol=symbol,
                        error=str(exc),
                    )
                    continue
                if rise is not None and rise != 0:
                    break
            if rise is None:
                return
            quotes.append(
                {
                    "code": code,
                    "name": name or code,
                    "rise_fall_pct": rise,
                    "source": "akshare",
                }
            )

    await asyncio.gather(*(one(code, name) for code, name in targets))
    if not quotes:
        return 0
    return await apply_theme_quotes(quotes, preserve_nonzero_when_batch_zero=False)


async def _collect_via_eastmoney(
    codes: set[str],
) -> tuple[date | None, list[dict[str, Any]]]:
    settings = get_settings()
    middleware = AntiScrapingMiddleware(
        proxy_url=settings.PROXY_URL if settings.PROXY_ENABLED else None,
        min_interval=0.2,
        max_interval=0.6,
        max_retries=1,
    )
    scraper = EastMoneyScraper(middleware=middleware)
    try:
        return await asyncio.wait_for(
            scraper.collect_theme_quotes(only_codes=codes),
            timeout=EASTMONEY_QUOTE_TIMEOUT_SECONDS,
        )
    finally:
        await scraper.close()


async def _collect_via_akshare(
    codes: set[str],
) -> tuple[date | None, list[dict[str, Any]]]:
    return await collect_akshare_theme_quotes(only_codes=codes)


async def refresh_strategy_quotes(codes: set[str]) -> StrategyQuoteRefreshResult:
    """按优先级刷新策略题材行情，并记录耗时与数据源。"""
    try:
        return await asyncio.wait_for(
            _refresh_strategy_quotes_inner(codes),
            timeout=OVERALL_QUOTE_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        raise RuntimeError(
            f"题材行情刷新超时（>{OVERALL_QUOTE_TIMEOUT_SECONDS} 秒），已回退数据库数据"
        ) from exc


async def _refresh_strategy_quotes_inner(
    codes: set[str],
) -> StrategyQuoteRefreshResult:
    started = time.monotonic()
    normalized_codes = {_normalize_board_code(code) for code in codes}
    attempts = ("eastmoney", "akshare")

    settings = get_settings()
    middleware = AntiScrapingMiddleware(
        proxy_url=settings.PROXY_URL if settings.PROXY_ENABLED else None,
        min_interval=0.2,
        max_interval=0.6,
        max_retries=1,
    )
    scraper = EastMoneyScraper(middleware=middleware)

    async def save(themes: list[dict[str, Any]]) -> None:
        from app.scrapers.theme_upsert import apply_theme_quotes

        await apply_theme_quotes(themes)

    try:
        result = await race_theme_quotes(
            collectors=[
                ("eastmoney", lambda: _collect_via_eastmoney(normalized_codes)),
                ("akshare", lambda: _collect_via_akshare(normalized_codes)),
            ],
            save=save,
            min_count=MIN_QUOTE_SUCCESS_COUNT,
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "strategy_quote_refresh_success",
            source=result.source,
            elapsed_ms=elapsed_ms,
            updated_count=result.updated_count,
        )
        return StrategyQuoteRefreshResult(
            trade_date=result.trade_date or date.today(),
            source=result.source,
            elapsed_ms=elapsed_ms,
            attempts=attempts,
            updated_count=result.updated_count,
        )
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.warning(
            "strategy_quote_refresh_failed",
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
        attempts_text = "、".join(attempts)
        raise RuntimeError(
            f"题材行情刷新失败（已尝试 {attempts_text}，耗时 {elapsed_ms / 1000:.1f} 秒），"
            f"已回退数据库数据"
        ) from exc
    finally:
        await scraper.close()
