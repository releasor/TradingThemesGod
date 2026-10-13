"""个人 AI OS 对话服务。"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_os import OsChatMessage, OsChatSession, OsProfile
from app.schemas.personal_os import (
    OsChatMessageCreate,
    OsChatMessageResponse,
    OsChatSessionCreate,
    OsChatSessionResponse,
    OsChatSessionUpdate,
)
from app.services.os_notes import OsNotesService
from app.services.os_profile import OsProfileService
from app.services.prompt_llm import PromptLLMService


def _build_system(profile: OsProfile, notes_text: str) -> str:
    parts = [profile.system_prompt.strip() or "你是有帮助的个人助手。"]
    policy = profile.memory_policy or {}
    if policy.get("inject_profile", True):
        archive: list[str] = []
        if profile.display_name:
            archive.append(f"称呼：{profile.display_name}")
        if profile.goals:
            archive.append(f"目标：{profile.goals}")
        if profile.health_baseline:
            archive.append(f"健康基线：{profile.health_baseline}")
        if archive:
            parts.append("【用户档案】\n" + "\n".join(archive))
    if notes_text:
        parts.append("【相关笔记】\n" + notes_text)
    report_app = (profile.report_prompt_appendix or "").strip()
    decision_app = (getattr(profile, "decision_prompt_appendix", None) or "").strip()
    tuning: list[str] = []
    if report_app:
        tuning.append("日报偏好：\n" + report_app[-1200:])
    if decision_app:
        tuning.append("决策偏好：\n" + decision_app[-1200:])
    if tuning:
        parts.append("【用户调参反馈】\n" + "\n\n".join(tuning))
    parts.append(
        "请结合上述信息回答；若与当前问题无关可忽略。"
        "你出建议草案，最终决定权在用户。"
    )
    return "\n\n".join(parts)


class OsChatService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.llm = PromptLLMService(session, user_id)
        self.profiles = OsProfileService(session, user_id)
        self.notes = OsNotesService(session, user_id)

    async def list_sessions(self) -> list[OsChatSessionResponse]:
        await self.profiles.require_module("chat")
        result = await self.session.execute(
            select(OsChatSession)
            .where(OsChatSession.user_id == self.user_id)
            .order_by(OsChatSession.updated_at.desc())
        )
        return [OsChatSessionResponse.model_validate(s) for s in result.scalars()]

    async def create_session(
        self, payload: OsChatSessionCreate
    ) -> OsChatSessionResponse:
        await self.profiles.require_module("chat")
        profile = await self.profiles.ensure_profile()
        prefs = profile.model_prefs or {}
        provider_id = payload.provider_id
        if provider_id is None:
            provider_id = prefs.get("default_provider_id")
        session = OsChatSession(
            user_id=self.user_id,
            title=(payload.title or "新对话").strip() or "新对话",
            provider_id=provider_id,
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return OsChatSessionResponse.model_validate(session)

    async def _get_owned(self, session_id: int) -> OsChatSession:
        session = await self.session.get(OsChatSession, session_id)
        if session is None or session.user_id != self.user_id:
            raise HTTPException(404, "会话不存在")
        return session

    async def update_session(
        self, session_id: int, payload: OsChatSessionUpdate
    ) -> OsChatSessionResponse:
        await self.profiles.require_module("chat")
        session = await self._get_owned(session_id)
        data = payload.model_dump(exclude_unset=True)
        if "title" in data and data["title"] is not None:
            data["title"] = data["title"].strip()
        for key, value in data.items():
            setattr(session, key, value)
        await self.session.commit()
        await self.session.refresh(session)
        return OsChatSessionResponse.model_validate(session)

    async def delete_session(self, session_id: int) -> None:
        await self.profiles.require_module("chat")
        session = await self._get_owned(session_id)
        await self.session.delete(session)
        await self.session.commit()

    async def list_messages(self, session_id: int) -> list[OsChatMessageResponse]:
        await self.profiles.require_module("chat")
        await self._get_owned(session_id)
        result = await self.session.execute(
            select(OsChatMessage)
            .where(OsChatMessage.session_id == session_id)
            .order_by(OsChatMessage.id.asc())
        )
        return [OsChatMessageResponse.model_validate(m) for m in result.scalars()]

    async def _prepare_completion(
        self, session: OsChatSession, payload: OsChatMessageCreate
    ) -> tuple[str, str, int | None]:
        """保存用户消息并组装 prompt。用户消息会先 commit，避免流式失败后整段回滚像“没发出去”。"""
        profile = await self.profiles.ensure_profile()
        policy = profile.memory_policy or {}
        top_k = int(policy.get("note_top_k", 5) or 0)
        recent = int(policy.get("recent_turns", 20) or 20)

        user_msg = OsChatMessage(
            session_id=session.id,
            role="user",
            content=payload.content.strip(),
            provider_id=payload.provider_id,
        )
        self.session.add(user_msg)
        # 先落库用户消息，流式中途失败时用户侧仍能看到已发送内容
        await self.session.commit()

        notes = await self.notes.search_for_context(payload.content, top_k)
        notes_text = "\n\n".join(f"### {n.title}\n{n.body[:1200]}" for n in notes)
        system = _build_system(profile, notes_text)

        result = await self.session.execute(
            select(OsChatMessage)
            .where(OsChatMessage.session_id == session.id)
            .order_by(OsChatMessage.id.asc())
        )
        msgs = list(result.scalars())[-recent:]
        transcript_parts = [
            f"{'用户' if m.role == 'user' else '助手'}：{m.content}" for m in msgs
        ]
        user_blob = "\n\n".join(transcript_parts)

        provider_id = payload.provider_id
        if provider_id is None:
            provider_id = session.provider_id
        if provider_id is None:
            provider_id = (profile.model_prefs or {}).get("default_provider_id")

        return system, user_blob, provider_id

    async def send_message(
        self, session_id: int, payload: OsChatMessageCreate
    ) -> OsChatMessageResponse:
        await self.profiles.require_module("chat")
        session = await self._get_owned(session_id)
        system, user_blob, provider_id = await self._prepare_completion(
            session, payload
        )
        reply = await self.llm.run_completion(
            system, user_blob, provider_id=provider_id
        )
        assistant = OsChatMessage(
            session_id=session_id,
            role="assistant",
            content=reply.strip(),
            provider_id=provider_id,
        )
        self.session.add(assistant)
        await self.session.commit()
        await self.session.refresh(assistant)
        return OsChatMessageResponse.model_validate(assistant)

    async def send_message_stream(
        self, session_id: int, payload: OsChatMessageCreate
    ) -> AsyncIterator[dict]:
        await self.profiles.require_module("chat")
        session = await self._get_owned(session_id)
        system, user_blob, provider_id = await self._prepare_completion(
            session, payload
        )
        yield {"type": "start"}
        yield {"type": "status", "message": "正在请求模型…"}
        parts: list[str] = []
        try:
            async for delta in self.llm.stream_completion(
                system, user_blob, provider_id=provider_id
            ):
                if not delta:
                    yield {"type": "status", "message": "模型思考中…"}
                    continue
                parts.append(delta)
                yield {"type": "delta", "text": delta}
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            yield {"type": "error", "message": detail}
            return
        except Exception as exc:  # noqa: BLE001
            yield {"type": "error", "message": f"模型调用失败：{str(exc)[:300]}"}
            return

        content = "".join(parts).strip()
        if not content:
            # 流式无正文时回退一次非流式，避免前端“发了没回音”
            try:
                yield {"type": "status", "message": "流式无正文，改用普通补全…"}
                content = (
                    await self.llm.run_completion(
                        system, user_blob, provider_id=provider_id
                    )
                ).strip()
            except Exception as exc:  # noqa: BLE001
                yield {
                    "type": "error",
                    "message": f"模型未返回有效内容：{str(exc)[:200]}",
                }
                return
        if not content:
            yield {"type": "error", "message": "模型未返回有效内容"}
            return

        assistant = OsChatMessage(
            session_id=session_id,
            role="assistant",
            content=content,
            provider_id=provider_id,
        )
        self.session.add(assistant)
        await self.session.commit()
        await self.session.refresh(assistant)
        yield {
            "type": "done",
            "result": content,
            "message_id": assistant.id,
            "run_id": None,
        }
