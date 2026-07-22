"""题材成分股市场广度与涨跌停快照服务。"""

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.theme_insights import classify_market_counts
from app.integrations.market.limit_pool import LimitPoolProvider
from app.repositories.theme import ThemeRepository
from app.repositories.theme_insight import ThemeInsightRepository


class ThemeMarketService:
    def __init__(
        self,
        session: AsyncSession,
        themes: ThemeRepository | None = None,
        insights: ThemeInsightRepository | None = None,
        limit_pool: LimitPoolProvider | None = None,
    ):
        self.session = session
        self.themes = themes or ThemeRepository(session)
        self.insights = insights or ThemeInsightRepository(session)
        self.limit_pool = limit_pool or LimitPoolProvider()

    async def refresh_all(self, trade_date: date) -> int:
        limit_up, limit_down = await self.limit_pool.fetch(trade_date)
        themes = await self.themes.list_with_stock_quotes()
        calculated_at = datetime.now(UTC)
        for theme in themes:
            stocks = [link.stock for link in theme.stocks]
            counts = classify_market_counts(stocks, limit_up, limit_down)
            await self.insights.upsert_snapshot(
                theme.id, trade_date, counts, calculated_at
            )
        await self.session.commit()
        return len(themes)
