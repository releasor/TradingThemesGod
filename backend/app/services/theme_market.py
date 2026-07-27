"""题材成分股市场广度与涨跌停快照服务。"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.theme_insights import MarketCounts, classify_market_counts
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
                theme.id,
                trade_date,
                counts,
                calculated_at,
                rise_fall_pct=theme.rise_fall_pct,
            )
        await self.session.commit()
        return len(themes)

    async def upsert_board_quotes(self, codes: set[str], trade_date: date) -> int:
        """写入或更新指定题材在交易日的板块涨跌幅。"""
        themes = await self.themes.list_by_codes(codes)
        if not themes:
            return 0
        calculated_at = datetime.now(UTC)
        empty_counts = MarketCounts(0, 0, 0, 0, None, None)
        for theme in themes:
            rise_fall_pct = (
                Decimal(theme.rise_fall_pct)
                if theme.rise_fall_pct is not None
                else None
            )
            snapshot = await self.insights.get_snapshot(theme.id, trade_date)
            if snapshot is None:
                await self.insights.upsert_snapshot(
                    theme.id,
                    trade_date,
                    empty_counts,
                    calculated_at,
                    rise_fall_pct=rise_fall_pct,
                )
                continue
            if rise_fall_pct is not None:
                snapshot.rise_fall_pct = rise_fall_pct
            snapshot.calculated_at = calculated_at
            self.session.add(snapshot)
        await self.session.commit()
        return len(themes)

    async def refresh_for_theme_codes(self, codes: set[str], trade_date: date) -> int:
        """仅刷新指定题材代码的市场快照。"""
        limit_up, limit_down = await self.limit_pool.fetch(trade_date)
        themes = await self.themes.list_with_stock_quotes_by_codes(codes)
        calculated_at = datetime.now(UTC)
        # 历史日只用成分股涨跌家数；themes.rise_fall_pct 是最新行情，不能回填到旧交易日。
        use_live_quote = trade_date == date.today()
        for theme in themes:
            stocks = [link.stock for link in theme.stocks]
            counts = classify_market_counts(stocks, limit_up, limit_down)
            await self.insights.upsert_snapshot(
                theme.id,
                trade_date,
                counts,
                calculated_at,
                rise_fall_pct=theme.rise_fall_pct if use_live_quote else None,
            )
        await self.session.commit()
        return len(themes)
