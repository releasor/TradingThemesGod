"""Prompt 自由聊天服务。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_workbench import PromptChatMessage, PromptChatSession
from app.schemas.prompt_workbench import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.services.prompt_llm import PromptLLMService
from app.services.prompt_templates import build_chat_system

_HISTORY_LIMIT = 20


class PromptChatService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.llm = PromptLLMService(session, user_id)

    async def list_sessions(self) -> list[ChatSessionResponse]:
        result = await self.session.execute(
            select(PromptChatSession)
            .where(PromptChatSession.user_id == self.user_id)
            .order_by(PromptChatSession.updated_at.desc())
        )
        return [
            ChatSessionResponse.model_validate(s) for s in result.scalars()
        ]

    async def create_session(
        self, payload: ChatSessionCreate
    ) -> ChatSessionResponse:
        session = PromptChatSession(
            user_id=self.user_id,
            title=(payload.title or "新对话").strip() or "新对话",
            provider_id=payload.provider_id,
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return ChatSessionResponse.model_validate(session)

    async def _get_owned(self, session_id: int) -> PromptChatSession:
        session = await self.session.get(PromptChatSession, session_id)
        if session is None or session.user_id != self.user_id:
            raise HTTPException(404, "会话不存在")
        return session

    async def update_session(
        self, session_id: int, payload: ChatSessionUpdate
    ) -> ChatSessionResponse:
        session = await self._get_owned(session_id)
        data = payload.model_dump(exclude_unset=True)
        if "title" in data and data["title"] is not None:
            data["title"] = data["title"].strip()
        for key, value in data.items():
            setattr(session, key, value)
        await self.session.commit()
        await self.session.refresh(session)
        return ChatSessionResponse.model_validate(session)

    async def delete_session(self, session_id: int) -> None:
        session = await self._get_owned(session_id)
        await self.session.delete(session)
        await self.session.commit()

    async def list_messages(self, session_id: int) -> list[ChatMessageResponse]:
        await self._get_owned(session_id)
        result = await self.session.execute(
            select(PromptChatMessage)
            .where(PromptChatMessage.session_id == session_id)
            .order_by(PromptChatMessage.id.asc())
        )
        return [
            ChatMessageResponse.model_validate(m) for m in result.scalars()
        ]

    async def send_message(
        self, session_id: int, payload: ChatMessageCreate
    ) -> ChatMessageResponse:
        session = await self._get_owned(session_id)
        user_msg = PromptChatMessage(
            session_id=session_id,
            role="user",
            content=payload.content.strip(),
        )
        self.session.add(user_msg)
        await self.session.flush()

        result = await self.session.execute(
            select(PromptChatMessage)
            .where(PromptChatMessage.session_id == session_id)
            .order_by(PromptChatMessage.id.asc())
        )
        msgs = list(result.scalars())[-_HISTORY_LIMIT:]

        # Fold history into a single user blob after system (adapter is system+user)
        transcript_parts: list[str] = []
        for m in msgs:
            label = "用户" if m.role == "user" else "助手"
            transcript_parts.append(f"{label}：{m.content}")
        user_blob = "\n\n".join(transcript_parts)

        provider_id = payload.provider_id
        if provider_id is None:
            provider_id = session.provider_id

        reply = await self.llm.run_completion(
            build_chat_system(),
            user_blob,
            provider_id=provider_id,
        )
        assistant = PromptChatMessage(
            session_id=session_id,
            role="assistant",
            content=reply.strip(),
        )
        self.session.add(assistant)
        await self.session.commit()
        await self.session.refresh(assistant)
        return ChatMessageResponse.model_validate(assistant)
