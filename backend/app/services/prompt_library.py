"""Prompt 库 CRUD。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_workbench import PromptItem
from app.schemas.prompt_workbench import (
    PromptItemCreate,
    PromptItemResponse,
    PromptItemUpdate,
)


class PromptLibraryService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    def _to_response(self, item: PromptItem) -> PromptItemResponse:
        tags = item.tags if isinstance(item.tags, list) else []
        return PromptItemResponse(
            id=item.id,
            user_id=item.user_id,
            title=item.title,
            body=item.body,
            category=item.category,
            tags=[str(t) for t in tags],
            enabled=item.enabled,
            pinned=item.pinned,
            sort_order=item.sort_order,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    async def list(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        enabled: bool | None = None,
    ) -> list[PromptItemResponse]:
        stmt = select(PromptItem).where(PromptItem.user_id == self.user_id)
        if enabled is not None:
            stmt = stmt.where(PromptItem.enabled.is_(enabled))
        if category:
            stmt = stmt.where(PromptItem.category == category)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                (PromptItem.title.like(like)) | (PromptItem.body.like(like))
            )
        stmt = stmt.order_by(
            PromptItem.pinned.desc(),
            PromptItem.sort_order.asc(),
            PromptItem.id.desc(),
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars())
        if tag:
            items = [
                i
                for i in items
                if isinstance(i.tags, list) and tag in [str(t) for t in i.tags]
            ]
        return [self._to_response(i) for i in items]

    async def create(self, payload: PromptItemCreate) -> PromptItemResponse:
        item = PromptItem(
            user_id=self.user_id,
            title=payload.title.strip(),
            body=payload.body,
            category=payload.category,
            tags=list(payload.tags),
            enabled=payload.enabled,
            pinned=payload.pinned,
            sort_order=payload.sort_order,
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return self._to_response(item)

    async def _get_owned(self, item_id: int) -> PromptItem:
        item = await self.session.get(PromptItem, item_id)
        if item is None or item.user_id != self.user_id:
            raise HTTPException(404, "Prompt 不存在")
        return item

    async def get(self, item_id: int) -> PromptItemResponse:
        return self._to_response(await self._get_owned(item_id))

    async def update(
        self, item_id: int, payload: PromptItemUpdate
    ) -> PromptItemResponse:
        item = await self._get_owned(item_id)
        data = payload.model_dump(exclude_unset=True)
        if "title" in data and data["title"] is not None:
            data["title"] = data["title"].strip()
        for key, value in data.items():
            setattr(item, key, value)
        await self.session.commit()
        await self.session.refresh(item)
        return self._to_response(item)

    async def delete(self, item_id: int) -> None:
        item = await self._get_owned(item_id)
        await self.session.delete(item)
        await self.session.commit()
