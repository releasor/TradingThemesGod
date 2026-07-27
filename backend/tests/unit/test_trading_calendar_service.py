"""TradingCalendar 开市日解析与周末/节假日回退。"""

from datetime import date

from app.services.trading_calendar import TradingCalendar


def setup_function():
    TradingCalendar.clear()


def test_resolve_holiday_monday_rolls_to_prior_friday():
    TradingCalendar.load_dates(
        {
            date(2026, 9, 30),
            date(2026, 10, 8),
            date(2026, 10, 9),
        }
    )
    assert TradingCalendar.resolve(date(2026, 10, 5)) == date(2026, 9, 30)
    assert TradingCalendar.is_trade_day(date(2026, 10, 5)) is False
    assert TradingCalendar.previous_trade_day(date(2026, 10, 8)) == date(2026, 9, 30)


def test_resolve_weekend_with_calendar():
    TradingCalendar.load_dates({date(2026, 7, 24), date(2026, 7, 27)})
    assert TradingCalendar.resolve(date(2026, 7, 25)) == date(2026, 7, 24)


def test_empty_calendar_weekend_fallback_degraded():
    TradingCalendar.clear()
    assert TradingCalendar.resolve(date(2026, 7, 26)) == date(2026, 7, 24)
    assert TradingCalendar.degraded is True


def test_list_trade_days_in_range():
    TradingCalendar.load_dates(
        {date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24), date(2026, 7, 27)}
    )
    assert TradingCalendar.list_trade_days(date(2026, 7, 23), date(2026, 7, 27)) == [
        date(2026, 7, 23),
        date(2026, 7, 24),
        date(2026, 7, 27),
    ]


def test_next_trade_day():
    TradingCalendar.load_dates({date(2026, 9, 30), date(2026, 10, 8)})
    assert TradingCalendar.next_trade_day(date(2026, 9, 30)) == date(2026, 10, 8)
