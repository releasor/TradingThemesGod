"""trading_calendar ORM 表名与约束。"""

from app.models.trading_calendar import TradingCalendarDay, TradingCalendarMeta


def test_day_tablename_and_pk():
    assert TradingCalendarDay.__tablename__ == "trading_calendar_days"
    cols = {c.name for c in TradingCalendarDay.__table__.columns}
    assert {"trade_date", "source", "synced_at"} <= cols


def test_meta_tablename():
    assert TradingCalendarMeta.__tablename__ == "trading_calendar_meta"
    cols = {c.name for c in TradingCalendarMeta.__table__.columns}
    assert {"id", "last_synced_at", "row_count", "min_date", "max_date", "last_error"} <= cols
