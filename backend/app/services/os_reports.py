"""个人 AI OS 日报服务。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_os import OsDailyReport
from app.schemas.personal_os import (
    OsDailyReportResponse,
    OsReportFeedbackRequest,
    OsReportGenerateRequest,
)
from app.services.os_journal import OsJournalService
from app.services.os_profile import OsProfileService
from app.services.prompt_llm import PromptLLMService


def _format_entries(entries) -> str:
    if not entries:
        return "（当日无日志条目）"
    lines: list[str] = []
    for e in entries:
        lines.append(
            f"- [{e.kind}] {e.occurred_at.isoformat()} payload={e.payload} note={e.note or ''}"
        )
    return "\n".join(lines)


class OsReportsService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.llm = PromptLLMService(session, user_id)
        self.profiles = OsProfileService(session, user_id)
        self.journal = OsJournalService(session, user_id)

    async def list(self, limit: int = 30) -> list[OsDailyReportResponse]:
        await self.profiles.require_module("reports")
        result = await self.session.execute(
            select(OsDailyReport)
            .where(OsDailyReport.user_id == self.user_id)
            .order_by(OsDailyReport.report_date.desc())
            .limit(min(limit, 100))
        )
        return [OsDailyReportResponse.model_validate(r) for r in result.scalars()]

    async def get(self, report_id: int) -> OsDailyReportResponse:
        await self.profiles.require_module("reports")
        report = await self.session.get(OsDailyReport, report_id)
        if report is None or report.user_id != self.user_id:
            raise HTTPException(404, "日报不存在")
        return OsDailyReportResponse.model_validate(report)

    def _build_prompts(
        self, profile, day: date, entries_text: str
    ) -> tuple[str, str]:
        appendix = (profile.report_prompt_appendix or "").strip()
        system = (
            "你是个人 AI 操作系统的日报教练。"
            "根据用户当日日志，输出结构化 Markdown 日报："
            "1) 今日摘要 2) 饮食/训练/睡眠/日程要点 3) 做得好的 4) 可改进 5) 明日建议。"
            "语气务实，避免空洞鸡汤。"
        )
        if appendix:
            system += f"\n\n【用户调参反馈】\n{appendix}"
        archive = []
        if profile.display_name:
            archive.append(f"称呼：{profile.display_name}")
        if profile.goals:
            archive.append(f"目标：{profile.goals}")
        if profile.health_baseline:
            archive.append(f"健康基线：{profile.health_baseline}")
        user = (
            f"日期：{day.isoformat()}\n"
            f"档案：\n{chr(10).join(archive) or '（无）'}\n\n"
            f"当日日志：\n{entries_text}\n\n请生成日报。"
        )
        return system, user

    async def generate(
        self, payload: OsReportGenerateRequest
    ) -> OsDailyReportResponse:
        await self.profiles.require_module("reports")
        profile = await self.profiles.ensure_profile()
        day = payload.report_date or datetime.now(timezone.utc).date()
        entries = await self.journal.entries_for_day(day)
        system, user = self._build_prompts(profile, day, _format_entries(entries))
        provider_id = payload.provider_id
        if provider_id is None:
            provider_id = (profile.model_prefs or {}).get("default_provider_id")
        content = await self.llm.run_completion(
            system, user, provider_id=provider_id
        )
        return await self._upsert(day, content.strip(), provider_id, [e.id for e in entries])

    async def generate_stream(
        self, payload: OsReportGenerateRequest
    ) -> AsyncIterator[dict]:
        await self.profiles.require_module("reports")
        profile = await self.profiles.ensure_profile()
        day = payload.report_date or datetime.now(timezone.utc).date()
        entries = await self.journal.entries_for_day(day)
        system, user = self._build_prompts(profile, day, _format_entries(entries))
        provider_id = payload.provider_id
        if provider_id is None:
            provider_id = (profile.model_prefs or {}).get("default_provider_id")
        yield {"type": "start"}
        parts: list[str] = []
        async for delta in self.llm.stream_completion(
            system, user, provider_id=provider_id
        ):
            if not delta:
                yield {"type": "status", "message": "正在生成日报…"}
                continue
            parts.append(delta)
            yield {"type": "delta", "text": delta}
        content = "".join(parts).strip()
        if not content:
            raise HTTPException(502, "模型未返回有效日报")
        report = await self._upsert(
            day, content, provider_id, [e.id for e in entries]
        )
        yield {
            "type": "done",
            "result": content,
            "run_id": report.id,
            "report_id": report.id,
        }

    async def _upsert(
        self,
        day: date,
        content: str,
        provider_id: int | None,
        entry_ids: list[int],
    ) -> OsDailyReport:
        result = await self.session.execute(
            select(OsDailyReport).where(
                OsDailyReport.user_id == self.user_id,
                OsDailyReport.report_date == day,
            )
        )
        report = result.scalar_one_or_none()
        if report is None:
            report = OsDailyReport(
                user_id=self.user_id,
                report_date=day,
                content=content,
                provider_id=provider_id,
                entry_ids=entry_ids,
            )
            self.session.add(report)
        else:
            report.content = content
            report.provider_id = provider_id
            report.entry_ids = entry_ids
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def feedback(
        self, report_id: int, payload: OsReportFeedbackRequest
    ) -> OsDailyReportResponse:
        await self.profiles.require_module("reports")
        report = await self.session.get(OsDailyReport, report_id)
        if report is None or report.user_id != self.user_id:
            raise HTTPException(404, "日报不存在")
        report.feedback_score = payload.score
        report.feedback_note = payload.note
        await self.session.commit()
        await self.session.refresh(report)
        if payload.apply_to_prompt:
            note = (payload.note or "").strip() or "（用户未写说明，仅按评分调参）"
            await self.profiles.append_tuning_note(
                field="report_prompt_appendix",
                line=f"[日报 {report.report_date.isoformat()} · 评分{payload.score}] {note}",
            )
        return OsDailyReportResponse.model_validate(report)
