"""龙虎榜采集与解析。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Awaitable, Callable

from app.domain.theme_insights import normalize_stock_code

FetchDragonTiger = Callable[[date], Awaitable[list[dict[str, Any]]]]


@dataclass
class SourceResult:
    success: bool
    items: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    source: str = "dragon_tiger"


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


def parse_dragon_tiger_row(
    row: dict[str, Any],
    *,
    trade_date: date,
    source: str = "akshare",
) -> dict[str, Any] | None:
    code = normalize_stock_code(
        str(row.get("code") or row.get("股票代码") or row.get("代码") or "")
    )
    if not code:
        return None
    reason = str(row.get("reason") or row.get("上榜原因") or row.get("解读") or "").strip()
    buy = _decimal(row.get("buy_amount") or row.get("买入额") or row.get("龙虎榜买入额"))
    sell = _decimal(row.get("sell_amount") or row.get("卖出额") or row.get("龙虎榜卖出额"))
    net = _decimal(row.get("net_amount") or row.get("净买额") or row.get("龙虎榜净买额"))
    if net is None and buy is not None and sell is not None:
        net = buy - sell
    return {
        "trade_date": trade_date,
        "stock_code": code,
        "stock_name": row.get("name") or row.get("名称") or row.get("股票简称"),
        "reason": reason or "未注明",
        "buy_amount": buy,
        "sell_amount": sell,
        "net_amount": net,
        "seat_summary": row.get("seat_summary") or row.get("席位") or row.get("营业部"),
        "source": source,
        "source_payload": row,
    }


def parse_dragon_tiger_rows(
    rows: list[dict[str, Any]],
    *,
    trade_date: date,
    source: str = "akshare",
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        parsed = parse_dragon_tiger_row(row, trade_date=trade_date, source=source)
        if parsed:
            items.append(parsed)
    return items


class DragonTigerScraper:
    """可注入 fetch 的龙虎榜采集器；默认使用 AkShare。"""

    def __init__(self, fetch_entries: FetchDragonTiger | None = None):
        if fetch_entries is None:
            from app.scrapers.akshare_short_term import fetch_dragon_tiger_entries

            fetch_entries = fetch_dragon_tiger_entries
        self._fetch_entries = fetch_entries

    async def fetch(self, trade_date: date) -> SourceResult:
        try:
            rows = await self._fetch_entries(trade_date)
            items = parse_dragon_tiger_rows(rows, trade_date=trade_date, source="akshare")
            if not items:
                return SourceResult(
                    success=False,
                    error="龙虎榜解析后无有效记录",
                    source="dragon_tiger",
                )
            return SourceResult(success=True, items=items, source="dragon_tiger")
        except Exception as exc:  # noqa: BLE001
            return SourceResult(success=False, error=str(exc), source="dragon_tiger")
