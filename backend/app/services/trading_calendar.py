"""进程内 A 股交易日历：开市日集合与 resolve/previous/next。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _shanghai_today() -> date:
    return datetime.now(_SHANGHAI).date()


def _weekend_fallback(value: date) -> date:
    resolved = value
    while resolved.weekday() >= 5:
        resolved -= timedelta(days=1)
    return resolved


class TradingCalendar:
    """开市日内存索引。空集时 degraded，resolve 仅做周末回退。"""

    _days: frozenset[date] = frozenset()
    _min: date | None = None
    _max: date | None = None
    degraded: bool = True

    @classmethod
    def clear(cls) -> None:
        cls._days = frozenset()
        cls._min = None
        cls._max = None
        cls.degraded = True

    @classmethod
    def load_dates(cls, days: set[date] | frozenset[date]) -> None:
        frozen = frozenset(days)
        cls._days = frozen
        cls._min = min(frozen) if frozen else None
        cls._max = max(frozen) if frozen else None
        cls.degraded = not bool(frozen)

    @classmethod
    def is_trade_day(cls, d: date) -> bool:
        if cls._days:
            return d in cls._days
        return d.weekday() < 5

    @classmethod
    def resolve(cls, trade_date: date | None = None) -> date:
        base = trade_date or _shanghai_today()
        if cls._days:
            steps = 0
            cursor = base
            while cursor not in cls._days and steps < 400:
                if cls._min is not None and cursor < cls._min - timedelta(days=14):
                    break
                cursor -= timedelta(days=1)
                steps += 1
            if cursor in cls._days:
                return cursor
        return _weekend_fallback(base)

    @classmethod
    def previous_trade_day(cls, d: date) -> date:
        """严格小于 d 的最近开市日。"""
        cursor = d - timedelta(days=1)
        if cls._days:
            steps = 0
            while cursor not in cls._days and steps < 400:
                if cls._min is not None and cursor < cls._min - timedelta(days=14):
                    break
                cursor -= timedelta(days=1)
                steps += 1
            if cursor in cls._days:
                return cursor
        return _weekend_fallback(cursor)

    @classmethod
    def next_trade_day(cls, d: date) -> date:
        """严格大于 d 的最近开市日。"""
        cursor = d + timedelta(days=1)
        if cls._days:
            steps = 0
            while cursor not in cls._days and steps < 400:
                if cls._max is not None and cursor > cls._max + timedelta(days=14):
                    break
                cursor += timedelta(days=1)
                steps += 1
            if cursor in cls._days:
                return cursor
        while cursor.weekday() >= 5:
            cursor += timedelta(days=1)
        return cursor

    @classmethod
    def list_trade_days(cls, start: date, end: date) -> list[date]:
        if start > end:
            return []
        if cls._days:
            return sorted(x for x in cls._days if start <= x <= end)
        out: list[date] = []
        cur = start
        while cur <= end:
            if cur.weekday() < 5:
                out.append(cur)
            cur += timedelta(days=1)
        return out
