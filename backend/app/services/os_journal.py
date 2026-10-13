"""个人 AI OS 生活日志服务。"""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_os import OsJournalEntry
from app.schemas.personal_os import (
    OsJournalCreate,
    OsJournalResponse,
    OsJournalUpdate,
)
from app.services.os_profile import OsProfileService


class OsJournalService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.profiles = OsProfileService(session, user_id)

    async def _get_owned(self, entry_id: int) -> OsJournalEntry:
        entry = await self.session.get(OsJournalEntry, entry_id)
        if entry is None or entry.user_id != self.user_id:
            raise HTTPException(404, "日志不存在")
        return entry

    async def list(
        self,
        *,
        kind: str | None = None,
        day: date | None = None,
        limit: int = 100,
    ) -> list[OsJournalResponse]:
        await self.profiles.require_module("journal")
        stmt = select(OsJournalEntry).where(OsJournalEntry.user_id == self.user_id)
        if kind:
            stmt = stmt.where(OsJournalEntry.kind == kind)
        if day is not None:
            start = datetime.combine(day, time.min, tzinfo=timezone.utc)
            end = datetime.combine(day, time.max, tzinfo=timezone.utc)
            stmt = stmt.where(
                OsJournalEntry.occurred_at >= start,
                OsJournalEntry.occurred_at <= end,
            )
        stmt = stmt.order_by(OsJournalEntry.occurred_at.desc()).limit(min(limit, 500))
        result = await self.session.execute(stmt)
        return [OsJournalResponse.model_validate(e) for e in result.scalars()]

    async def create(self, payload: OsJournalCreate) -> OsJournalResponse:
        await self.profiles.require_module("journal")
        entry = OsJournalEntry(
            user_id=self.user_id,
            kind=payload.kind,
            occurred_at=payload.occurred_at,
            payload=dict(payload.payload or {}),
            note=payload.note,
            media_refs=list(payload.media_refs or []),
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return OsJournalResponse.model_validate(entry)

    async def update(
        self, entry_id: int, payload: OsJournalUpdate
    ) -> OsJournalResponse:
        await self.profiles.require_module("journal")
        entry = await self._get_owned(entry_id)
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(entry, key, value)
        await self.session.commit()
        await self.session.refresh(entry)
        return OsJournalResponse.model_validate(entry)

    async def delete(self, entry_id: int) -> None:
        await self.profiles.require_module("journal")
        entry = await self._get_owned(entry_id)
        await self.session.delete(entry)
        await self.session.commit()

    async def entries_for_day(self, day: date) -> list[OsJournalEntry]:
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)
        result = await self.session.execute(
            select(OsJournalEntry)
            .where(
                OsJournalEntry.user_id == self.user_id,
                OsJournalEntry.occurred_at >= start,
                OsJournalEntry.occurred_at <= end,
            )
            .order_by(OsJournalEntry.occurred_at.asc())
        )
        return list(result.scalars())
