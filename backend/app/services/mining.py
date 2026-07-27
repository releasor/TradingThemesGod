"""题材挖掘聚合服务。"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.concept_node import ConceptNode
from app.models.concept_node_stock import ConceptNodeStock
from app.models.short_term_signal import SectorRotationSnapshot
from app.models.stock import Stock
from app.models.theme import Theme
from app.models.theme_mining import ThemeMiningCard, ThemeMiningMember, ThemeMiningNote
from app.models.theme_stock import ThemeStock
from app.repositories.theme_mining import (
    CardWrite,
    MemberWrite,
    ThemeMiningRepository,
)
from app.schemas.mining import (
    MiningBoardResponse,
    MiningCardItem,
    MiningEnsureResponse,
    MiningMemberItem,
    MiningNoteResponse,
)
from app.services.mining_rules import StockMetric, ThemeMiningInput, mine_theme
from app.services.model_provider import ModelProviderService
from app.services.short_term import ShortTermService

logger = get_logger(__name__)

TOP_THEMES = 40
PREVIEW_MEMBER_LIMIT = 5
NOTE_TIMEOUT_SECONDS = 90

SYSTEM_PROMPT = """你是严谨的中国 A 股题材挖掘助手。只能依据用户提供的挖掘卡与成份股摘要撰写点评，不得编造未给出的价格或事件。
输出简短中文 Markdown（含「供参考，非投资建议」），聚焦该挖掘类型的可观察逻辑与风险。"""


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _note_to_response(row: ThemeMiningNote) -> MiningNoteResponse:
    return MiningNoteResponse(
        id=row.id,
        card_id=row.card_id,
        user_id=row.user_id,
        status=row.status,
        content_md=row.content_md or "",
        model_name=row.model_name,
        error=row.error,
    )


class MiningService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repo: ThemeMiningRepository | None = None,
    ):
        self.session = session
        self.repo = repo or ThemeMiningRepository(session)

    async def ensure(self, trade_date: date | None = None) -> MiningEnsureResponse:
        resolved = ShortTermService.resolve_trade_date(trade_date)
        snapshots = await self._load_top_snapshots(resolved)
        theme_ids = [snap.theme_id for snap in snapshots]
        stocks_by_theme = await self._load_theme_stocks(theme_ids)
        all_stock_ids = [
            stock.id
            for stocks in stocks_by_theme.values()
            for stock in stocks
        ]
        node_by_stock = await self._load_one_node_per_stock(all_stock_ids)

        drafts_by_type: dict[str, list[CardWrite]] = defaultdict(list)
        for snap in snapshots:
            stocks = stocks_by_theme.get(snap.theme_id, [])
            metrics = [
                StockMetric(
                    stock_id=stock.id,
                    rise_fall_pct=_float_or_none(stock.rise_fall_pct),
                    heat=None,
                    name=stock.name,
                )
                for stock in stocks
            ]
            drafts = mine_theme(
                ThemeMiningInput(
                    theme_id=snap.theme_id,
                    lifecycle_stage=snap.lifecycle_stage,
                    strength_score=snap.strength_score,
                    leader_clarity_score=snap.leader_clarity_score,
                    flow_score=snap.flow_score,
                    stocks=metrics,
                )
            )
            for draft in drafts:
                members = [
                    MemberWrite(
                        stock_id=member.stock_id,
                        score=member.score,
                        rank=member.rank,
                        role_tag=member.role_tag,
                        metrics=member.metrics,
                        concept_node_id=node_by_stock.get(member.stock_id),
                    )
                    for member in draft.members
                ]
                drafts_by_type[draft.mining_type].append(
                    CardWrite(
                        theme_id=snap.theme_id,
                        mining_type=draft.mining_type,
                        score=draft.score,
                        rank=0,
                        lifecycle_stage=draft.lifecycle_stage,
                        strength_score=draft.strength_score,
                        rationale=draft.rationale,
                        score_breakdown=draft.score_breakdown,
                        degraded=draft.degraded,
                        missing_metrics=draft.missing_metrics,
                        members=members,
                    )
                )

        writes: list[CardWrite] = []
        counts: dict[str, int] = {
            "low_branch": 0,
            "catch_up": 0,
            "hidden_leader": 0,
        }
        for mining_type, cards in drafts_by_type.items():
            cards.sort(key=lambda item: item.score, reverse=True)
            for index, card in enumerate(cards, start=1):
                card.rank = index
                writes.append(card)
            counts[mining_type] = len(cards)

        card_count = await self.repo.replace_day_cards(resolved, writes)
        await self.session.commit()

        return MiningEnsureResponse(
            trade_date=resolved,
            theme_count=len(snapshots),
            card_count=card_count,
            counts=counts,
        )

    async def get_board(self, trade_date: date | None = None) -> MiningBoardResponse:
        resolved = ShortTermService.resolve_trade_date(trade_date)
        board = await self.repo.list_board(resolved)
        all_cards = [
            card
            for cards in board.values()
            for card in cards
        ]
        items_by_type = await self._cards_to_items(
            all_cards, preview_limit=PREVIEW_MEMBER_LIMIT
        )
        return MiningBoardResponse(
            trade_date=resolved,
            low_branch=items_by_type.get("low_branch", []),
            catch_up=items_by_type.get("catch_up", []),
            hidden_leader=items_by_type.get("hidden_leader", []),
        )

    async def get_card(
        self, card_id: int, user_id: int | None = None
    ) -> MiningCardItem:
        card = await self.repo.get_card(card_id)
        if card is None:
            raise HTTPException(404, "挖掘卡不存在")
        items = await self._cards_to_items([card], preview_limit=None)
        item = items[card.mining_type][0]
        if user_id is not None:
            note = await self.repo.get_note(card_id, user_id)
            if note is not None:
                item.note = _note_to_response(note)
        return item

    async def ensure_note(self, card_id: int, user_id: int) -> MiningNoteResponse:
        card = await self.repo.get_card(card_id)
        if card is None:
            raise HTTPException(404, "挖掘卡不存在")

        existing = await self.repo.get_note(card_id, user_id)
        if existing is not None and existing.status == "success":
            return _note_to_response(existing)

        row = await self.repo.upsert_note(
            card_id=card_id,
            user_id=user_id,
            status="pending",
            content_md="",
            model_name=None,
            error=None,
        )
        await self.session.commit()
        asyncio.create_task(_generate_note_in_background(card_id, user_id))
        return _note_to_response(row)

    async def _load_top_snapshots(
        self, trade_date: date
    ) -> list[SectorRotationSnapshot]:
        result = await self.session.scalars(
            select(SectorRotationSnapshot)
            .where(SectorRotationSnapshot.trade_date == trade_date)
            .order_by(desc(SectorRotationSnapshot.strength_score))
            .limit(TOP_THEMES)
        )
        return list(result.all())

    async def _load_theme_names(self, theme_ids: list[int]) -> dict[int, str]:
        if not theme_ids:
            return {}
        result = await self.session.scalars(
            select(Theme).where(Theme.id.in_(theme_ids))
        )
        return {theme.id: theme.name for theme in result.all()}

    async def _load_theme_stocks(
        self, theme_ids: list[int]
    ) -> dict[int, list[Stock]]:
        if not theme_ids:
            return {}
        result = await self.session.execute(
            select(ThemeStock.theme_id, Stock)
            .join(Stock, Stock.id == ThemeStock.stock_id)
            .where(ThemeStock.theme_id.in_(theme_ids))
            .order_by(ThemeStock.theme_id, ThemeStock.sort_order)
        )
        grouped: dict[int, list[Stock]] = defaultdict(list)
        for theme_id, stock in result.all():
            grouped[theme_id].append(stock)
        return grouped

    async def _load_one_node_per_stock(
        self, stock_ids: list[int]
    ) -> dict[int, int]:
        if not stock_ids:
            return {}
        result = await self.session.execute(
            select(ConceptNodeStock.stock_id, ConceptNodeStock.node_id).where(
                ConceptNodeStock.stock_id.in_(stock_ids)
            )
        )
        mapping: dict[int, int] = {}
        for stock_id, node_id in result.all():
            if stock_id not in mapping:
                mapping[stock_id] = node_id
        return mapping

    async def _cards_to_items(
        self,
        cards: list[ThemeMiningCard],
        *,
        preview_limit: int | None,
    ) -> dict[str, list[MiningCardItem]]:
        if not cards:
            return {
                "low_branch": [],
                "catch_up": [],
                "hidden_leader": [],
            }

        card_ids = [card.id for card in cards]
        theme_ids = list({card.theme_id for card in cards})
        theme_names = await self._load_theme_names(theme_ids)
        members = await self.repo.list_members(card_ids)
        members_by_card: dict[int, list[ThemeMiningMember]] = defaultdict(list)
        for member in members:
            members_by_card[member.card_id].append(member)

        stock_ids = list({member.stock_id for member in members})
        node_ids = [
            member.concept_node_id
            for member in members
            if member.concept_node_id is not None
        ]
        stocks = await self._load_stocks(stock_ids)
        nodes = await self._load_nodes(node_ids)

        grouped: dict[str, list[MiningCardItem]] = defaultdict(list)
        for card in cards:
            card_members = members_by_card.get(card.id, [])
            visible = (
                card_members
                if preview_limit is None
                else card_members[:preview_limit]
            )
            grouped[card.mining_type].append(
                MiningCardItem(
                    id=card.id,
                    trade_date=card.trade_date,
                    theme_id=card.theme_id,
                    theme_name=theme_names.get(card.theme_id, f"题材{card.theme_id}"),
                    mining_type=card.mining_type,
                    score=card.score,
                    rank=card.rank,
                    lifecycle_stage=card.lifecycle_stage,
                    strength_score=card.strength_score,
                    rationale=card.rationale,
                    score_breakdown=dict(card.score_breakdown or {}),
                    degraded=card.degraded,
                    missing_metrics=list(card.missing_metrics or []),
                    member_count=len(card_members),
                    members=[
                        self._member_to_item(member, stocks, nodes)
                        for member in visible
                    ],
                )
            )
        return grouped

    async def _load_stocks(self, stock_ids: list[int]) -> dict[int, Stock]:
        if not stock_ids:
            return {}
        result = await self.session.scalars(
            select(Stock).where(Stock.id.in_(stock_ids))
        )
        return {stock.id: stock for stock in result.all()}

    async def _load_nodes(self, node_ids: list[int]) -> dict[int, ConceptNode]:
        if not node_ids:
            return {}
        result = await self.session.scalars(
            select(ConceptNode).where(ConceptNode.id.in_(node_ids))
        )
        return {node.id: node for node in result.all()}

    @staticmethod
    def _member_to_item(
        member: ThemeMiningMember,
        stocks: dict[int, Stock],
        nodes: dict[int, ConceptNode],
    ) -> MiningMemberItem:
        stock = stocks.get(member.stock_id)
        node = (
            nodes.get(member.concept_node_id)
            if member.concept_node_id is not None
            else None
        )
        metrics = dict(member.metrics or {})
        rise = metrics.get("rise_fall_pct")
        if rise is None and stock is not None:
            rise = _float_or_none(stock.rise_fall_pct)
        elif rise is not None:
            rise = _float_or_none(rise)
        return MiningMemberItem(
            stock_id=member.stock_id,
            stock_code=stock.code if stock else None,
            stock_name=stock.name if stock else None,
            concept_node_id=member.concept_node_id,
            concept_node_name=node.name if node else None,
            score=member.score,
            rank=member.rank,
            role_tag=member.role_tag,
            metrics=metrics,
            rise_fall_pct=rise,
        )


def _note_prompt_payload(
    card: ThemeMiningCard,
    theme_name: str,
    members: list[ThemeMiningMember],
    stocks: dict[int, Stock],
) -> dict[str, Any]:
    return {
        "theme_name": theme_name,
        "mining_type": card.mining_type,
        "lifecycle_stage": card.lifecycle_stage,
        "strength_score": card.strength_score,
        "score": card.score,
        "rationale": card.rationale,
        "degraded": card.degraded,
        "members": [
            {
                "stock_code": stocks[m.stock_id].code if m.stock_id in stocks else None,
                "stock_name": stocks[m.stock_id].name if m.stock_id in stocks else None,
                "role_tag": m.role_tag,
                "score": m.score,
                "metrics": m.metrics,
            }
            for m in members[:12]
        ],
    }


async def _generate_note_in_background(card_id: int, user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        repo = ThemeMiningRepository(session)
        try:
            await repo.upsert_note(
                card_id=card_id,
                user_id=user_id,
                status="running",
                content_md="",
                model_name=None,
                error=None,
            )
            await session.commit()

            card = await repo.get_card(card_id)
            if card is None:
                await repo.upsert_note(
                    card_id=card_id,
                    user_id=user_id,
                    status="failed",
                    content_md="",
                    error="挖掘卡不存在",
                )
                return

            theme = await session.get(Theme, card.theme_id)
            theme_name = theme.name if theme else f"题材{card.theme_id}"
            members = await repo.list_members([card_id])
            stock_ids = [m.stock_id for m in members]
            stocks: dict[int, Stock] = {}
            if stock_ids:
                result = await session.scalars(
                    select(Stock).where(Stock.id.in_(stock_ids))
                )
                stocks = {s.id: s for s in result.all()}

            providers = ModelProviderService(session, user_id)
            provider = await providers.get_default()
            adapter = providers.adapter(provider)
            user_prompt = (
                "请基于下列题材挖掘卡 JSON 输出简短中文 Markdown 点评。\n\n"
                + json.dumps(
                    _note_prompt_payload(card, theme_name, members, stocks),
                    ensure_ascii=False,
                    default=str,
                )
            )
            raw = await adapter.complete(
                SYSTEM_PROMPT,
                user_prompt,
                json_mode=False,
                reasoning=False,
                timeout_seconds=max(
                    int(provider.timeout_seconds or 60), NOTE_TIMEOUT_SECONDS
                ),
            )
            content = (raw or "").strip()
            if not content:
                raise ValueError("模型返回空内容")
            if "供参考，非投资建议" not in content:
                content = content + "\n\n供参考，非投资建议。"

            await repo.upsert_note(
                card_id=card_id,
                user_id=user_id,
                status="success",
                content_md=content,
                model_name=provider.model,
                error=None,
            )
        except Exception as exc:  # noqa: BLE001 — 后台不得抛穿事件循环
            logger.warning(
                "theme_mining_note_failed",
                card_id=card_id,
                user_id=user_id,
                error=str(exc)[:300],
            )
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                pass
            try:
                await repo.upsert_note(
                    card_id=card_id,
                    user_id=user_id,
                    status="failed",
                    content_md="",
                    model_name=None,
                    error=str(exc)[:300],
                )
            except Exception as write_exc:  # noqa: BLE001
                logger.warning(
                    "theme_mining_note_fail_write_failed",
                    card_id=card_id,
                    error=str(write_exc)[:300],
                )
        finally:
            try:
                await session.commit()
            except Exception as commit_exc:  # noqa: BLE001
                logger.warning(
                    "theme_mining_note_commit_failed",
                    card_id=card_id,
                    error=str(commit_exc),
                )
