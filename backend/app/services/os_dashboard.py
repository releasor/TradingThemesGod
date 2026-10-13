"""个人 AI OS 仪表盘：汇总 + 钉选 + 优化指引。"""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_os import (
    OsChatSession,
    OsDailyReport,
    OsDashboardPin,
    OsDecisionThread,
    OsJournalEntry,
    OsNote,
)
from app.schemas.personal_os import (
    OsDashboardCounts,
    OsDashboardJournalByKind,
    OsDashboardOverview,
    OsDashboardPinCreate,
    OsDashboardPinResponse,
    OsDashboardPinUpdate,
    OsDashboardRecentItem,
    OsOptimizeTip,
)
from app.services.os_profile import OsProfileService

_HREF = {
    "chat_session": "/os/chat?session={id}",
    "note": "/os/memory",
    "journal": "/os/journal",
    "report": "/os/reports",
    "decision": "/os/decisions",
}

_TYPE_LABEL = {
    "chat_session": "对话",
    "note": "笔记",
    "journal": "日志",
    "report": "日报",
    "decision": "决策",
}


class OsDashboardService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.profiles = OsProfileService(session, user_id)

    def _href(self, source_type: str, source_id: int) -> str:
        tpl = _HREF.get(source_type, "/os")
        return tpl.format(id=source_id)

    def _pin_response(self, pin: OsDashboardPin) -> OsDashboardPinResponse:
        return OsDashboardPinResponse(
            id=pin.id,
            user_id=pin.user_id,
            source_type=pin.source_type,
            source_id=pin.source_id,
            title=pin.title,
            snippet=pin.snippet,
            sort_order=pin.sort_order,
            href=self._href(pin.source_type, pin.source_id),
            created_at=pin.created_at,
            updated_at=pin.updated_at,
        )

    async def _count(self, model) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(model).where(model.user_id == self.user_id)
        )
        return int(result.scalar_one() or 0)

    async def overview(self) -> OsDashboardOverview:
        profile = await self.profiles.ensure_profile()

        chat_n = await self._count(OsChatSession)
        note_n = await self._count(OsNote)
        journal_n = await self._count(OsJournalEntry)
        report_n = await self._count(OsDailyReport)
        decision_n = await self._count(OsDecisionThread)
        pin_n = await self._count(OsDashboardPin)

        kind_rows = await self.session.execute(
            select(OsJournalEntry.kind, func.count())
            .where(OsJournalEntry.user_id == self.user_id)
            .group_by(OsJournalEntry.kind)
        )
        by_kind = {k: int(c) for k, c in kind_rows.all()}
        journal_by_kind = OsDashboardJournalByKind(
            diet=by_kind.get("diet", 0),
            training=by_kind.get("training", 0),
            sleep=by_kind.get("sleep", 0),
            schedule=by_kind.get("schedule", 0),
        )

        pins = await self.list_pins()
        pinned_keys = {(p.source_type, p.source_id) for p in pins}

        recent = await self._recent_items(pinned_keys)
        tips = self._optimize_tips(
            profile=profile,
            chat_n=chat_n,
            note_n=note_n,
            journal_n=journal_n,
            report_n=report_n,
            decision_n=decision_n,
            prefs=profile.model_prefs or {},
        )

        if journal_n == 0 and note_n == 0 and chat_n == 0:
            readiness = "empty"
        elif journal_n < 7:
            readiness = "warmup"
        else:
            readiness = "ready"

        return OsDashboardOverview(
            display_name=profile.display_name,
            goals=profile.goals,
            health_baseline=dict(profile.health_baseline or {}),
            module_flags=dict(profile.module_flags or {}),
            has_report_tuning=bool((profile.report_prompt_appendix or "").strip()),
            has_decision_tuning=bool(
                (getattr(profile, "decision_prompt_appendix", None) or "").strip()
            ),
            data_readiness=readiness,  # type: ignore[arg-type]
            counts=OsDashboardCounts(
                chat_sessions=chat_n,
                notes=note_n,
                journal=journal_n,
                reports=report_n,
                decisions=decision_n,
                pins=pin_n,
            ),
            journal_by_kind=journal_by_kind,
            recent=recent,
            pins=pins,
            optimize_tips=tips,
        )

    async def _recent_items(
        self, pinned_keys: set[tuple[str, int]]
    ) -> list[OsDashboardRecentItem]:
        items: list[OsDashboardRecentItem] = []

        sessions = await self.session.execute(
            select(OsChatSession)
            .where(OsChatSession.user_id == self.user_id)
            .order_by(OsChatSession.updated_at.desc())
            .limit(5)
        )
        for s in sessions.scalars():
            items.append(
                OsDashboardRecentItem(
                    id=s.id,
                    source_type="chat_session",
                    title=s.title,
                    snippet=None,
                    href=self._href("chat_session", s.id),
                    at=s.updated_at,
                    pinned=("chat_session", s.id) in pinned_keys,
                )
            )

        notes = await self.session.execute(
            select(OsNote)
            .where(OsNote.user_id == self.user_id)
            .order_by(OsNote.updated_at.desc())
            .limit(5)
        )
        for n in notes.scalars():
            items.append(
                OsDashboardRecentItem(
                    id=n.id,
                    source_type="note",
                    title=n.title,
                    snippet=(n.body or "")[:120],
                    href=self._href("note", n.id),
                    at=n.updated_at,
                    pinned=("note", n.id) in pinned_keys,
                )
            )

        journals = await self.session.execute(
            select(OsJournalEntry)
            .where(OsJournalEntry.user_id == self.user_id)
            .order_by(OsJournalEntry.occurred_at.desc())
            .limit(5)
        )
        for j in journals.scalars():
            items.append(
                OsDashboardRecentItem(
                    id=j.id,
                    source_type="journal",
                    title=f"{j.kind} · {j.occurred_at.date().isoformat()}",
                    snippet=j.note,
                    href=self._href("journal", j.id),
                    at=j.occurred_at,
                    pinned=("journal", j.id) in pinned_keys,
                )
            )

        reports = await self.session.execute(
            select(OsDailyReport)
            .where(OsDailyReport.user_id == self.user_id)
            .order_by(OsDailyReport.report_date.desc())
            .limit(5)
        )
        for r in reports.scalars():
            items.append(
                OsDashboardRecentItem(
                    id=r.id,
                    source_type="report",
                    title=f"日报 {r.report_date.isoformat()}",
                    snippet=(r.content or "")[:120],
                    href=self._href("report", r.id),
                    at=r.updated_at,
                    pinned=("report", r.id) in pinned_keys,
                )
            )

        decisions = await self.session.execute(
            select(OsDecisionThread)
            .where(OsDecisionThread.user_id == self.user_id)
            .order_by(OsDecisionThread.updated_at.desc())
            .limit(5)
        )
        for d in decisions.scalars():
            items.append(
                OsDashboardRecentItem(
                    id=d.id,
                    source_type="decision",
                    title=d.question[:80],
                    snippet=d.constraints,
                    href=self._href("decision", d.id),
                    at=d.updated_at,
                    pinned=("decision", d.id) in pinned_keys,
                )
            )

        items.sort(key=lambda x: x.at or datetime.min, reverse=True)
        return items[:12]

    def _optimize_tips(
        self,
        *,
        profile,
        chat_n: int,
        note_n: int,
        journal_n: int,
        report_n: int,
        decision_n: int,
        prefs: dict,
    ) -> list[OsOptimizeTip]:
        tips: list[OsOptimizeTip] = []

        if not (profile.goals or "").strip():
            tips.append(
                OsOptimizeTip(
                    id="set-goals",
                    title="先写清目标与底线",
                    body="个人 OS 的人设与目标是后续对话/日报/决策的锚点。先写 3–5 条可验证目标。",
                    priority="high",
                    action_href="/os/memory",
                    action_label="去完善档案",
                )
            )

        if journal_n < 7:
            tips.append(
                OsOptimizeTip(
                    id="warmup-journal",
                    title="先攒 2–4 周生活数据",
                    body=(
                        f"当前日志 {journal_n} 条。播客方法是先开图攒数据，"
                        "再让多模型分析大事，而不是空数据重注。"
                    ),
                    priority="high",
                    action_href="/os/journal",
                    action_label="记一条日志",
                )
            )
        elif report_n == 0:
            tips.append(
                OsOptimizeTip(
                    id="first-report",
                    title="用日志生成第一份日报",
                    body="数据够用后，让 AI 出日报并手动纠错反馈，形成调参闭环。",
                    priority="high",
                    action_href="/os/reports",
                    action_label="生成日报",
                )
            )

        compare = list(prefs.get("compare_provider_ids") or [])
        if len(compare) < 2:
            tips.append(
                OsOptimizeTip(
                    id="multi-model",
                    title="配置 2–3 个对比模型",
                    body="同一问题问多个模型再取上中下策。可用免费/按次模型起步，不必模型忠诚。",
                    priority="medium",
                    action_href="/os/settings",
                    action_label="模型偏好",
                )
            )

        if report_n > 0 and not (profile.report_prompt_appendix or "").strip():
            tips.append(
                OsOptimizeTip(
                    id="report-feedback",
                    title="给日报打分并写入调参",
                    body="反馈会进入报告附录，影响后续生成语气与重点——这是「训练你的 OS」。",
                    priority="medium",
                    action_href="/os/reports",
                    action_label="去反馈",
                )
            )

        if decision_n == 0 and journal_n >= 7:
            tips.append(
                OsOptimizeTip(
                    id="first-decision",
                    title="大事用开图模板跑多模型",
                    body="先填资源/约束/样本/版本，再出上中下策；AI 出草案，你拍板。",
                    priority="medium",
                    action_href="/os/decisions",
                    action_label="开图决策",
                )
            )

        if note_n == 0 and chat_n > 3:
            tips.append(
                OsOptimizeTip(
                    id="capture-notes",
                    title="把碎片沉淀成笔记",
                    body="对话会过期；把原则、案例、benchmark 写入笔记，才能成为可迁移数据资产。",
                    priority="low",
                    action_href="/os/memory",
                    action_label="写笔记",
                )
            )

        tips.append(
            OsOptimizeTip(
                id="export-assets",
                title="定期导出 Markdown ZIP",
                body="数据资产比模型忠诚更重要。设置页可一键导出档案/日志/日报/决策。",
                priority="low",
                action_href="/os/settings",
                action_label="去导出",
            )
        )

        tips.append(
            OsOptimizeTip(
                id="human-final-say",
                title="人保留最终判断权",
                body="表面「信 AI」实质是多模型草案 + 你拍板。禁止自动替你下人生注。",
                priority="low",
            )
        )

        # 高优先在前
        order = {"high": 0, "medium": 1, "low": 2}
        tips.sort(key=lambda t: order.get(t.priority, 9))
        return tips

    async def list_pins(self) -> list[OsDashboardPinResponse]:
        result = await self.session.execute(
            select(OsDashboardPin)
            .where(OsDashboardPin.user_id == self.user_id)
            .order_by(OsDashboardPin.sort_order.asc(), OsDashboardPin.id.desc())
        )
        return [self._pin_response(p) for p in result.scalars()]

    async def _resolve_source(
        self, source_type: str, source_id: int
    ) -> tuple[str, str | None]:
        if source_type == "chat_session":
            row = await self.session.get(OsChatSession, source_id)
            if row is None or row.user_id != self.user_id:
                raise HTTPException(404, "对话不存在")
            return row.title, None
        if source_type == "note":
            row = await self.session.get(OsNote, source_id)
            if row is None or row.user_id != self.user_id:
                raise HTTPException(404, "笔记不存在")
            return row.title, (row.body or "")[:200]
        if source_type == "journal":
            row = await self.session.get(OsJournalEntry, source_id)
            if row is None or row.user_id != self.user_id:
                raise HTTPException(404, "日志不存在")
            title = f"{row.kind} · {row.occurred_at.date().isoformat()}"
            return title, row.note
        if source_type == "report":
            row = await self.session.get(OsDailyReport, source_id)
            if row is None or row.user_id != self.user_id:
                raise HTTPException(404, "日报不存在")
            return f"日报 {row.report_date.isoformat()}", (row.content or "")[:200]
        if source_type == "decision":
            row = await self.session.get(OsDecisionThread, source_id)
            if row is None or row.user_id != self.user_id:
                raise HTTPException(404, "决策不存在")
            return row.question[:200], row.constraints
        raise HTTPException(400, f"不支持的类型：{source_type}")

    async def pin(self, payload: OsDashboardPinCreate) -> OsDashboardPinResponse:
        title, snippet = await self._resolve_source(
            payload.source_type, payload.source_id
        )
        if payload.title and payload.title.strip():
            title = payload.title.strip()[:240]
        if payload.snippet is not None:
            snippet = payload.snippet

        pin = OsDashboardPin(
            user_id=self.user_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            title=title[:240],
            snippet=snippet,
            sort_order=0,
        )
        self.session.add(pin)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            result = await self.session.execute(
                select(OsDashboardPin).where(
                    OsDashboardPin.user_id == self.user_id,
                    OsDashboardPin.source_type == payload.source_type,
                    OsDashboardPin.source_id == payload.source_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                raise HTTPException(409, "钉选冲突") from None
            return self._pin_response(existing)
        await self.session.refresh(pin)
        return self._pin_response(pin)

    async def update_pin(
        self, pin_id: int, payload: OsDashboardPinUpdate
    ) -> OsDashboardPinResponse:
        pin = await self.session.get(OsDashboardPin, pin_id)
        if pin is None or pin.user_id != self.user_id:
            raise HTTPException(404, "钉选不存在")
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(pin, key, value)
        await self.session.commit()
        await self.session.refresh(pin)
        return self._pin_response(pin)

    async def unpin(self, pin_id: int) -> None:
        pin = await self.session.get(OsDashboardPin, pin_id)
        if pin is None or pin.user_id != self.user_id:
            raise HTTPException(404, "钉选不存在")
        await self.session.delete(pin)
        await self.session.commit()

    async def unpin_by_source(self, source_type: str, source_id: int) -> None:
        result = await self.session.execute(
            select(OsDashboardPin).where(
                OsDashboardPin.user_id == self.user_id,
                OsDashboardPin.source_type == source_type,
                OsDashboardPin.source_id == source_id,
            )
        )
        pin = result.scalar_one_or_none()
        if pin is None:
            raise HTTPException(404, "钉选不存在")
        await self.session.delete(pin)
        await self.session.commit()
