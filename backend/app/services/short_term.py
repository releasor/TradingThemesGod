"""短线机会雷达服务。"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.theme_classification import exclude_market_signals
from app.models.theme import Theme
from app.models.theme_market_snapshot import ThemeMarketSnapshot
from app.schemas.short_term import (
    MarketStrategyCardResponse,
    ShortTermOverviewResponse,
    ShortTermPeriod,
)
from app.services.short_term_rules import MarketStrengthInput, ShortTermRuleEngine
from app.services.theme_market import ThemeMarketService

INDEX_SIGNAL_CODES = {"BK0500", "BK0611", "BK0612", "BK0701", "BK0705"}
EMOTION_SIGNAL_CODES = {"BK0816", "BK1630", "BK1638", "BK1645"}


@dataclass(frozen=True)
class PeriodThemeMetric:
    """周期内题材市场快照聚合指标。"""

    rise_fall_pct: float
    heat_index: float
    stock_count: int
    up_count: int
    down_count: int
    limit_up_count: int
    limit_down_count: int
    trading_days: int = 1


class ShortTermService:
    """基于现有市场表现数据生成短线雷达概览。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.rules = ShortTermRuleEngine()

    async def get_overview(
        self,
        trade_date: date | None = None,
        period: ShortTermPeriod = "today",
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ShortTermOverviewResponse:
        """获取短线概览和指数情绪策略卡。"""
        resolved_end_date = end_date or trade_date or date.today()
        resolved_start_date, period_label = self._resolve_period(
            resolved_end_date, period, start_date
        )
        if resolved_start_date > resolved_end_date:
            msg = "自定义开始日期不能晚于结束日期"
            raise ValueError(msg)

        await self._ensure_period_snapshots(resolved_start_date, resolved_end_date)
        index_signals = await self._list_themes_by_codes(INDEX_SIGNAL_CODES)
        emotion_signals = await self._list_themes_by_codes(EMOTION_SIGNAL_CODES)
        leading_themes = await self._list_leading_themes()
        period_metrics = await self._list_period_snapshot_metrics(
            resolved_start_date, resolved_end_date
        )

        index_score = self._average_pct(index_signals)
        emotion_score = self._period_emotion_score(period_metrics)
        if emotion_score is None:
            emotion_score = self._emotion_score(emotion_signals)
        consecutive_count = self._period_limit_up_count(period_metrics)
        if consecutive_count is None:
            consecutive_count = sum(theme.stock_count or 0 for theme in emotion_signals)
        rotation_score = self._period_rotation_score(period_metrics)
        if rotation_score is None:
            rotation_score = self._rotation_score(leading_themes)

        card = self.rules.evaluate_market_strategy(
            MarketStrengthInput(
                index_score=index_score,
                emotion_score=emotion_score,
                consecutive_board_count=consecutive_count,
                rotation_score=rotation_score,
                period_label=period_label,
            )
        )
        missing_sources = []
        if not index_signals:
            missing_sources.append("index_signals")
        if not emotion_signals:
            missing_sources.append("emotion_signals")
        if not leading_themes:
            missing_sources.append("sector_rotation")
        if not period_metrics:
            missing_sources.append("周期市场快照")

        market_emotion = "情绪强" if card.emotion_strength == "strong" else "情绪弱"
        outlook = self._build_outlook(card.primary_strategy, card.secondary_strategy)
        risks = self._risk_signals(card.index_strength, card.emotion_strength)

        return ShortTermOverviewResponse(
            trade_date=resolved_end_date,
            period=period,
            period_label=period_label,
            start_date=resolved_start_date,
            end_date=resolved_end_date,
            degraded=bool(missing_sources),
            missing_sources=missing_sources,
            market_emotion=market_emotion,
            short_term_outlook=outlook,
            operation_advice=card.operation_advice,
            tracking_focus=card.focus_targets,
            core_conclusion=f"{card.primary_strategy}，辅助观察{card.secondary_strategy}。",
            risk_signals=risks,
            sector_count=len(period_metrics) or len(leading_themes),
            candidate_count=0,
            strategy_card=MarketStrategyCardResponse(**card.__dict__),
        )

    async def _list_themes_by_codes(self, codes: set[str]) -> list[Theme]:
        result = await self.session.execute(
            select(Theme).where(Theme.deleted_at.is_(None), Theme.code.in_(codes))
        )
        return list(result.scalars().all())

    async def _list_leading_themes(self) -> list[Theme]:
        result = await self.session.execute(
            select(Theme)
            .where(Theme.deleted_at.is_(None), exclude_market_signals())
            .order_by(desc(Theme.rise_fall_pct), desc(Theme.heat_index))
            .limit(5)
        )
        return list(result.scalars().all())

    async def _ensure_period_snapshots(self, start_date: date, end_date: date) -> None:
        """补齐周期内工作日市场快照，让切换周期时数据随周期变化。"""
        target_dates = self._period_trade_dates(start_date, end_date)
        if not target_dates:
            return

        result = await self.session.execute(
            select(distinct(ThemeMarketSnapshot.trade_date)).where(
                ThemeMarketSnapshot.trade_date.in_(target_dates)
            )
        )
        existing_dates = set(result.scalars().all())
        missing_dates = [day for day in target_dates if day not in existing_dates]
        if not missing_dates:
            return

        market_service = ThemeMarketService(self.session)
        for day in missing_dates:
            await market_service.refresh_all(day)

    async def _list_period_snapshot_metrics(
        self, start_date: date, end_date: date
    ) -> list[PeriodThemeMetric]:
        """按周期聚合每日题材市场快照。"""
        result = await self.session.execute(
            select(
                Theme.id,
                func.avg(Theme.rise_fall_pct).label("rise_fall_pct"),
                func.avg(Theme.heat_index).label("heat_index"),
                func.max(Theme.stock_count).label("stock_count"),
                func.sum(ThemeMarketSnapshot.up_count).label("up_count"),
                func.sum(ThemeMarketSnapshot.down_count).label("down_count"),
                func.sum(func.coalesce(ThemeMarketSnapshot.limit_up_count, 0)).label(
                    "limit_up_count"
                ),
                func.sum(func.coalesce(ThemeMarketSnapshot.limit_down_count, 0)).label(
                    "limit_down_count"
                ),
                func.count(distinct(ThemeMarketSnapshot.trade_date)).label(
                    "trading_days"
                ),
            )
            .join(Theme, Theme.id == ThemeMarketSnapshot.theme_id)
            .where(
                Theme.deleted_at.is_(None),
                exclude_market_signals(),
                ThemeMarketSnapshot.trade_date >= start_date,
                ThemeMarketSnapshot.trade_date <= end_date,
            )
            .group_by(Theme.id)
        )
        return [
            PeriodThemeMetric(
                rise_fall_pct=float(row.rise_fall_pct or 0),
                heat_index=float(row.heat_index or 0),
                stock_count=int(row.stock_count or 0),
                up_count=int(row.up_count or 0),
                down_count=int(row.down_count or 0),
                limit_up_count=int(row.limit_up_count or 0),
                limit_down_count=int(row.limit_down_count or 0),
                trading_days=max(int(row.trading_days or 1), 1),
            )
            for row in result.all()
        ]

    @staticmethod
    def _average_pct(themes: list[Theme]) -> float | None:
        if not themes:
            return None
        total = sum(Decimal(theme.rise_fall_pct or 0) for theme in themes)
        return float(total / len(themes))

    @staticmethod
    def _emotion_score(themes: list[Theme]) -> float | None:
        if not themes:
            return None
        count_score = min(sum(theme.stock_count or 0 for theme in themes), 60)
        pct_score = max(
            min(sum(float(theme.rise_fall_pct or 0) for theme in themes), 20), -20
        )
        return max(0, min(100, 30 + count_score + pct_score))

    @staticmethod
    def _period_emotion_score(metrics: list[PeriodThemeMetric]) -> float | None:
        if not metrics:
            return None
        average_limit_up_count = ShortTermService._period_limit_up_count(metrics) or 0
        limit_score = min(average_limit_up_count, 60)
        up_count = sum(metric.up_count for metric in metrics)
        down_count = sum(metric.down_count for metric in metrics)
        active_count = up_count + down_count
        breadth_score = 0
        if active_count > 0:
            breadth_score = ((up_count - down_count) / active_count) * 20
        return max(0, min(100, 30 + limit_score + breadth_score))

    @staticmethod
    def _period_limit_up_count(metrics: list[PeriodThemeMetric]) -> float | None:
        if not metrics:
            return None
        trading_days = ShortTermService._metric_trading_days(metrics)
        total_limit_up_count = sum(metric.limit_up_count for metric in metrics)
        return round(total_limit_up_count / trading_days / len(metrics), 1)

    @staticmethod
    def _metric_trading_days(metrics: list[PeriodThemeMetric]) -> int:
        return max((metric.trading_days for metric in metrics), default=1)

    @staticmethod
    def _rotation_score(themes: list[Theme]) -> float | None:
        if not themes:
            return None
        hot_count = sum(1 for theme in themes if float(theme.rise_fall_pct or 0) > 1)
        heat = sum(float(theme.heat_index or 0) for theme in themes) / len(themes)
        return min(100, hot_count * 12 + heat / 2)

    @staticmethod
    def _period_rotation_score(metrics: list[PeriodThemeMetric]) -> float | None:
        if not metrics:
            return None
        rotating_count = sum(
            1
            for metric in metrics
            if metric.limit_up_count > 0 or metric.up_count > metric.down_count
        )
        avg_heat = sum(metric.heat_index for metric in metrics) / len(metrics)
        return min(100, rotating_count * 10 + avg_heat / 2)

    @staticmethod
    def _build_outlook(primary: str, secondary: str) -> str:
        return f"当前更适合{primary}，盘中用{secondary}作为节奏确认。"

    @staticmethod
    def _risk_signals(index_strength: str, emotion_strength: str) -> list[str]:
        risks = []
        if index_strength == "weak":
            risks.append("指数承压")
        if emotion_strength == "weak":
            risks.append("短线情绪不足")
        return risks

    @staticmethod
    def _resolve_period(
        end_date: date, period: ShortTermPeriod, custom_start_date: date | None = None
    ) -> tuple[date, str]:
        if period == "custom":
            return custom_start_date or end_date - timedelta(days=14), "自定义"
        if period == "current_week":
            return end_date - timedelta(days=end_date.weekday()), "本周"
        if period == "half_month":
            return end_date - timedelta(days=14), "近半月"
        if period == "current_month":
            return end_date.replace(day=1), "本月"
        return end_date, "当日"

    @staticmethod
    def _period_trade_dates(start_date: date, end_date: date) -> list[date]:
        days = (end_date - start_date).days
        return [
            start_date + timedelta(days=offset)
            for offset in range(days + 1)
            if (start_date + timedelta(days=offset)).weekday() < 5
        ]
