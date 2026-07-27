"""主线图谱聚合服务。"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from datetime import date
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.short_term_signal import SectorRotationSnapshot
from app.models.theme import Theme
from app.models.theme_stock import ThemeStock
from app.repositories.mainline_graph import (
    EdgeWrite,
    MainlineGraphRepository,
    NodeWrite,
)
from app.schemas.mainline_graph import (
    MainlineGraphAcceptEdgeRequest,
    MainlineGraphCreateDraftRequest,
    MainlineGraphEdgeItem,
    MainlineGraphEdgePatch,
    MainlineGraphEnsureResponse,
    MainlineGraphNodeItem,
    MainlineGraphPatchEdgesRequest,
    MainlineGraphThemeConceptResponse,
    MainlineGraphVersionListResponse,
    MainlineGraphVersionMeta,
    MainlineGraphViewResponse,
)
from app.services.concept_graph import ConceptGraphService
from app.services.mainline_graph_rules import (
    ThemeSnap,
    assign_roles,
    build_edges,
    jaccard,
)
from app.services.short_term import ShortTermService

logger = get_logger(__name__)

TOP_THEMES = 30
TOP_MAIN = 5
JACCARD_MIN = 0.12


class MainlineGraphService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repo: MainlineGraphRepository | None = None,
    ):
        self.session = session
        self.repo = repo or MainlineGraphRepository(session)

    async def ensure(
        self,
        trade_date: date | None = None,
        *,
        use_model: bool = False,
        user_id: int | None = None,
    ) -> MainlineGraphEnsureResponse:
        started = time.perf_counter()
        resolved = ShortTermService.resolve_trade_date(trade_date)
        snapshots = await self._load_top_snapshots(resolved)
        themes = [
            ThemeSnap(
                theme_id=snap.theme_id,
                mainline_score=snap.mainline_score,
                strength_score=snap.strength_score,
                lifecycle_stage=snap.lifecycle_stage,
            )
            for snap in snapshots
        ]
        theme_ids = [item.theme_id for item in themes]
        stock_sets = await self._load_stock_sets(theme_ids)
        roles = assign_roles(themes, top_main=TOP_MAIN)

        ordered = sorted(
            themes,
            key=lambda item: (-item.mainline_score, item.theme_id),
        )
        mainline_ids = [item.theme_id for item in ordered[:TOP_MAIN]]
        overlap = self._compute_overlap(stock_sets, mainline_ids, theme_ids)
        edge_drafts = build_edges(
            themes,
            overlap,
            jaccard_min=JACCARD_MIN,
            top_main=TOP_MAIN,
        )

        node_writes = [
            NodeWrite(
                theme_id=snap.theme_id,
                mainline_score=snap.mainline_score,
                strength_score=snap.strength_score,
                lifecycle_stage=snap.lifecycle_stage,
                role=roles.get(snap.theme_id, "branch"),
            )
            for snap in snapshots
        ]
        edge_writes = [
            EdgeWrite(
                from_theme_id=edge.from_theme_id,
                to_theme_id=edge.to_theme_id,
                weight=edge.weight,
                method=edge.method,
                status=edge.status,
                rationale=edge.rationale,
            )
            for edge in edge_drafts
        ]

        version = await self.repo.create_auto_version(
            resolved,
            node_writes,
            edge_writes,
            meta={"source": "rules", "top_themes": TOP_THEMES, "top_main": TOP_MAIN},
        )
        await self.session.commit()
        await self.session.refresh(version)

        model_queued = False
        if use_model and user_id is not None:
            model_queued = True
            await self.repo.update_version_meta(
                version.id, {"model_queued": True, "model_status": "queued"}
            )
            await self.session.commit()
            await self.session.refresh(version)
            asyncio.create_task(
                _suggest_model_edges_background(version.id, user_id)
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return MainlineGraphEnsureResponse(
            trade_date=resolved,
            version_id=version.id,
            node_count=len(node_writes),
            edge_count=len(edge_writes),
            model_queued=model_queued,
            generated_at=version.updated_at or version.created_at,
            elapsed_ms=elapsed_ms,
        )

    async def view(
        self,
        trade_date: date | None = None,
        version_id: int | None = None,
    ) -> MainlineGraphViewResponse:
        if version_id is not None:
            try:
                payload = await self.repo.get_view_payload(version_id)
            except ValueError as exc:
                raise HTTPException(404, str(exc)) from exc
            resolved = payload.version.trade_date
        else:
            resolved = ShortTermService.resolve_trade_date(trade_date)
            payload = await self.repo.resolve_view(resolved)
            if payload is None:
                return MainlineGraphViewResponse(
                    trade_date=resolved,
                    empty=True,
                )

        theme_names = await self._load_theme_names(
            [node.theme_id for node in payload.nodes]
        )
        return MainlineGraphViewResponse(
            trade_date=resolved,
            version=self._version_meta(payload.version),
            nodes=[
                MainlineGraphNodeItem(
                    id=node.id,
                    theme_id=node.theme_id,
                    theme_name=theme_names.get(
                        node.theme_id, f"题材{node.theme_id}"
                    ),
                    mainline_score=node.mainline_score,
                    strength_score=node.strength_score,
                    lifecycle_stage=node.lifecycle_stage,
                    role=node.role,
                    payload=node.payload,
                )
                for node in payload.nodes
            ],
            edges=[
                MainlineGraphEdgeItem(
                    id=edge.id,
                    from_theme_id=edge.from_theme_id,
                    to_theme_id=edge.to_theme_id,
                    weight=edge.weight,
                    method=edge.method,
                    status=edge.status,
                    rationale=edge.rationale or "",
                    created_by=edge.created_by,
                )
                for edge in payload.edges
            ],
            empty=False,
        )

    async def list_versions(
        self, trade_date: date | None = None
    ) -> MainlineGraphVersionListResponse:
        resolved = ShortTermService.resolve_trade_date(trade_date)
        versions = await self.repo.list_versions(resolved)
        return MainlineGraphVersionListResponse(
            trade_date=resolved,
            items=[self._version_meta(row) for row in versions],
        )

    async def create_draft(
        self,
        user_id: int,
        payload: MainlineGraphCreateDraftRequest,
    ) -> MainlineGraphVersionMeta:
        source_id = payload.source_version_id
        if source_id is None:
            resolved = ShortTermService.resolve_trade_date(payload.trade_date)
            view = await self.repo.resolve_view(resolved)
            if view is None:
                raise HTTPException(404, "当日无可克隆的图谱版本")
            source_id = view.version.id
        try:
            draft = await self.repo.clone_version(
                source_id, user_id, title=payload.title
            )
            await self.session.commit()
            await self.session.refresh(draft)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return self._version_meta(draft)

    async def patch_edges(
        self,
        version_id: int,
        user_id: int,
        payload: MainlineGraphPatchEdgesRequest,
    ) -> MainlineGraphViewResponse:
        for patch in payload.edges:
            try:
                await self._apply_edge_patch(version_id, user_id, patch)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
        await self.session.commit()
        return await self.view(version_id=version_id)

    async def publish(self, version_id: int) -> MainlineGraphVersionMeta:
        try:
            published = await self.repo.publish_version(version_id)
            await self.session.commit()
            await self.session.refresh(published)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return self._version_meta(published)

    async def accept_edge(
        self,
        edge_id: int,
        user_id: int,
        payload: MainlineGraphAcceptEdgeRequest,
    ) -> MainlineGraphEdgeItem:
        try:
            edge = await self.repo.accept_suggested_edge(
                edge_id,
                payload.draft_version_id,
                user_id=user_id,
            )
            await self.session.commit()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return MainlineGraphEdgeItem(
            id=edge.id,
            from_theme_id=edge.from_theme_id,
            to_theme_id=edge.to_theme_id,
            weight=edge.weight,
            method=edge.method,
            status=edge.status,
            rationale=edge.rationale or "",
            created_by=edge.created_by,
        )

    async def get_theme_concept(
        self,
        theme_id: int,
        trade_date: date | None = None,
    ) -> MainlineGraphThemeConceptResponse:
        theme = await self.session.get(Theme, theme_id)
        if theme is None:
            raise HTTPException(404, "题材不存在")

        # 主线页概念树只需树结构，跳过成分股关联以降低超时风险
        concept_graph = await ConceptGraphService(self.session).get_graph(
            theme_id, include_stocks=False
        )
        resolved = ShortTermService.resolve_trade_date(trade_date)
        snap = await self.session.scalar(
            select(SectorRotationSnapshot)
            .where(
                SectorRotationSnapshot.theme_id == theme_id,
                SectorRotationSnapshot.trade_date == resolved,
            )
            .limit(1)
        )
        if snap is None:
            snap = await self.session.scalar(
                select(SectorRotationSnapshot)
                .where(SectorRotationSnapshot.theme_id == theme_id)
                .order_by(desc(SectorRotationSnapshot.trade_date))
                .limit(1)
            )

        return MainlineGraphThemeConceptResponse(
            theme_id=theme_id,
            theme_name=theme.name,
            trade_date=snap.trade_date if snap else resolved,
            lifecycle_stage=snap.lifecycle_stage if snap else None,
            strength_score=snap.strength_score if snap else None,
            mainline_score=snap.mainline_score if snap else None,
            concept_graph=concept_graph,
        )

    async def _apply_edge_patch(
        self,
        version_id: int,
        user_id: int,
        patch: MainlineGraphEdgePatch,
    ) -> None:
        if patch.op == "delete":
            if patch.edge_id is None:
                raise ValueError("删除边需提供 edge_id")
            await self.repo.delete_edge(version_id, patch.edge_id)
            return

        if patch.from_theme_id is None or patch.to_theme_id is None:
            raise ValueError("upsert 需提供 from_theme_id 与 to_theme_id")
        if patch.weight is None:
            raise ValueError("upsert 需提供 weight")
        await self.repo.upsert_edge(
            version_id,
            from_theme_id=patch.from_theme_id,
            to_theme_id=patch.to_theme_id,
            weight=patch.weight,
            method=patch.method,
            status=patch.status,
            rationale=patch.rationale,
            created_by=user_id,
        )

    async def _load_top_snapshots(
        self, trade_date: date
    ) -> list[SectorRotationSnapshot]:
        result = await self.session.scalars(
            select(SectorRotationSnapshot)
            .where(SectorRotationSnapshot.trade_date == trade_date)
            .order_by(desc(SectorRotationSnapshot.mainline_score))
            .limit(TOP_THEMES)
        )
        return list(result.all())

    async def _load_stock_sets(
        self, theme_ids: list[int]
    ) -> dict[int, set[int]]:
        if not theme_ids:
            return {}
        result = await self.session.execute(
            select(ThemeStock.theme_id, ThemeStock.stock_id).where(
                ThemeStock.theme_id.in_(theme_ids)
            )
        )
        grouped: dict[int, set[int]] = defaultdict(set)
        for theme_id, stock_id in result.all():
            grouped[theme_id].add(stock_id)
        return grouped

    @staticmethod
    def _compute_overlap(
        stock_sets: dict[int, set[int]],
        mainline_ids: list[int],
        theme_ids: list[int],
    ) -> dict[tuple[int, int], float]:
        overlap: dict[tuple[int, int], float] = {}
        for main_id in mainline_ids:
            for other_id in theme_ids:
                if other_id == main_id:
                    continue
                key = (min(main_id, other_id), max(main_id, other_id))
                if key in overlap:
                    continue
                overlap[key] = jaccard(
                    stock_sets.get(main_id, set()),
                    stock_sets.get(other_id, set()),
                )
        return overlap

    async def _load_theme_names(self, theme_ids: list[int]) -> dict[int, str]:
        if not theme_ids:
            return {}
        result = await self.session.scalars(
            select(Theme).where(Theme.id.in_(theme_ids))
        )
        return {theme.id: theme.name for theme in result.all()}

    @staticmethod
    def _version_meta(version: Any) -> MainlineGraphVersionMeta:
        return MainlineGraphVersionMeta(
            id=version.id,
            trade_date=version.trade_date,
            kind=version.kind,
            title=version.title,
            status=version.status,
            parent_version_id=version.parent_version_id,
            created_by=version.created_by,
            published_at=version.published_at,
            meta=dict(version.meta or {}),
            created_at=getattr(version, "created_at", None),
            updated_at=getattr(version, "updated_at", None),
        )


async def _suggest_model_edges_background(version_id: int, user_id: int) -> None:
    """模型建议边后台 stub：标记完成，不阻塞 ensure。"""
    async with AsyncSessionLocal() as session:
        repo = MainlineGraphRepository(session)
        try:
            await repo.update_version_meta(
                version_id,
                {
                    "model_queued": False,
                    "model_status": "done",
                    "model_user_id": user_id,
                    "model_edge_count": 0,
                },
            )
            await session.commit()
        except Exception as exc:  # noqa: BLE001 — 后台不得抛穿事件循环
            logger.warning(
                "mainline_graph_model_suggest_failed",
                version_id=version_id,
                user_id=user_id,
                error=str(exc)[:300],
            )
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                pass
            try:
                await repo.update_version_meta(
                    version_id,
                    {
                        "model_queued": False,
                        "model_status": "failed",
                        "model_error": str(exc)[:300],
                    },
                )
                await session.commit()
            except Exception as write_exc:  # noqa: BLE001
                logger.warning(
                    "mainline_graph_model_fail_write_failed",
                    version_id=version_id,
                    error=str(write_exc)[:300],
                )
