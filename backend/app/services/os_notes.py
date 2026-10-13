"""个人 AI OS 笔记服务。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_os import OsNote
from app.schemas.personal_os import OsNoteCreate, OsNoteResponse, OsNoteUpdate
from app.services.os_profile import OsProfileService


class OsNotesService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.profiles = OsProfileService(session, user_id)

    async def _get_owned(self, note_id: int) -> OsNote:
        note = await self.session.get(OsNote, note_id)
        if note is None or note.user_id != self.user_id:
            raise HTTPException(404, "笔记不存在")
        return note

    async def list(self, q: str | None = None, limit: int = 50) -> list[OsNoteResponse]:
        await self.profiles.require_module("memory")
        stmt = select(OsNote).where(OsNote.user_id == self.user_id)
        if q and q.strip():
            like = f"%{q.strip()}%"
            stmt = stmt.where(or_(OsNote.title.like(like), OsNote.body.like(like)))
        stmt = stmt.order_by(OsNote.updated_at.desc()).limit(min(limit, 200))
        result = await self.session.execute(stmt)
        return [OsNoteResponse.model_validate(n) for n in result.scalars()]

    async def search_for_context(self, query: str, top_k: int) -> list[OsNote]:
        if top_k <= 0:
            return []
        stmt = select(OsNote).where(OsNote.user_id == self.user_id)
        if query.strip():
            like = f"%{query.strip()[:80]}%"
            stmt = stmt.where(or_(OsNote.title.like(like), OsNote.body.like(like)))
        stmt = stmt.order_by(OsNote.updated_at.desc()).limit(top_k)
        result = await self.session.execute(stmt)
        notes = list(result.scalars())
        if notes:
            return notes
        # 无关键词命中时回退最近笔记
        fallback = await self.session.execute(
            select(OsNote)
            .where(OsNote.user_id == self.user_id)
            .order_by(OsNote.updated_at.desc())
            .limit(top_k)
        )
        return list(fallback.scalars())

    async def create(self, payload: OsNoteCreate) -> OsNoteResponse:
        await self.profiles.require_module("memory")
        note = OsNote(
            user_id=self.user_id,
            title=payload.title.strip(),
            body=payload.body.strip(),
            tags=list(payload.tags or []),
        )
        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)
        return OsNoteResponse.model_validate(note)

    async def update(self, note_id: int, payload: OsNoteUpdate) -> OsNoteResponse:
        await self.profiles.require_module("memory")
        note = await self._get_owned(note_id)
        data = payload.model_dump(exclude_unset=True)
        if "title" in data and data["title"] is not None:
            data["title"] = data["title"].strip()
        if "body" in data and data["body"] is not None:
            data["body"] = data["body"].strip()
        for key, value in data.items():
            setattr(note, key, value)
        await self.session.commit()
        await self.session.refresh(note)
        return OsNoteResponse.model_validate(note)

    async def delete(self, note_id: int) -> None:
        await self.profiles.require_module("memory")
        note = await self._get_owned(note_id)
        await self.session.delete(note)
        await self.session.commit()
