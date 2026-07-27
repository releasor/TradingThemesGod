"""复盘台聚合服务：事件投影，无事件时降级到快照表。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import ReviewAiReport, ReviewEvent, ReviewRun
from app.models.short_term_signal import SectorRotationSnapshot, ShortTermCandidate
from app.models.stock import Stock
from app.models.theme import Theme
from app.repositories.review import ReviewRepository
from app.schemas.review import (
    ReviewCandidateItem,
    ReviewCandidatePerformance,
    ReviewDayResponse,
    ReviewPerformance,
    ReviewRunBrief,
    ReviewStageTransition,
    ReviewThemeDayPoint,
    ReviewThemeResponse,
)
from app.services.short_term import ShortTermService
from app.services.trading_calendar import TradingCalendar


def _previous_weekday(value: date) -> date:
    return TradingCalendar.previous_trade_day(value)


def _next_weekday(value: date) -> date:
    return TradingCalendar.next_trade_day(value)

def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ReviewService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ReviewRepository(session)

    async def list_days(self, start: date, end: date) -> list[date]:
        run_dates = await self.repo.list_trade_dates(start, end)
        snap_dates = await self._list_snapshot_trade_dates(start, end)
        return sorted(set(run_dates) | set(snap_dates))

    async def get_day(self, trade_date: date | None) -> ReviewDayResponse:
        day = ShortTermService.resolve_trade_date(trade_date)
        events = await self.repo.list_events(day)
        runs = await self.repo.list_runs(day)
        if events:
            return await self._project_from_events(day, events, runs)
        return await self._project_from_legacy_snapshots(day, runs)

    async def get_theme(self, theme_id: int, days: int = 10) -> ReviewThemeResponse:
        end = ShortTermService.resolve_trade_date(None)
        # 日历缓冲覆盖周末，再按 snapshot 条数截断
        start = end - timedelta(days=max(days * 3, days))
        names = await self._load_theme_names([theme_id])
        theme_name = names.get(theme_id, f"题材#{theme_id}")

        history = await self._load_lifecycle_history(theme_id, days)
        trajectory = [
            ReviewThemeDayPoint(
                trade_date=row.trade_date,
                stage=row.lifecycle_stage,
                strength_score=row.strength_score or 0,
                rise_fall_pct=None,
            )
            for row in history
        ]

        events = await self.repo.list_theme_events(theme_id, start, end)
        related = await self._candidates_from_events(
            [e for e in events if e.event_type == "candidate_upsert"]
        )
        if not related:
            related = await self._load_theme_candidates(theme_id, start, end)

        trade_dates = {p.trade_date for p in trajectory}
        trade_dates.update(e.trade_date for e in events)
        run_refs: list[ReviewRunBrief] = []
        seen_run_ids: set[int] = set()
        for td in sorted(trade_dates):
            for run in await self.repo.list_runs(td):
                if run.id in seen_run_ids:
                    continue
                seen_run_ids.add(run.id)
                run_refs.append(self._run_brief(run))

        return ReviewThemeResponse(
            theme_id=theme_id,
            theme_name=theme_name,
            days=days,
            trajectory=trajectory,
            related_candidates=related,
            run_refs=run_refs,
        )

    async def _project_from_events(
        self,
        day: date,
        events: list[ReviewEvent],
        runs: list[ReviewRun],
    ) -> ReviewDayResponse:
        strategy_card: dict[str, Any] | None = None
        for event in events:
            if event.event_type == "strategy_card":
                strategy_card = dict(event.payload_json or {})

        missing: list[str] = []
        degraded = False
        if strategy_card and strategy_card.get("degraded"):
            degraded = True
            extra = strategy_card.get("missing_sources") or []
            if isinstance(extra, list):
                missing.extend(str(x) for x in extra)

        candidates = await self._candidates_from_events(
            [e for e in events if e.event_type == "candidate_upsert"]
        )
        transitions = await self._transitions_from_events(
            [e for e in events if e.event_type == "sector_stage_change"]
        )
        performance = await self._build_performance(day, candidates)
        report_summary = await self._report_summary(day)

        return ReviewDayResponse(
            trade_date=day,
            degraded=degraded,
            missing_sources=missing,
            runs=[self._run_brief(r) for r in runs],
            strategy_card=strategy_card,
            candidates=candidates,
            stage_transitions=transitions,
            performance=performance,
            report_summary=report_summary,
        )

    async def _project_from_legacy_snapshots(
        self,
        day: date,
        runs: list[ReviewRun],
    ) -> ReviewDayResponse:
        candidates_raw = await self._load_legacy_candidates(day)
        stock_ids = [c.stock_id for c in candidates_raw]
        theme_ids = [c.theme_id for c in candidates_raw if c.theme_id is not None]
        stock_map = await self._load_stock_map(stock_ids)
        theme_names = await self._load_theme_names(theme_ids)

        candidates = [
            ReviewCandidateItem(
                stock_id=c.stock_id,
                stock_code=(stock_map[c.stock_id].code if c.stock_id in stock_map else None),
                stock_name=(stock_map[c.stock_id].name if c.stock_id in stock_map else None),
                theme_id=c.theme_id,
                theme_name=theme_names.get(c.theme_id) if c.theme_id else None,
                strategy=c.strategy or "",
                score=int(c.score or 0),
                rank=int(c.rank or 0),
                decision=c.decision or "",
            )
            for c in candidates_raw
        ]

        transitions = await self._legacy_stage_transitions(day)
        performance = await self._build_performance(day, candidates)
        report_summary = await self._report_summary(day)

        return ReviewDayResponse(
            trade_date=day,
            degraded=True,
            missing_sources=["review_events"],
            runs=[self._run_brief(r) for r in runs],
            strategy_card=None,
            candidates=candidates,
            stage_transitions=transitions,
            performance=performance,
            report_summary=report_summary,
        )

    async def _candidates_from_events(
        self, events: list[ReviewEvent]
    ) -> list[ReviewCandidateItem]:
        if not events:
            return []

        # 同 stock+strategy 取最后一次 upsert
        latest: dict[tuple[int, str], ReviewEvent] = {}
        for event in events:
            stock_id = event.entity_id
            if stock_id is None:
                continue
            strategy = str((event.payload_json or {}).get("strategy") or "")
            latest[(stock_id, strategy)] = event

        stock_ids = [sid for sid, _ in latest]
        theme_ids = [
            int(p["theme_id"])
            for e in latest.values()
            for p in [e.payload_json or {}]
            if p.get("theme_id") is not None
        ]
        stock_map = await self._load_stock_map(stock_ids)
        theme_names = await self._load_theme_names(theme_ids)

        items: list[ReviewCandidateItem] = []
        for (stock_id, strategy), event in latest.items():
            payload = event.payload_json or {}
            theme_id = payload.get("theme_id")
            theme_id_int = int(theme_id) if theme_id is not None else None
            stock = stock_map.get(stock_id)
            items.append(
                ReviewCandidateItem(
                    stock_id=stock_id,
                    stock_code=stock.code if stock else None,
                    stock_name=stock.name if stock else None,
                    theme_id=theme_id_int,
                    theme_name=theme_names.get(theme_id_int) if theme_id_int else None,
                    strategy=strategy,
                    score=int(payload.get("score") or 0),
                    rank=int(payload.get("rank") or 0),
                    decision=str(payload.get("decision") or ""),
                )
            )
        items.sort(key=lambda x: (x.rank or 0, -x.score))
        return items

    async def _transitions_from_events(
        self, events: list[ReviewEvent]
    ) -> list[ReviewStageTransition]:
        if not events:
            return []
        theme_ids = [e.entity_id for e in events if e.entity_id is not None]
        theme_names = await self._load_theme_names(theme_ids)
        result: list[ReviewStageTransition] = []
        for event in events:
            if event.entity_id is None:
                continue
            payload = event.payload_json or {}
            to_stage = payload.get("to_stage")
            if not to_stage:
                continue
            result.append(
                ReviewStageTransition(
                    theme_id=event.entity_id,
                    theme_name=theme_names.get(event.entity_id),
                    from_stage=payload.get("from_stage"),
                    to_stage=str(to_stage),
                    strength_score=payload.get("strength_score"),
                )
            )
        return result

    async def _legacy_stage_transitions(
        self, day: date
    ) -> list[ReviewStageTransition]:
        today_rows = await self._load_sector_snapshots_for_date(day)
        if not today_rows:
            return []
        prior_day = _previous_weekday(day)
        prior_rows = await self._load_sector_snapshots_for_date(prior_day)
        prior_map = {r.theme_id: r for r in prior_rows}
        theme_ids = [r.theme_id for r in today_rows]
        theme_names = await self._load_theme_names(theme_ids)

        transitions: list[ReviewStageTransition] = []
        for row in today_rows:
            prior = prior_map.get(row.theme_id)
            from_stage = prior.lifecycle_stage if prior else None
            to_stage = row.lifecycle_stage
            if from_stage == to_stage:
                continue
            transitions.append(
                ReviewStageTransition(
                    theme_id=row.theme_id,
                    theme_name=theme_names.get(row.theme_id),
                    from_stage=from_stage,
                    to_stage=to_stage,
                    strength_score=row.strength_score,
                )
            )
        return transitions

    async def _build_performance(
        self,
        day: date,
        candidates: list[ReviewCandidateItem],
    ) -> ReviewPerformance | None:
        if not candidates:
            return ReviewPerformance(candidates=[])

        today = ShortTermService.resolve_trade_date(None)
        next_day = _next_weekday(day)
        stock_map = await self._load_stock_map([c.stock_id for c in candidates])

        items: list[ReviewCandidatePerformance] = []
        for cand in candidates:
            stock = stock_map.get(cand.stock_id)
            same_day_pct: float | None = None
            next_day_pct: float | None = None
            reason: str | None = None

            if day == today:
                same_day_pct = _to_float(stock.rise_fall_pct) if stock else None
                if same_day_pct is None:
                    reason = "无当日涨跌幅"
            else:
                reason = "无历史行情快照"

            if next_day == today:
                next_day_pct = _to_float(stock.rise_fall_pct) if stock else None
                if next_day_pct is None and reason is None:
                    reason = "次日涨跌幅不可用"
            elif next_day > today:
                if reason is None:
                    reason = "次日尚未开盘或无数据"
            else:
                # 历史次日也无行情表
                if reason is None:
                    reason = "无历史行情快照"
                next_day_pct = None

            items.append(
                ReviewCandidatePerformance(
                    stock_id=cand.stock_id,
                    stock_code=cand.stock_code or (stock.code if stock else None),
                    stock_name=cand.stock_name or (stock.name if stock else None),
                    same_day_pct=same_day_pct,
                    next_day_pct=next_day_pct,
                    reason=reason,
                )
            )
        return ReviewPerformance(candidates=items)

    async def _report_summary(self, day: date) -> str | None:
        report = await self.repo.get_report(day, None)
        return self._extract_report_summary(report)

    @staticmethod
    def _extract_report_summary(report: ReviewAiReport | None) -> str | None:
        if report is None:
            return None
        if report.status not in ("success", "rule_fallback"):
            return None
        content = report.content_json or {}
        summary = content.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        if report.content_md and report.content_md.strip():
            return report.content_md.strip().splitlines()[0][:200]
        return None

    @staticmethod
    def _run_brief(run: ReviewRun) -> ReviewRunBrief:
        return ReviewRunBrief(
            id=run.id,
            trade_date=run.trade_date,
            run_type=run.run_type,
            status=run.status,
            source_status=dict(run.source_status or {}),
            started_at=run.started_at,
            finished_at=run.finished_at,
        )

    async def _list_snapshot_trade_dates(
        self, start: date, end: date
    ) -> list[date]:
        result = await self.session.scalars(
            select(distinct(SectorRotationSnapshot.trade_date))
            .where(
                SectorRotationSnapshot.trade_date >= start,
                SectorRotationSnapshot.trade_date <= end,
            )
            .order_by(SectorRotationSnapshot.trade_date.asc())
        )
        return list(result.all())

    async def _load_sector_snapshots(
        self, trade_date: date
    ) -> list[SectorRotationSnapshot]:
        return await self._load_sector_snapshots_for_date(trade_date)

    async def _load_sector_snapshots_for_date(
        self, trade_date: date
    ) -> list[SectorRotationSnapshot]:
        result = await self.session.scalars(
            select(SectorRotationSnapshot).where(
                SectorRotationSnapshot.trade_date == trade_date
            )
        )
        return list(result.all())

    async def _load_legacy_candidates(
        self, trade_date: date
    ) -> list[ShortTermCandidate]:
        result = await self.session.scalars(
            select(ShortTermCandidate)
            .where(ShortTermCandidate.trade_date == trade_date)
            .order_by(ShortTermCandidate.rank.asc())
        )
        return list(result.all())

    async def _load_lifecycle_history(
        self, theme_id: int, days: int
    ) -> list[SectorRotationSnapshot]:
        result = await self.session.scalars(
            select(SectorRotationSnapshot)
            .where(SectorRotationSnapshot.theme_id == theme_id)
            .order_by(SectorRotationSnapshot.trade_date.desc())
            .limit(days)
        )
        rows = list(result.all())
        rows.reverse()
        return rows

    async def _load_theme_candidates(
        self, theme_id: int, start: date, end: date
    ) -> list[ReviewCandidateItem]:
        result = await self.session.scalars(
            select(ShortTermCandidate)
            .where(
                ShortTermCandidate.theme_id == theme_id,
                ShortTermCandidate.trade_date >= start,
                ShortTermCandidate.trade_date <= end,
            )
            .order_by(
                ShortTermCandidate.trade_date.desc(),
                ShortTermCandidate.rank.asc(),
            )
            .limit(50)
        )
        rows = list(result.all())
        if not rows:
            return []
        stock_map = await self._load_stock_map([r.stock_id for r in rows])
        names = await self._load_theme_names([theme_id])
        theme_name = names.get(theme_id)
        return [
            ReviewCandidateItem(
                stock_id=r.stock_id,
                stock_code=stock_map[r.stock_id].code if r.stock_id in stock_map else None,
                stock_name=stock_map[r.stock_id].name if r.stock_id in stock_map else None,
                theme_id=theme_id,
                theme_name=theme_name,
                strategy=r.strategy or "",
                score=int(r.score or 0),
                rank=int(r.rank or 0),
                decision=r.decision or "",
            )
            for r in rows
        ]

    async def _load_stock_map(self, stock_ids: list[int]) -> dict[int, Stock]:
        ids = sorted({i for i in stock_ids if i is not None})
        if not ids:
            return {}
        result = await self.session.scalars(select(Stock).where(Stock.id.in_(ids)))
        return {row.id: row for row in result.all()}

    async def _load_theme_names(self, theme_ids: list[int]) -> dict[int, str]:
        ids = sorted({i for i in theme_ids if i is not None})
        if not ids:
            return {}
        result = await self.session.execute(
            select(Theme.id, Theme.name).where(Theme.id.in_(ids))
        )
        return {row[0]: row[1] for row in result.all()}
