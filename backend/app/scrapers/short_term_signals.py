"""短线涨停/炸板等信号采集与解析。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal
from typing import Any, Callable, Awaitable

from app.domain.theme_insights import normalize_stock_code

FetchLimitPools = Callable[[date], Awaitable[dict[str, list[dict[str, Any]]]]]


@dataclass
class SourceResult:
    success: bool
    items: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    source: str = "short_term_signals"


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").strip()
        if not value or value in {"-", "--"}:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _decimal(value: Any) -> Decimal | None:
    number = _number(value)
    if number is None:
        return None
    return Decimal(str(number))


def _parse_time(value: Any) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    if not text or text in {"-", "--"}:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return time.fromisoformat(text if fmt == "%H:%M:%S" and text.count(":") == 2 else text)
        except ValueError:
            continue
    parts = text.split(":")
    try:
        if len(parts) >= 2:
            return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except ValueError:
        return None
    return None


def parse_limit_pool_row(
    row: dict[str, Any],
    *,
    trade_date: date,
    signal_type: str,
    source: str = "akshare",
) -> dict[str, Any] | None:
    code = normalize_stock_code(
        str(row.get("code") or row.get("股票代码") or row.get("代码") or "")
    )
    if not code:
        return None

    is_failed = signal_type == "failed_limit_up" or bool(row.get("is_failed"))
    is_one_word = signal_type == "one_word_limit_up" or bool(
        row.get("is_one_word") or row.get("一字板")
    )
    streak = int(_number(row.get("streak_days") or row.get("连板数") or row.get("连续涨停天数")) or 0)
    if signal_type == "second_limit_up" and streak < 2:
        streak = 2
    if signal_type in {"limit_up", "first_limit_up", "one_word_limit_up"} and streak < 1:
        streak = 1

    return {
        "trade_date": trade_date,
        "stock_code": code,
        "stock_name": row.get("name") or row.get("名称") or row.get("股票简称"),
        "signal_type": signal_type,
        "limit_up_order": int(_number(row.get("limit_up_order") or row.get("封板顺序")) or 0)
        or None,
        "first_limit_up_at": _parse_time(
            row.get("first_limit_up_at") or row.get("首次封板时间") or row.get("首次涨停时间")
        ),
        "last_limit_up_at": _parse_time(
            row.get("last_limit_up_at") or row.get("最后封板时间") or row.get("最终涨停时间")
        ),
        "open_board_count": int(
            _number(row.get("open_board_count") or row.get("开板次数") or 0) or 0
        ),
        "streak_days": streak,
        "is_one_word": is_one_word,
        "is_failed": is_failed,
        "price": _decimal(row.get("price") or row.get("最新价") or row.get("收盘价")),
        "turnover_rate": _decimal(row.get("turnover_rate") or row.get("换手率")),
        "amount": _decimal(row.get("amount") or row.get("成交额")),
        "market_cap": _decimal(row.get("market_cap") or row.get("总市值")),
        "float_market_cap": _decimal(row.get("float_market_cap") or row.get("流通市值")),
        "source": source,
        "source_payload": row,
    }


def parse_limit_pools(
    pools: dict[str, list[dict[str, Any]]],
    *,
    trade_date: date,
    source: str = "akshare",
) -> list[dict[str, Any]]:
    """pools keys: limit_up / failed_limit_up / one_word_limit_up / near_limit_up."""
    type_map = {
        "limit_up": "limit_up",
        "failed_limit_up": "failed_limit_up",
        "one_word_limit_up": "one_word_limit_up",
        "near_limit_up": "near_limit_up",
        "first_limit_up": "first_limit_up",
        "second_limit_up": "second_limit_up",
    }
    items: list[dict[str, Any]] = []
    for key, rows in pools.items():
        signal_type = type_map.get(key)
        if not signal_type:
            continue
        for row in rows:
            parsed = parse_limit_pool_row(
                row, trade_date=trade_date, signal_type=signal_type, source=source
            )
            if parsed:
                items.append(parsed)
    return items


class ShortTermSignalScraper:
    """可注入 fetch 的涨停池采集器；默认使用 AkShare。"""

    def __init__(self, fetch_pools: FetchLimitPools | None = None):
        if fetch_pools is None:
            from app.scrapers.akshare_short_term import fetch_limit_pools

            fetch_pools = fetch_limit_pools
        self._fetch_pools = fetch_pools

    async def fetch(self, trade_date: date) -> SourceResult:
        try:
            pools = await self._fetch_pools(trade_date)
            items = parse_limit_pools(pools, trade_date=trade_date, source="akshare")
            if not items:
                return SourceResult(
                    success=False,
                    error="涨停池解析后无有效记录",
                    source="short_term_signals",
                )
            return SourceResult(success=True, items=items, source="short_term_signals")
        except Exception as exc:  # noqa: BLE001 — 采集层捕获后降级
            return SourceResult(
                success=False,
                error=str(exc),
                source="short_term_signals",
            )
