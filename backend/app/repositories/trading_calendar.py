"""交易日历仓储。"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trading_calendar import TradingCalendarDay, TradingCalendarMeta

META_ID = 1
DEFAULT_SOURCE = "akshare_sina"


class TradingCalendarRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_meta_row(self) -> TradingCalendarMeta:
        row = await self.session.get(TradingCalendarMeta, META_ID)
        if row is not None:
            return row
        row = TradingCalendarMeta(id=META_ID, source=DEFAULT_SOURCE, row_count=0)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_meta(self) -> TradingCalendarMeta | None:
        return await self.session.get(TradingCalendarMeta, META_ID)

    async def list_all_dates(self) -> list[date]:
        result = await self.session.scalars(
            select(TradingCalendarDay.trade_date).order_by(TradingCalendarDay.trade_date.asc())
        )
        return list(result.all())

    async def replace_all(self, dates: list[date], *, source: str = DEFAULT_SOURCE) -> int:
        await self.session.execute(delete(TradingCalendarDay))
        now = datetime.now(timezone.utc)
        self.session.add_all(
            [
                TradingCalendarDay(trade_date=d, source=source, synced_at=now)
                for d in dates
            ]
        )
        await self.session.flush()
        return len(dates)

    async def upsert_meta(
        self,
        *,
        source: str = DEFAULT_SOURCE,
        last_synced_at: datetime | None = None,
        row_count: int = 0,
        min_date: date | None = None,
        max_date: date | None = None,
        last_error: str | None = None,
        clear_error: bool = False,
    ) -> TradingCalendarMeta:
        row = await self.ensure_meta_row()
        row.source = source
        row.row_count = row_count
        row.min_date = min_date
        row.max_date = max_date
        row.updated_at = datetime.now(timezone.utc)
        if last_synced_at is not None:
            row.last_synced_at = last_synced_at
        if clear_error:
            row.last_error = None
        elif last_error is not None:
            row.last_error = last_error
        await self.session.flush()
        return row
