"""题材轮动快照重建（含生命周期与四维强度）。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.theme_classification import (
    exclude_market_signals,
    only_indicator_signals,
    only_market_signals,
)
from app.models.short_term_signal import (
    DailyStockSignal,
    DragonTigerEntry,
    SectorRotationSnapshot,
)

if TYPE_CHECKING:
    from app.services.review_events import ReviewRunContext

from app.models.stock import Stock
from app.models.theme import Theme
from app.models.theme_market_snapshot import ThemeMarketSnapshot
from app.models.theme_stock import ThemeStock
from app.repositories.short_term_signal import ShortTermSignalRepository
from app.services.lifecycle_rules import (
    TOP_COVER_DEFAULT,
    ThemeDayMetrics,
    build_snapshot_scores,
)

logger = get_logger(__name__)


def _f(value: Decimal | float | int | None, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


class SectorRotationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ShortTermSignalRepository(session)

    async def rebuild(
        self,
        trade_date: date,
        *,
        top_n: int = TOP_COVER_DEFAULT,
        review_ctx: ReviewRunContext | None = None,
    ) -> int:
        theme_ids = await self._cover_theme_ids(trade_date, top_n=top_n)
        if not theme_ids:
            return 0

        prior_stages = await self._load_prior_lifecycle_stages(theme_ids, trade_date)
        history_start = trade_date - timedelta(days=30)
        snapshots = await self._load_snapshots(theme_ids, history_start, trade_date)
        signals = await self._load_signals(theme_ids, history_start, trade_date)
        dragon = await self._load_dragon_by_theme(theme_ids, trade_date)
        quotes = await self._load_theme_quotes(theme_ids)
        leaders = await self._load_leader_stats(theme_ids)

        rows: list[dict] = []
        for theme_id in theme_ids:
            theme = quotes.get(theme_id)
            if theme is None:
                continue
            leader_rise, avg_rise, second_rise = leaders.get(
                theme_id, (None, _f(theme.rise_fall_pct), None)
            )
            days = self._build_history(
                theme=theme,
                trade_date=trade_date,
                snapshots=snapshots.get(theme_id, {}),
                signals=signals.get(theme_id, {}),
                dragon_net=dragon.get(theme_id),
                dragon_percentile=self._percentile(
                    dragon.get(theme_id), list(dragon.values())
                ),
                leader_rise=leader_rise,
                avg_rise=avg_rise,
                second_rise=second_rise,
            )
            if not days:
                continue
            scores = build_snapshot_scores(days)
            today_signals = signals.get(theme_id, {}).get(trade_date, {})
            rows.append(
                {
                    "trade_date": trade_date,
                    "theme_id": theme_id,
                    "trend_score": scores.trend_score,
                    "emotion_score": scores.emotion_score,
                    "rotation_score": scores.rotation_score,
                    "mainline_score": scores.mainline_score,
                    "risk_score": scores.risk_score,
                    "strong_stock_count": today_signals.get("strong", 0),
                    "limit_up_count": today_signals.get("limit_up", 0),
                    "failed_limit_up_count": today_signals.get("failed", 0),
                    "near_limit_up_count": today_signals.get("near", 0),
                    "summary": scores.summary,
                    "source": "rules",
                    "lifecycle_stage": scores.lifecycle_stage,
                    "lifecycle_confidence": scores.lifecycle_confidence,
                    "strength_score": scores.strength_score,
                    "limit_quality_score": scores.limit_quality_score,
                    "flow_score": scores.flow_score,
                    "leader_clarity_score": scores.leader_clarity_score,
                    "breadth_score": scores.breadth_score,
                    "score_breakdown": scores.score_breakdown,
                    "degraded": scores.degraded,
                    "missing_metrics": scores.missing_metrics,
                }
            )

        await self.repo.upsert_sector_snapshots(rows)
        if review_ctx is not None:
            await self._emit_stage_changes(review_ctx, rows, prior_stages)
        return len(rows)

    async def _load_prior_lifecycle_stages(
        self, theme_ids: set[int], trade_date: date
    ) -> dict[int, str | None]:
        prior_date = await self.session.scalar(
            select(SectorRotationSnapshot.trade_date)
            .where(SectorRotationSnapshot.trade_date < trade_date)
            .order_by(desc(SectorRotationSnapshot.trade_date))
            .limit(1)
        )
        if prior_date is None:
            return {}
        snapshots = await self.repo.list_snapshots(prior_date)
        return {
            row.theme_id: row.lifecycle_stage
            for row in snapshots
            if row.theme_id in theme_ids
        }

    async def _emit_stage_changes(
        self,
        review_ctx: ReviewRunContext,
        rows: list[dict],
        prior_stages: dict[int, str | None],
    ) -> None:
        for row in rows:
            theme_id = row["theme_id"]
            new_stage = row["lifecycle_stage"]
            old_stage = prior_stages.get(theme_id)
            if old_stage == new_stage:
                continue
            try:
                await review_ctx.emit_stage_change(
                    theme_id,
                    {
                        "from_stage": old_stage,
                        "to_stage": new_stage,
                        "strength_score": row.get("strength_score"),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "复盘阶段迁移事件写入失败",
                    theme_id=theme_id,
                    error=str(exc),
                )

    async def _cover_theme_ids(self, trade_date: date, *, top_n: int) -> set[int]:
        heat_rows = (
            await self.session.scalars(
                select(Theme.id)
                .where(exclude_market_signals())
                .order_by(desc(Theme.heat_index))
                .limit(top_n)
            )
        ).all()
        rise_rows = (
            await self.session.scalars(
                select(Theme.id)
                .where(exclude_market_signals())
                .order_by(desc(Theme.rise_fall_pct))
                .limit(top_n)
            )
        ).all()
        signal_theme_ids = (
            await self.session.scalars(
                select(DailyStockSignal.theme_id)
                .where(
                    DailyStockSignal.trade_date == trade_date,
                    DailyStockSignal.theme_id.is_not(None),
                )
                .distinct()
            )
        ).all()
        # 行情指标 / 市场表现单独成组展示，重建时一并覆盖
        market_ids = (
            await self.session.scalars(
                select(Theme.id).where(
                    Theme.deleted_at.is_(None), only_market_signals()
                )
            )
        ).all()
        indicator_ids = (
            await self.session.scalars(
                select(Theme.id).where(
                    Theme.deleted_at.is_(None), only_indicator_signals()
                )
            )
        ).all()
        return (
            set(heat_rows)
            | set(rise_rows)
            | {tid for tid in signal_theme_ids if tid}
            | set(market_ids)
            | set(indicator_ids)
        )

    async def _load_snapshots(
        self, theme_ids: set[int], start: date, end: date
    ) -> dict[int, dict[date, ThemeMarketSnapshot]]:
        rows = (
            await self.session.scalars(
                select(ThemeMarketSnapshot).where(
                    ThemeMarketSnapshot.theme_id.in_(theme_ids),
                    ThemeMarketSnapshot.trade_date >= start,
                    ThemeMarketSnapshot.trade_date <= end,
                )
            )
        ).all()
        out: dict[int, dict[date, ThemeMarketSnapshot]] = defaultdict(dict)
        for row in rows:
            out[row.theme_id][row.trade_date] = row
        return out

    async def _load_signals(
        self, theme_ids: set[int], start: date, end: date
    ) -> dict[int, dict[date, dict[str, int]]]:
        rows = (
            await self.session.scalars(
                select(DailyStockSignal).where(
                    DailyStockSignal.theme_id.in_(theme_ids),
                    DailyStockSignal.trade_date >= start,
                    DailyStockSignal.trade_date <= end,
                )
            )
        ).all()
        out: dict[int, dict[date, dict[str, int]]] = defaultdict(
            lambda: defaultdict(
                lambda: {
                    "limit_up": 0,
                    "failed": 0,
                    "near": 0,
                    "one_word": 0,
                    "streak_ge2": 0,
                    "strong": 0,
                }
            )
        )
        for row in rows:
            if row.theme_id is None:
                continue
            bucket = out[row.theme_id][row.trade_date]
            if row.signal_type in {
                "limit_up",
                "first_limit_up",
                "second_limit_up",
                "one_word_limit_up",
            }:
                bucket["limit_up"] += 1
                bucket["strong"] += 1
            if row.signal_type == "failed_limit_up" or row.is_failed:
                bucket["failed"] += 1
            if row.signal_type == "near_limit_up":
                bucket["near"] += 1
            if row.is_one_word or row.signal_type == "one_word_limit_up":
                bucket["one_word"] += 1
            if row.streak_days >= 2:
                bucket["streak_ge2"] += 1
        return out

    async def _load_dragon_by_theme(
        self, theme_ids: set[int], trade_date: date
    ) -> dict[int, float]:
        stock_theme = (
            await self.session.execute(
                select(ThemeStock.theme_id, ThemeStock.stock_id).where(
                    ThemeStock.theme_id.in_(theme_ids)
                )
            )
        ).all()
        stock_to_themes: dict[int, list[int]] = defaultdict(list)
        for theme_id, stock_id in stock_theme:
            stock_to_themes[stock_id].append(theme_id)

        entries = (
            await self.session.scalars(
                select(DragonTigerEntry).where(DragonTigerEntry.trade_date == trade_date)
            )
        ).all()
        totals: dict[int, float] = defaultdict(float)
        for entry in entries:
            for theme_id in stock_to_themes.get(entry.stock_id, []):
                totals[theme_id] += _f(entry.net_amount)
        return dict(totals)

    async def _load_theme_quotes(self, theme_ids: set[int]) -> dict[int, Theme]:
        rows = (
            await self.session.scalars(select(Theme).where(Theme.id.in_(theme_ids)))
        ).all()
        return {row.id: row for row in rows}

    async def _load_leader_stats(
        self, theme_ids: set[int]
    ) -> dict[int, tuple[float | None, float | None, float | None]]:
        rows = (
            await self.session.execute(
                select(ThemeStock.theme_id, Stock.rise_fall_pct)
                .join(Stock, Stock.id == ThemeStock.stock_id)
                .where(ThemeStock.theme_id.in_(theme_ids))
            )
        ).all()
        by_theme: dict[int, list[float]] = defaultdict(list)
        for theme_id, rise in rows:
            if rise is not None:
                by_theme[theme_id].append(float(rise))
        out: dict[int, tuple[float | None, float | None, float | None]] = {}
        for theme_id, values in by_theme.items():
            values.sort(reverse=True)
            avg = sum(values) / len(values)
            leader = values[0]
            second = values[1] if len(values) > 1 else None
            out[theme_id] = (leader, avg, second)
        return out

    def _percentile(self, value: float | None, values: list[float | None]) -> float | None:
        if value is None:
            return None
        cleaned = sorted(v for v in values if v is not None)
        if not cleaned:
            return None
        rank = sum(1 for v in cleaned if v <= value)
        return rank / len(cleaned)

    def _build_history(
        self,
        *,
        theme: Theme,
        trade_date: date,
        snapshots: dict[date, ThemeMarketSnapshot],
        signals: dict[date, dict[str, int]],
        dragon_net: float | None,
        dragon_percentile: float | None,
        leader_rise: float | None,
        avg_rise: float | None,
        second_rise: float | None,
    ) -> list[ThemeDayMetrics]:
        dates = sorted(set(snapshots.keys()) | set(signals.keys()) | {trade_date})
        dates = [d for d in dates if d <= trade_date][-10:]
        if trade_date not in dates:
            dates.append(trade_date)
            dates = sorted(dates)[-10:]

        history: list[ThemeDayMetrics] = []
        for day in dates:
            snap = snapshots.get(day)
            sig = signals.get(day, {})
            limit_up = sig.get("limit_up")
            if limit_up is None and snap is not None:
                limit_up = int(snap.limit_up_count or 0)
            limit_up = int(limit_up or 0)
            failed = int(sig.get("failed") or 0)
            history.append(
                ThemeDayMetrics(
                    trade_date=day,
                    heat_index=_f(theme.heat_index),
                    rise_fall_pct=_f(
                        snap.rise_fall_pct
                        if snap and snap.rise_fall_pct is not None
                        else theme.rise_fall_pct
                    ),
                    stock_count=int(theme.stock_count or 0),
                    up_count=int(snap.up_count if snap else 0),
                    down_count=int(snap.down_count if snap else 0),
                    flat_count=int(snap.flat_count if snap else 0),
                    suspended_count=int(snap.suspended_count if snap else 0),
                    limit_up_count=limit_up,
                    failed_limit_up_count=failed,
                    one_word_count=int(sig.get("one_word") or 0),
                    streak_ge2_count=int(sig.get("streak_ge2") or 0),
                    leader_rise_fall_pct=leader_rise,
                    avg_rise_fall_pct=avg_rise,
                    second_rise_fall_pct=second_rise,
                    dragon_net_amount=dragon_net if day == trade_date else None,
                    theme_net_percentile=dragon_percentile if day == trade_date else None,
                )
            )
        return history
