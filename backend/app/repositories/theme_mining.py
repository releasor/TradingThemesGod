"""题材挖掘快照与点评仓储。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.theme_mining import ThemeMiningCard, ThemeMiningMember, ThemeMiningNote


@dataclass
class MemberWrite:
    """写入成份股明细。"""

    stock_id: int
    score: int
    rank: int
    role_tag: str
    metrics: dict[str, Any] = field(default_factory=dict)
    concept_node_id: int | None = None


@dataclass
class CardWrite:
    """写入挖掘卡（含 members）。"""

    theme_id: int
    mining_type: str
    score: int
    rank: int
    lifecycle_stage: str
    strength_score: int
    rationale: str
    score_breakdown: dict[str, Any] = field(default_factory=dict)
    degraded: bool = False
    missing_metrics: list[Any] = field(default_factory=list)
    members: list[MemberWrite] = field(default_factory=list)


class ThemeMiningRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def replace_day_cards(
        self,
        trade_date: date,
        cards_with_members: list[CardWrite],
    ) -> int:
        """删除当日旧卡（members CASCADE）后整批插入。"""
        await self.session.execute(
            delete(ThemeMiningCard).where(ThemeMiningCard.trade_date == trade_date)
        )
        await self.session.flush()

        for payload in cards_with_members:
            card = ThemeMiningCard(
                trade_date=trade_date,
                theme_id=payload.theme_id,
                mining_type=payload.mining_type,
                score=payload.score,
                rank=payload.rank,
                lifecycle_stage=payload.lifecycle_stage,
                strength_score=payload.strength_score,
                rationale=payload.rationale,
                score_breakdown=payload.score_breakdown,
                degraded=payload.degraded,
                missing_metrics=payload.missing_metrics,
            )
            self.session.add(card)
            await self.session.flush()
            for member in payload.members:
                self.session.add(
                    ThemeMiningMember(
                        card_id=card.id,
                        stock_id=member.stock_id,
                        concept_node_id=member.concept_node_id,
                        score=member.score,
                        rank=member.rank,
                        role_tag=member.role_tag,
                        metrics=member.metrics,
                    )
                )
        await self.session.flush()
        return len(cards_with_members)

    async def list_cards(self, trade_date: date) -> list[ThemeMiningCard]:
        result = await self.session.scalars(
            select(ThemeMiningCard)
            .where(ThemeMiningCard.trade_date == trade_date)
            .order_by(ThemeMiningCard.mining_type, ThemeMiningCard.rank)
        )
        return list(result.all())

    async def list_board(
        self, trade_date: date
    ) -> dict[str, list[ThemeMiningCard]]:
        """按 mining_type 分组返回当日卡片。"""
        cards = await self.list_cards(trade_date)
        board: dict[str, list[ThemeMiningCard]] = {
            "low_branch": [],
            "catch_up": [],
            "hidden_leader": [],
        }
        for card in cards:
            bucket = board.setdefault(card.mining_type, [])
            bucket.append(card)
        return board

    async def get_card(self, card_id: int) -> ThemeMiningCard | None:
        return await self.session.get(ThemeMiningCard, card_id)

    async def list_members(self, card_ids: list[int]) -> list[ThemeMiningMember]:
        if not card_ids:
            return []
        result = await self.session.scalars(
            select(ThemeMiningMember)
            .where(ThemeMiningMember.card_id.in_(card_ids))
            .order_by(ThemeMiningMember.card_id, ThemeMiningMember.rank)
        )
        return list(result.all())

    async def get_note(
        self, card_id: int, user_id: int
    ) -> ThemeMiningNote | None:
        return await self.session.scalar(
            select(ThemeMiningNote).where(
                ThemeMiningNote.card_id == card_id,
                ThemeMiningNote.user_id == user_id,
            )
        )

    async def upsert_note(
        self,
        *,
        card_id: int,
        user_id: int,
        status: str,
        content_md: str = "",
        model_name: str | None = None,
        error: str | None = None,
    ) -> ThemeMiningNote:
        row = await self.get_note(card_id, user_id)
        if row is None:
            row = ThemeMiningNote(card_id=card_id, user_id=user_id)
            self.session.add(row)

        row.status = status
        row.content_md = content_md
        row.model_name = model_name
        row.error = error
        await self.session.flush()
        return row
