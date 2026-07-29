"""短线机会雷达服务。"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Awaitable, Callable, TypeVar

import asyncio
from fastapi import HTTPException
from sqlalchemy import desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.theme_classification import classify_board_kind, exclude_market_signals
from app.models.theme import Theme
from app.models.theme_market_snapshot import ThemeMarketSnapshot
from app.schemas.short_term import (
    MarketStrategyCardResponse,
    RefreshMeta,
    SectorRotationItem,
    SectorRotationResponse,
    ShortTermOverviewResponse,
    ShortTermPeriod,
    ShortTermSignalRefreshResponse,
    ThemeLifecycleResponse,
    LifecyclePoint,
)
from app.services.short_term_rules import MarketStrengthInput, ShortTermRuleEngine
from app.services.strategy_quote_refresh import (
    StrategyQuoteRefreshResult,
    refresh_strategy_quotes,
)
from app.services.theme_market import ThemeMarketService
from app.services.sector_rotation import SectorRotationService
from app.repositories.short_term_signal import ShortTermSignalRepository
from app.scrapers.short_term_signals import ShortTermSignalScraper
from app.scrapers.dragon_tiger import DragonTigerScraper
from app.models.stock import Stock
from app.models.short_term_signal import SectorRotationSnapshot

logger = get_logger(__name__)
T = TypeVar("T")

INDEX_SIGNAL_CODES = {"BK0500", "BK0611", "BK0612", "BK0701", "BK0705"}
EMOTION_SIGNAL_CODES = {"BK0816", "BK1630", "BK1638", "BK1645"}
STRATEGY_QUOTE_CODES = INDEX_SIGNAL_CODES | EMOTION_SIGNAL_CODES
INDEX_BREADTH_PCT_SCALE = 2.0


@dataclass(frozen=True)
class IndexPeriodMetric:
    """周期内指数板块每日快照指标。"""

    trade_date: date
    rise_fall_pct: float | None
    up_count: int
    down_count: int


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
        self._last_quote_refresh: StrategyQuoteRefreshResult | None = None

    def _review_writer(self):
        from app.repositories.review import ReviewRepository
        from app.services.review_events import ReviewEventWriter

        return ReviewEventWriter(ReviewRepository(self.session))

    async def _safe_review_emit(self, coro: Awaitable[Any]) -> None:
        try:
            await coro
        except Exception as exc:  # noqa: BLE001
            logger.warning("复盘事件 emit 失败", error=str(exc))

    async def _run_with_review_track(
        self,
        *,
        trade_date: date,
        run_type: str,
        request_meta: dict[str, Any] | None,
        fn: Callable[[Any | None], Awaitable[T]],
    ) -> T:
        result: T | None = None
        track_started = False
        try:
            async with self._review_writer().track(
                trade_date=trade_date,
                run_type=run_type,
                request_meta=request_meta,
            ) as ctx:
                track_started = True
                result = await fn(ctx)
        except Exception as exc:  # noqa: BLE001
            if not track_started:
                logger.warning(
                    "复盘 run 启动失败",
                    run_type=run_type,
                    trade_date=str(trade_date),
                    error=str(exc),
                )
                return await fn(None)
            if result is not None:
                logger.warning(
                    "复盘 run 结束失败",
                    run_type=run_type,
                    trade_date=str(trade_date),
                    error=str(exc),
                )
                return result
            raise
        else:
            return result  # type: ignore[return-value]

    async def _emit_overview_review_events(
        self, ctx: Any | None, overview: ShortTermOverviewResponse
    ) -> None:
        if ctx is None:
            return
        card = overview.strategy_card
        await self._safe_review_emit(
            ctx.emit_strategy_card(
                {
                    "title": card.title,
                    "index_strength": card.index_strength,
                    "emotion_strength": card.emotion_strength,
                    "primary_strategy": card.primary_strategy,
                    "secondary_strategy": card.secondary_strategy,
                    "rationale": card.rationale[:5],
                }
            )
        )
        await self._safe_review_emit(
            ctx.emit_emotion(
                {
                    "market_emotion": overview.market_emotion,
                    "emotion_strength": card.emotion_strength,
                    "risk_signals": overview.risk_signals,
                }
            )
        )

    async def _emit_candidate_batch(self, ctx: Any | None, candidates: list) -> None:
        if ctx is None:
            return
        for candidate in candidates[:50]:
            await self._safe_review_emit(
                ctx.emit_candidate(
                    candidate.stock_id,
                    {
                        "strategy": candidate.strategy,
                        "theme_id": candidate.theme_id,
                        "score": candidate.score,
                        "rank": candidate.rank,
                        "decision": candidate.decision,
                    },
                )
            )

    async def get_overview(
        self,
        trade_date: date | None = None,
        period: ShortTermPeriod = "today",
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        ensure_snapshots: bool = True,
    ) -> ShortTermOverviewResponse:
        """获取短线概览和指数情绪策略卡。

        自定义周期默认只读库内快照，避免按日全量补数导致切换卡顿；
        需要补数时请走刷新行情或数据库分析接口。
        未指定交易日时，周末回退到最近周五，避免「当日」落在休市日导致周期快照为空。
        """
        if end_date is not None:
            resolved_end_date = end_date
        elif trade_date is not None:
            resolved_end_date = trade_date
        else:
            resolved_end_date = self.resolve_trade_date(None)
        resolved_start_date, period_label = self._resolve_period(
            resolved_end_date, period, start_date
        )
        if resolved_start_date > resolved_end_date:
            msg = "自定义开始日期不能晚于结束日期"
            raise ValueError(msg)

        if ensure_snapshots and period != "custom":
            await self._ensure_period_snapshots(resolved_start_date, resolved_end_date)
        return await self._build_overview(
            resolved_start_date, resolved_end_date, period, period_label
        )

    async def analyze_from_database(
        self,
        trade_date: date | None = None,
        period: ShortTermPeriod = "today",
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ShortTermOverviewResponse:
        """仅依据数据库已有数据重新分析策略卡，不触发外部拉取。"""
        if end_date is not None:
            resolved_end_date = end_date
        elif trade_date is not None:
            resolved_end_date = trade_date
        else:
            resolved_end_date = self.resolve_trade_date(None)

        async def _analyze(review_ctx: Any | None) -> ShortTermOverviewResponse:
            overview = await self.get_overview(
                trade_date,
                period,
                start_date=start_date,
                end_date=end_date,
                ensure_snapshots=False,
            )
            await self._emit_overview_review_events(review_ctx, overview)
            return overview

        return await self._run_with_review_track(
            trade_date=resolved_end_date,
            run_type="overview_analyze",
            request_meta={"period": period},
            fn=_analyze,
        )

    async def refresh_data_and_get_overview(
        self,
        trade_date: date | None = None,
        period: ShortTermPeriod = "today",
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ShortTermOverviewResponse:
        """拉取最新行情并重建周期快照后返回策略卡。

        短线信号全量采集请走 `refresh_signals` / `POST /signals/refresh`。
        """
        return await self._refresh_quotes_overview(
            trade_date, period, start_date=start_date, end_date=end_date
        )

    async def _refresh_quotes_overview(
        self,
        trade_date: date | None = None,
        period: ShortTermPeriod = "today",
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ShortTermOverviewResponse:
        """拉取最新行情并重建周期快照后返回策略卡。"""
        if end_date is not None:
            resolved_end_date = end_date
        elif trade_date is not None:
            resolved_end_date = self.resolve_trade_date(trade_date)
        else:
            resolved_end_date = self.resolve_trade_date(None)

        async def _refresh(review_ctx: Any | None) -> ShortTermOverviewResponse:
            resolved_start_date, period_label = self._resolve_period(
                resolved_end_date, period, start_date
            )
            if resolved_start_date > resolved_end_date:
                msg = "自定义开始日期不能晚于结束日期"
                raise ValueError(msg)

            quote_error: str | None = None
            try:
                await asyncio.wait_for(self._refresh_strategy_quotes(), timeout=25)
            except HTTPException as exc:
                if exc.status_code == 409:
                    raise
                quote_error = str(exc.detail)
            except (asyncio.TimeoutError, RuntimeError) as exc:
                quote_error = str(exc)

            if period != "today":
                await self._ensure_strategy_snapshots(
                    resolved_end_date, STRATEGY_QUOTE_CODES
                )
            if self._last_quote_refresh is not None:
                await self._persist_index_quote_snapshots(
                    self._last_quote_refresh.trade_date
                )
            overview = await self._build_overview(
                resolved_start_date, resolved_end_date, period, period_label
            )

            if review_ctx is not None:
                if self._last_quote_refresh is not None:
                    await self._safe_review_emit(
                        review_ctx.emit_quote_refresh(
                            {
                                "code_count": self._last_quote_refresh.updated_count,
                                "source": self._last_quote_refresh.source,
                            }
                        )
                    )
                elif quote_error:
                    await self._safe_review_emit(
                        review_ctx.emit_quote_refresh(
                            {
                                "code_count": len(STRATEGY_QUOTE_CODES),
                                "source": "database",
                                "error": quote_error,
                            }
                        )
                    )
                await self._emit_overview_review_events(review_ctx, overview)

            if quote_error:
                return overview.model_copy(
                    update={
                        "degraded": True,
                        "missing_sources": list(
                            dict.fromkeys([*overview.missing_sources, "strategy_quotes"])
                        ),
                        "refresh_meta": RefreshMeta(
                            quote_source="database",
                            quote_attempts=["东方财富", "AKShare"],
                            quote_message=quote_error,
                        ),
                    }
                )
            if self._last_quote_refresh is None:
                return overview
            return overview.model_copy(
                update={
                    "refresh_meta": RefreshMeta(
                        elapsed_ms=self._last_quote_refresh.elapsed_ms,
                        quote_source=self._last_quote_refresh.source,
                        quote_attempts=list(self._last_quote_refresh.attempts),
                    )
                }
            )

        return await self._run_with_review_track(
            trade_date=resolved_end_date,
            run_type="quote_refresh",
            request_meta={"period": period},
            fn=_refresh,
        )

    @staticmethod
    def resolve_trade_date(trade_date: date | None = None) -> date:
        """解析交易日：非开市日回退到上一开市日（含法定节假日）。"""
        from app.services.trading_calendar import TradingCalendar

        return TradingCalendar.resolve(trade_date)

    async def refresh_signals(
        self,
        trade_date: date | None = None,
        *,
        signal_scraper: ShortTermSignalScraper | None = None,
        dragon_scraper: DragonTigerScraper | None = None,
    ) -> ShortTermSignalRefreshResponse:
        """采集短线信号、龙虎榜并重建轮动/生命周期快照。"""
        resolved = self.resolve_trade_date(trade_date)

        async def _refresh(review_ctx: Any | None) -> ShortTermSignalRefreshResponse:
            repo = ShortTermSignalRepository(self.session)
            run = await repo.create_run(resolved)
            source_status: dict[str, object] = {}
            missing: list[str] = []
            signal_count = 0
            dragon_count = 0
            sector_count = 0
            candidate_count = 0

            signal_scraper_impl = signal_scraper or ShortTermSignalScraper()
            dragon_scraper_impl = dragon_scraper or DragonTigerScraper()

            signal_result = await signal_scraper_impl.fetch(resolved)
            source_status["short_term_signals"] = {
                "success": signal_result.success,
                "error": signal_result.error,
                "count": len(signal_result.items),
            }
            if signal_result.success:
                resolved_items = await self._resolve_signal_stock_ids(signal_result.items)
                signal_count = await repo.upsert_signals(resolved_items)
            else:
                missing.append("short_term_signals")

            dragon_result = await dragon_scraper_impl.fetch(resolved)
            source_status["dragon_tiger"] = {
                "success": dragon_result.success,
                "error": dragon_result.error,
                "count": len(dragon_result.items),
            }
            if dragon_result.success:
                resolved_dragon = await self._resolve_signal_stock_ids(dragon_result.items)
                dragon_count = await repo.upsert_dragon_tiger_entries(resolved_dragon)
            else:
                missing.append("dragon_tiger")

            try:
                sector_count = await SectorRotationService(self.session).rebuild(
                    resolved, review_ctx=review_ctx
                )
                source_status["sector_rotation"] = {
                    "success": True,
                    "count": sector_count,
                }
            except Exception as exc:  # noqa: BLE001
                missing.append("sector_rotation")
                source_status["sector_rotation"] = {
                    "success": False,
                    "error": str(exc),
                }

            candidates = await repo.get_candidates(resolved)
            candidate_count = len(candidates)

            if missing and (signal_count or dragon_count or sector_count):
                status = "partial"
            elif missing and not (signal_count or dragon_count or sector_count):
                status = "failed"
            else:
                status = "success"

            await repo.finish_run(
                run,
                status=status,
                source_status=source_status,
                error_message=None if status != "failed" else "短线信号刷新失败",
            )
            await self.session.commit()

            if review_ctx is not None:
                if status == "partial":
                    review_ctx.set_partial(source_status)
                await self._safe_review_emit(
                    review_ctx.emit_signal_batch(
                        {
                            "counts": {
                                "signal_count": signal_count,
                                "dragon_tiger_count": dragon_count,
                                "sector_count": sector_count,
                                "candidate_count": candidate_count,
                            },
                            "missing_sources": missing,
                        }
                    )
                )
                await self._emit_candidate_batch(review_ctx, candidates)

            return ShortTermSignalRefreshResponse(
                trade_date=resolved,
                status=status,
                signal_count=signal_count,
                dragon_tiger_count=dragon_count,
                sector_count=sector_count,
                candidate_count=candidate_count,
                degraded=bool(missing),
                missing_sources=missing,
                source_status=source_status,
                error_message=None if status != "failed" else "短线信号刷新失败",
            )

        result = await self._run_with_review_track(
            trade_date=resolved,
            run_type="signals_refresh",
            request_meta=None,
            fn=_refresh,
        )
        if result.status != "failed":
            try:
                from app.services.mining import MiningService

                await MiningService(self.session).ensure(resolved)
            except Exception as exc:  # noqa: BLE001 — 挖掘失败不阻断 refresh
                logger.warning(
                    "theme_mining_ensure_after_refresh_failed",
                    trade_date=str(resolved),
                    error=str(exc)[:300],
                )
            try:
                from app.services.mainline_graph import MainlineGraphService

                await MainlineGraphService(self.session).ensure(resolved)
            except Exception as exc:  # noqa: BLE001 — 主线图谱失败不阻断 refresh
                logger.warning(
                    "mainline_graph_ensure_after_refresh_failed",
                    trade_date=str(resolved),
                    error=str(exc)[:300],
                )
        return result

    async def get_sectors(
        self, trade_date: date | None = None, source: str | None = None
    ) -> SectorRotationResponse:
        from app.domain.scraper_sources import get_default_dashboard_source

        resolved_source = (source or "").strip() or get_default_dashboard_source()
        resolved = self.resolve_trade_date(trade_date)
        repo = ShortTermSignalRepository(self.session)
        snapshots = await repo.list_snapshots(resolved)
        if not snapshots:
            # fallback: nearest prior date with rows
            latest = await self.session.scalar(
                select(SectorRotationSnapshot.trade_date)
                .order_by(desc(SectorRotationSnapshot.trade_date))
                .limit(1)
            )
            if latest:
                resolved = latest
                snapshots = await repo.list_snapshots(resolved)

        theme_ids = [row.theme_id for row in snapshots]
        theme_meta: dict[int, tuple[str, str]] = {}
        if theme_ids:
            themes = (
                await self.session.scalars(
                    select(Theme).where(
                        Theme.id.in_(theme_ids),
                        Theme.source == resolved_source,
                        Theme.deleted_at.is_(None),
                    )
                )
            ).all()
            theme_meta = {
                t.id: (t.name, classify_board_kind(t.code, t.name)) for t in themes
            }

        items: list[SectorRotationItem] = []
        for row in snapshots:
            meta = theme_meta.get(row.theme_id)
            if meta is None:
                # 非当前题材源的快照行跳过
                continue
            name, kind = meta
            items.append(
                SectorRotationItem(
                    theme_id=row.theme_id,
                    theme_name=name,
                    board_kind=kind,  # type: ignore[arg-type]
                    lifecycle_stage=row.lifecycle_stage,  # type: ignore[arg-type]
                    lifecycle_confidence=row.lifecycle_confidence,
                    strength_score=row.strength_score,
                    mainline_score=row.mainline_score,
                    risk_score=row.risk_score,
                    limit_up_count=row.limit_up_count,
                    failed_limit_up_count=row.failed_limit_up_count,
                    summary=row.summary,
                    degraded=row.degraded,
                    missing_metrics=list(row.missing_metrics or []),
                )
            )
        # 同组内按主线分/强度排序，方便前端分区展示
        kind_rank = {"theme": 0, "indicator": 1, "market": 2}
        items.sort(
            key=lambda item: (
                kind_rank.get(item.board_kind, 9),
                -item.mainline_score,
                -item.strength_score,
            )
        )
        degraded = any(item.degraded for item in items)
        missing = sorted(
            {
                metric
                for item in items
                for metric in item.missing_metrics
            }
        )
        if not items:
            missing = list(dict.fromkeys([*missing, f"source:{resolved_source}"]))
        return SectorRotationResponse(
            trade_date=resolved,
            items=items,
            degraded=degraded or not items,
            missing_sources=missing,
        )

    async def get_theme_lifecycle(
        self, theme_id: int, days: int = 10
    ) -> ThemeLifecycleResponse:
        repo = ShortTermSignalRepository(self.session)
        rows = await repo.list_lifecycle_history(theme_id, days=days)
        points = [
            LifecyclePoint(
                trade_date=row.trade_date,
                lifecycle_stage=row.lifecycle_stage,  # type: ignore[arg-type]
                strength_score=row.strength_score,
                limit_quality_score=row.limit_quality_score,
                flow_score=row.flow_score,
                leader_clarity_score=row.leader_clarity_score,
                breadth_score=row.breadth_score,
                lifecycle_confidence=row.lifecycle_confidence,
            )
            for row in rows
        ]
        return ThemeLifecycleResponse(theme_id=theme_id, days=days, points=points)

    async def _resolve_signal_stock_ids(
        self, items: list[dict]
    ) -> list[dict]:
        from app.models.theme_stock import ThemeStock

        codes = {item.get("stock_code") for item in items if item.get("stock_code")}
        if not codes:
            return []

        # 缺失股票先落库，避免本地库无成分时整批跳过
        existing = (
            await self.session.scalars(select(Stock).where(Stock.code.in_(codes)))
        ).all()
        by_code = {s.code: s for s in existing}
        for item in items:
            code = item.get("stock_code")
            if not code or code in by_code:
                continue
            stock = Stock(
                code=code,
                name=str(item.get("stock_name") or code),
                current_price=item.get("price"),
                rise_fall_pct=None,
            )
            self.session.add(stock)
            by_code[code] = stock
        await self.session.flush()

        stock_ids = [s.id for s in by_code.values()]
        theme_links = (
            await self.session.execute(
                select(ThemeStock.stock_id, Theme.id, Theme.heat_index)
                .join(Theme, Theme.id == ThemeStock.theme_id)
                .where(ThemeStock.stock_id.in_(stock_ids))
            )
        ).all()
        best_theme: dict[int, tuple[int, float]] = {}
        for stock_id, theme_id, heat in theme_links:
            heat_v = float(heat or 0)
            prev = best_theme.get(stock_id)
            if prev is None or heat_v > prev[1]:
                best_theme[stock_id] = (theme_id, heat_v)

        resolved: list[dict] = []
        for item in items:
            code = item.get("stock_code")
            stock = by_code.get(code)
            if stock is None:
                continue
            payload = {
                k: v for k, v in item.items() if k not in {"stock_code", "stock_name"}
            }
            payload["stock_id"] = stock.id
            if payload.get("theme_id") is None and stock.id in best_theme:
                payload["theme_id"] = best_theme[stock.id][0]
            resolved.append(payload)
        return resolved

    async def _build_overview(
        self,
        resolved_start_date: date,
        resolved_end_date: date,
        period: ShortTermPeriod,
        period_label: str,
    ) -> ShortTermOverviewResponse:
        index_signals = await self._list_themes_by_codes(INDEX_SIGNAL_CODES)
        emotion_signals = await self._list_themes_by_codes(EMOTION_SIGNAL_CODES)
        leading_themes = await self._list_leading_themes()
        period_metrics = await self._list_period_snapshot_metrics(
            resolved_start_date, resolved_end_date
        )

        index_period_metrics = await self._list_index_period_snapshot_metrics(
            resolved_start_date, resolved_end_date
        )
        index_score = self._resolve_index_score(
            resolved_start_date,
            resolved_end_date,
            index_signals,
            index_period_metrics,
        )
        emotion_score = self._period_emotion_score(period_metrics)
        if emotion_score is None:
            emotion_score = self._emotion_score(emotion_signals)
        consecutive_count = self._period_limit_up_count(period_metrics)
        if consecutive_count is None:
            consecutive_count = sum(theme.stock_count or 0 for theme in emotion_signals)
        rotation_score = self._period_rotation_score(period_metrics)
        if rotation_score is None:
            rotation_score = self._rotation_score(leading_themes)

        expected_index_days = 1
        index_sample_days = 1 if index_signals else 0
        if resolved_start_date != resolved_end_date:
            expected_index_days = len(
                self._period_trade_dates(resolved_start_date, resolved_end_date)
            )
            index_sample_days = len(
                {metric.trade_date for metric in index_period_metrics}
            )

        card = self.rules.evaluate_market_strategy(
            MarketStrengthInput(
                index_score=index_score,
                emotion_score=emotion_score,
                consecutive_board_count=consecutive_count,
                rotation_score=rotation_score,
                period_label=period_label,
                index_sample_days=index_sample_days,
                index_expected_days=expected_index_days,
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
        if resolved_start_date != resolved_end_date:
            if not index_period_metrics:
                missing_sources.append("指数周期快照")
            elif index_sample_days < expected_index_days:
                missing_sources.append("指数周期快照不完整")

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

    async def _ensure_period_snapshots(
        self, start_date: date, end_date: date, *, force: bool = False
    ) -> None:
        """补齐周期内工作日市场快照，让切换周期时数据随周期变化。"""
        target_dates = self._period_trade_dates(start_date, end_date)
        if not target_dates:
            return

        if force:
            missing_dates = target_dates
        else:
            result = await self.session.execute(
                select(distinct(ThemeMarketSnapshot.trade_date)).where(
                    ThemeMarketSnapshot.trade_date.in_(target_dates)
                )
            )
            existing_dates = set(result.scalars().all())
            missing_dates = [day for day in target_dates if day not in existing_dates]

        if missing_dates:
            market_service = ThemeMarketService(self.session)
            for day in missing_dates:
                await market_service.refresh_all(day)
        # 题材快照已齐时仍要补指数板：指数强度依赖 INDEX_SIGNAL_CODES，
        # 不能因为其它题材已有当日快照就跳过。
        await self._ensure_index_period_snapshots(start_date, end_date)

    async def _ensure_index_period_snapshots(
        self, start_date: date, end_date: date
    ) -> None:
        """补齐周期内指数板块快照，供周期指数强度计算。

        仅回填当日：成分股行情表只有最新涨跌幅，用它去写历史快照会把
        「今天的强弱」复制到每一天，周期切换仍然全是弱/全是强。
        """
        missing_dates = await self._missing_index_snapshot_dates(start_date, end_date)
        today = date.today()
        missing_dates = [day for day in missing_dates if day == today]
        if not missing_dates:
            return
        market_service = ThemeMarketService(self.session)
        for day in missing_dates:
            await market_service.refresh_for_theme_codes(INDEX_SIGNAL_CODES, day)

    async def _missing_index_snapshot_dates(
        self, start_date: date, end_date: date
    ) -> list[date]:
        target_dates = self._period_trade_dates(start_date, end_date)
        if not target_dates:
            return []
        result = await self.session.execute(
            select(distinct(ThemeMarketSnapshot.trade_date)).join(
                Theme, Theme.id == ThemeMarketSnapshot.theme_id
            ).where(
                Theme.deleted_at.is_(None),
                Theme.code.in_(sorted(INDEX_SIGNAL_CODES)),
                ThemeMarketSnapshot.trade_date >= start_date,
                ThemeMarketSnapshot.trade_date <= end_date,
            )
        )
        existing_dates = set(result.scalars().all())
        return [day for day in target_dates if day not in existing_dates]

    async def _persist_index_quote_snapshots(self, trade_date: date) -> None:
        market_service = ThemeMarketService(self.session)
        await market_service.upsert_board_quotes(INDEX_SIGNAL_CODES, trade_date)

    async def _ensure_strategy_snapshots(
        self, trade_date: date, codes: set[str]
    ) -> None:
        """仅刷新策略相关题材快照，避免全量题材计算。"""
        market_service = ThemeMarketService(self.session)
        await market_service.refresh_for_theme_codes(codes, trade_date)

    async def _refresh_strategy_quotes(self) -> StrategyQuoteRefreshResult:
        """快速刷新题材涨跌幅，东方财富超时后自动切换 AKShare。

        与全量采集解耦，避免策略卡刷新被长时间全量任务锁死。
        """
        try:
            result = await refresh_strategy_quotes(STRATEGY_QUOTE_CODES)
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc

        self._last_quote_refresh = result
        return result

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

    async def _list_index_period_snapshot_metrics(
        self, start_date: date, end_date: date
    ) -> list[IndexPeriodMetric]:
        """按周期读取指数板块每日涨跌幅快照。"""
        result = await self.session.execute(
            select(
                ThemeMarketSnapshot.trade_date,
                ThemeMarketSnapshot.rise_fall_pct,
                ThemeMarketSnapshot.up_count,
                ThemeMarketSnapshot.down_count,
            )
            .join(Theme, Theme.id == ThemeMarketSnapshot.theme_id)
            .where(
                Theme.deleted_at.is_(None),
                Theme.code.in_(sorted(INDEX_SIGNAL_CODES)),
                ThemeMarketSnapshot.trade_date >= start_date,
                ThemeMarketSnapshot.trade_date <= end_date,
            )
        )
        return [
            IndexPeriodMetric(
                trade_date=row.trade_date,
                rise_fall_pct=(
                    float(row.rise_fall_pct) if row.rise_fall_pct is not None else None
                ),
                up_count=int(row.up_count or 0),
                down_count=int(row.down_count or 0),
            )
            for row in result.all()
        ]

    @staticmethod
    def _resolve_index_score(
        start_date: date,
        end_date: date,
        index_signals: list[Theme],
        index_period_metrics: list[IndexPeriodMetric],
    ) -> float | None:
        live_score = ShortTermService._average_pct(index_signals)
        period_score = ShortTermService._period_index_score(index_period_metrics)
        if start_date == end_date:
            return live_score if live_score is not None else period_score
        return period_score if period_score is not None else live_score

    @staticmethod
    def _index_metric_pct(metric: IndexPeriodMetric) -> float:
        if metric.rise_fall_pct is not None:
            return metric.rise_fall_pct
        active = metric.up_count + metric.down_count
        if active <= 0:
            return 0.0
        breadth_ratio = (metric.up_count - metric.down_count) / active
        return breadth_ratio * INDEX_BREADTH_PCT_SCALE

    @staticmethod
    def _period_index_score(metrics: list[IndexPeriodMetric]) -> float | None:
        if not metrics:
            return None
        by_day: dict[date, list[float]] = defaultdict(list)
        for metric in metrics:
            by_day[metric.trade_date].append(ShortTermService._index_metric_pct(metric))
        daily_averages = [
            sum(values) / len(values) for values in by_day.values() if values
        ]
        if not daily_averages:
            return None
        return sum(daily_averages) / len(daily_averages)

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
        from app.services.trading_calendar import TradingCalendar

        return TradingCalendar.list_trade_days(start_date, end_date)
