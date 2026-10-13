"""个人 AI OS 数据导出（Markdown ZIP）。"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_os import (
    OsDailyReport,
    OsDecisionOption,
    OsDecisionRun,
    OsDecisionThread,
    OsJournalEntry,
    OsNote,
    OsProfile,
)
from app.services.os_profile import OsProfileService


def _safe_name(text: str, fallback: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in (text or "")[:60])
    return cleaned.strip("._") or fallback


class OsExportService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.profiles = OsProfileService(session, user_id)

    async def build_zip(self) -> bytes:
        profile = await self.profiles.ensure_profile()
        buf = io.BytesIO()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.md", self._readme(stamp))
            zf.writestr("00-profile.md", self._profile_md(profile))
            await self._write_notes(zf)
            await self._write_journal(zf)
            await self._write_reports(zf)
            await self._write_decisions(zf)

        return buf.getvalue()

    def _readme(self, stamp: str) -> str:
        return (
            "# 个人 AI OS 数据导出\n\n"
            f"- 导出时间（UTC）：{stamp}\n"
            f"- user_id：{self.user_id}\n\n"
            "本包为可迁移 Markdown 资产，不绑定特定模型供应商。\n"
            "健康与决策内容仅供个人复盘，不构成医疗或投资建议。\n"
        )

    def _profile_md(self, profile: OsProfile) -> str:
        return "\n".join(
            [
                "# 档案\n",
                f"- 称呼：{profile.display_name or '（未设）'}",
                f"- 目标：\n\n{profile.goals or '（未设）'}\n",
                f"- 健康基线：\n\n```json\n"
                f"{json.dumps(profile.health_baseline or {}, ensure_ascii=False, indent=2)}\n```\n",
                f"- 系统提示词：\n\n{profile.system_prompt}\n",
                f"- 记忆策略：\n\n```json\n"
                f"{json.dumps(profile.memory_policy or {}, ensure_ascii=False, indent=2)}\n```\n",
                f"- 模块开关：\n\n```json\n"
                f"{json.dumps(profile.module_flags or {}, ensure_ascii=False, indent=2)}\n```\n",
                f"- 模型偏好：\n\n```json\n"
                f"{json.dumps(profile.model_prefs or {}, ensure_ascii=False, indent=2)}\n```\n",
                "## 日报调参附录\n\n"
                f"{profile.report_prompt_appendix or '（无）'}\n",
                "## 决策调参附录\n\n"
                f"{getattr(profile, 'decision_prompt_appendix', None) or '（无）'}\n",
            ]
        )

    async def _write_notes(self, zf: zipfile.ZipFile) -> None:
        result = await self.session.execute(
            select(OsNote)
            .where(OsNote.user_id == self.user_id)
            .order_by(OsNote.updated_at.desc())
            .limit(5000)
        )
        notes = list(result.scalars())
        index_lines = ["# 笔记索引\n"]
        for note in notes:
            name = f"notes/{note.id}-{_safe_name(note.title, 'note')}.md"
            tags = ", ".join(note.tags or [])
            body = (
                f"# {note.title}\n\n"
                f"- tags: {tags or '（无）'}\n"
                f"- updated: {note.updated_at.isoformat() if note.updated_at else ''}\n\n"
                f"{note.body}\n"
            )
            zf.writestr(name, body)
            index_lines.append(f"- [{note.title}]({name})")
        zf.writestr("notes/README.md", "\n".join(index_lines) + "\n")

    async def _write_journal(self, zf: zipfile.ZipFile) -> None:
        result = await self.session.execute(
            select(OsJournalEntry)
            .where(OsJournalEntry.user_id == self.user_id)
            .order_by(OsJournalEntry.occurred_at.desc())
            .limit(2000)
        )
        lines = ["# 生活日志\n"]
        for e in result.scalars():
            day = e.occurred_at.date().isoformat() if e.occurred_at else "unknown"
            lines.append(f"## {day} · {e.kind} (#{e.id})\n")
            lines.append(f"- 时间：{e.occurred_at.isoformat() if e.occurred_at else ''}")
            if e.note:
                lines.append(f"- 备注：{e.note}")
            lines.append(
                f"- payload：\n\n```json\n"
                f"{json.dumps(e.payload or {}, ensure_ascii=False, indent=2)}\n```\n"
            )
        zf.writestr("journal.md", "\n".join(lines))

    async def _write_reports(self, zf: zipfile.ZipFile) -> None:
        result = await self.session.execute(
            select(OsDailyReport)
            .where(OsDailyReport.user_id == self.user_id)
            .order_by(OsDailyReport.report_date.desc())
            .limit(500)
        )
        for r in result.scalars():
            day = r.report_date.isoformat()
            fb = ""
            if r.feedback_score is not None:
                fb = f"\n\n---\n反馈评分：{r.feedback_score}\n{r.feedback_note or ''}\n"
            zf.writestr(
                f"reports/{day}.md",
                f"# 日报 {day}\n\n{r.content}{fb}\n",
            )

    async def _write_decisions(self, zf: zipfile.ZipFile) -> None:
        result = await self.session.execute(
            select(OsDecisionThread)
            .where(OsDecisionThread.user_id == self.user_id)
            .order_by(OsDecisionThread.updated_at.desc())
            .limit(200)
        )
        for thread in result.scalars():
            run_result = await self.session.execute(
                select(OsDecisionRun)
                .where(OsDecisionRun.thread_id == thread.id)
                .order_by(OsDecisionRun.id.desc())
                .limit(1)
            )
            run = run_result.scalar_one_or_none()
            parts = [
                f"# 决策 #{thread.id}\n",
                f"- 状态：{thread.status}",
                f"- 问题：{thread.question}",
                f"- 约束：{thread.constraints or '（无）'}",
                f"- 选择 option_id：{thread.chosen_option_id or '（未选）'}",
                f"- 结果备注：{thread.outcome_note or '（无）'}\n",
            ]
            if run is not None:
                parts.append(f"## 最新运行 #{run.id}\n")
                parts.append(f"{run.summary or ''}\n")
                opts = await self.session.execute(
                    select(OsDecisionOption)
                    .where(OsDecisionOption.run_id == run.id)
                    .order_by(OsDecisionOption.id.asc())
                )
                for o in opts.scalars():
                    parts.append(
                        f"### {o.tier} · {o.title}"
                        f"{'（已选）' if o.selected else ''}\n\n"
                        f"{o.content}\n"
                    )
                    if o.feedback_score is not None:
                        parts.append(
                            f"- 反馈：{o.feedback_score} {o.feedback_note or ''}\n"
                        )
            name = (
                f"decisions/{thread.id}-"
                f"{_safe_name(thread.question, 'decision')}.md"
            )
            zf.writestr(name, "\n".join(parts))
