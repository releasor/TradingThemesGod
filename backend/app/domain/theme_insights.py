"""题材洞察领域纯数据结构与计算函数。"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any, Protocol
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class MarketCounts:
    up_count: int
    down_count: int
    flat_count: int
    suspended_count: int
    limit_up_count: int | None
    limit_down_count: int | None


class StockQuote(Protocol):
    code: str
    rise_fall_pct: Decimal | None


def normalize_stock_code(value: object) -> str:
    code = str(value).strip().split(".")[-1]
    return code.zfill(6)


def classify_market_counts(
    stocks: Iterable[StockQuote],
    limit_up_codes: set[str] | None,
    limit_down_codes: set[str] | None,
) -> MarketCounts:
    up_count = down_count = flat_count = suspended_count = 0
    codes: set[str] = set()
    for stock in stocks:
        codes.add(normalize_stock_code(stock.code))
        change = stock.rise_fall_pct
        if change is None:
            suspended_count += 1
        elif change > 0:
            up_count += 1
        elif change < 0:
            down_count += 1
        else:
            flat_count += 1
    return MarketCounts(
        up_count=up_count,
        down_count=down_count,
        flat_count=flat_count,
        suspended_count=suspended_count,
        limit_up_count=(
            len(codes & limit_up_codes) if limit_up_codes is not None else None
        ),
        limit_down_count=(
            len(codes & limit_down_codes) if limit_down_codes is not None else None
        ),
    )


def deduplicate_event_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按规范化标题和发布日期合并同一事件的多来源重复记录。"""
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        published_at = event.get("published_at")
        if not isinstance(published_at, datetime):
            unique.append(event)
            continue
        key = build_event_key(str(event.get("title", "")), published_at)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def build_event_key(title: str, published_at: datetime) -> str:
    """生成跨来源、跨刷新稳定的题材事件键。"""
    normalized_title = "".join(
        character.lower() for character in title if character.isalnum()
    )
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    publication_date = published_at.astimezone(ZoneInfo("Asia/Shanghai")).date()
    payload = f"{normalized_title}|{publication_date.isoformat()}"
    return sha256(payload.encode("utf-8")).hexdigest()
