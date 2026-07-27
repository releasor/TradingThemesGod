"""主线图谱版本 / 节点 / 边仓储。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mainline_graph import (
    MainlineGraphEdge,
    MainlineGraphNode,
    MainlineGraphVersion,
)


@dataclass
class NodeWrite:
    theme_id: int
    mainline_score: int
    strength_score: int
    lifecycle_stage: str
    role: str
    payload: dict[str, Any] | None = None


@dataclass
class EdgeWrite:
    from_theme_id: int
    to_theme_id: int
    weight: float
    method: str = "rules"
    status: str = "active"
    rationale: str = ""
    created_by: int | None = None


@dataclass
class GraphViewPayload:
    version: MainlineGraphVersion
    nodes: list[MainlineGraphNode] = field(default_factory=list)
    edges: list[MainlineGraphEdge] = field(default_factory=list)


class MainlineGraphRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_auto_version(
        self,
        trade_date: date,
        nodes: list[NodeWrite],
        edges: list[EdgeWrite],
        *,
        meta: dict[str, Any] | None = None,
    ) -> MainlineGraphVersion:
        """刷新当日 kind=auto 版本（原地复用 id，避免 URL versionId 失效）。"""
        from sqlalchemy import delete

        existing = await self.session.scalar(
            select(MainlineGraphVersion)
            .where(
                MainlineGraphVersion.trade_date == trade_date,
                MainlineGraphVersion.kind == "auto",
            )
            .order_by(MainlineGraphVersion.id.desc())
            .limit(1)
        )

        if existing is not None:
            version = existing
            # 清理同日多余 auto（历史 delete+insert 残留）
            extras = await self.session.scalars(
                select(MainlineGraphVersion).where(
                    MainlineGraphVersion.trade_date == trade_date,
                    MainlineGraphVersion.kind == "auto",
                    MainlineGraphVersion.id != version.id,
                )
            )
            for row in extras.all():
                await self.session.delete(row)
            await self.session.execute(
                delete(MainlineGraphEdge).where(
                    MainlineGraphEdge.version_id == version.id
                )
            )
            await self.session.execute(
                delete(MainlineGraphNode).where(
                    MainlineGraphNode.version_id == version.id
                )
            )
            version.status = "open"
            version.title = None
            version.parent_version_id = None
            version.created_by = None
            version.published_at = None
            version.meta = meta or {}
            await self.session.flush()
        else:
            version = MainlineGraphVersion(
                trade_date=trade_date,
                kind="auto",
                title=None,
                status="open",
                parent_version_id=None,
                created_by=None,
                published_at=None,
                meta=meta or {},
            )
            self.session.add(version)
            await self.session.flush()

        await self._insert_nodes_edges(version.id, nodes, edges)
        return version

    async def clone_version(
        self,
        source_id: int,
        user_id: int,
        title: str | None = None,
    ) -> MainlineGraphVersion:
        source = await self.get_version(source_id)
        if source is None:
            raise ValueError("源版本不存在")

        payload = await self.get_view_payload(source_id)
        draft = MainlineGraphVersion(
            trade_date=source.trade_date,
            kind="draft",
            title=title,
            status="open",
            parent_version_id=source.id,
            created_by=user_id,
            published_at=None,
            meta=dict(source.meta or {}),
        )
        self.session.add(draft)
        await self.session.flush()

        node_writes = [
            NodeWrite(
                theme_id=node.theme_id,
                mainline_score=node.mainline_score,
                strength_score=node.strength_score,
                lifecycle_stage=node.lifecycle_stage,
                role=node.role,
                payload=dict(node.payload) if node.payload else None,
            )
            for node in payload.nodes
        ]
        edge_writes = [
            EdgeWrite(
                from_theme_id=edge.from_theme_id,
                to_theme_id=edge.to_theme_id,
                weight=edge.weight,
                method=edge.method,
                status=edge.status,
                rationale=edge.rationale or "",
                created_by=edge.created_by,
            )
            for edge in payload.edges
        ]
        await self._insert_nodes_edges(draft.id, node_writes, edge_writes)
        return draft

    async def get_version(self, version_id: int) -> MainlineGraphVersion | None:
        return await self.session.get(MainlineGraphVersion, version_id)

    async def list_versions(self, trade_date: date) -> list[MainlineGraphVersion]:
        result = await self.session.scalars(
            select(MainlineGraphVersion)
            .where(MainlineGraphVersion.trade_date == trade_date)
            .order_by(
                MainlineGraphVersion.kind,
                MainlineGraphVersion.id.desc(),
            )
        )
        return list(result.all())

    async def get_view_payload(self, version_id: int) -> GraphViewPayload:
        version = await self.get_version(version_id)
        if version is None:
            raise ValueError("版本不存在")
        nodes = list(
            (
                await self.session.scalars(
                    select(MainlineGraphNode)
                    .where(MainlineGraphNode.version_id == version_id)
                    .order_by(MainlineGraphNode.theme_id)
                )
            ).all()
        )
        edges = list(
            (
                await self.session.scalars(
                    select(MainlineGraphEdge)
                    .where(MainlineGraphEdge.version_id == version_id)
                    .order_by(MainlineGraphEdge.id)
                )
            ).all()
        )
        return GraphViewPayload(version=version, nodes=nodes, edges=edges)

    async def resolve_view(self, trade_date: date) -> GraphViewPayload | None:
        """优先 published，否则 auto。"""
        published = await self.session.scalar(
            select(MainlineGraphVersion)
            .where(
                MainlineGraphVersion.trade_date == trade_date,
                MainlineGraphVersion.kind == "published",
                MainlineGraphVersion.status == "published",
            )
            .order_by(MainlineGraphVersion.id.desc())
            .limit(1)
        )
        if published is not None:
            return await self.get_view_payload(published.id)

        auto = await self.session.scalar(
            select(MainlineGraphVersion)
            .where(
                MainlineGraphVersion.trade_date == trade_date,
                MainlineGraphVersion.kind == "auto",
            )
            .order_by(MainlineGraphVersion.id.desc())
            .limit(1)
        )
        if auto is None:
            return None
        return await self.get_view_payload(auto.id)

    async def upsert_edge(
        self,
        version_id: int,
        *,
        from_theme_id: int,
        to_theme_id: int,
        weight: float,
        method: str = "manual",
        status: str = "active",
        rationale: str = "",
        created_by: int | None = None,
    ) -> MainlineGraphEdge:
        version = await self._require_draft(version_id)
        existing = await self.session.scalar(
            select(MainlineGraphEdge).where(
                MainlineGraphEdge.version_id == version.id,
                MainlineGraphEdge.from_theme_id == from_theme_id,
                MainlineGraphEdge.to_theme_id == to_theme_id,
            )
        )
        if existing is None:
            existing = MainlineGraphEdge(
                version_id=version.id,
                from_theme_id=from_theme_id,
                to_theme_id=to_theme_id,
            )
            self.session.add(existing)

        existing.weight = weight
        existing.method = method
        existing.status = status
        existing.rationale = rationale
        if created_by is not None:
            existing.created_by = created_by
        await self.session.flush()
        return existing

    async def delete_edge(self, version_id: int, edge_id: int) -> None:
        await self._require_draft(version_id)
        edge = await self.session.get(MainlineGraphEdge, edge_id)
        if edge is None or edge.version_id != version_id:
            raise ValueError("边不存在")
        await self.session.delete(edge)
        await self.session.flush()

    async def publish_version(self, draft_id: int) -> MainlineGraphVersion:
        draft = await self.get_version(draft_id)
        if draft is None:
            raise ValueError("版本不存在")
        if draft.kind != "draft" or draft.status != "open":
            raise ValueError("仅草稿版本可发布")

        old_published = await self.session.scalars(
            select(MainlineGraphVersion).where(
                MainlineGraphVersion.trade_date == draft.trade_date,
                MainlineGraphVersion.kind == "published",
                MainlineGraphVersion.status == "published",
            )
        )
        for row in old_published.all():
            row.status = "archived"
            row.kind = "published"

        now = datetime.now(UTC)
        draft.kind = "published"
        draft.status = "published"
        draft.published_at = now
        await self.session.flush()
        return draft

    async def accept_suggested_edge(
        self,
        edge_id: int,
        draft_version_id: int,
        *,
        user_id: int | None = None,
    ) -> MainlineGraphEdge:
        draft = await self._require_draft(draft_version_id)
        source = await self.session.get(MainlineGraphEdge, edge_id)
        if source is None:
            raise ValueError("建议边不存在")
        if source.status != "suggested":
            raise ValueError("仅 suggested 边可采纳")

        return await self.upsert_edge(
            draft.id,
            from_theme_id=source.from_theme_id,
            to_theme_id=source.to_theme_id,
            weight=source.weight,
            method=source.method if source.method in {"model", "rules"} else "manual",
            status="active",
            rationale=source.rationale or "",
            created_by=user_id,
        )

    async def update_version_meta(
        self,
        version_id: int,
        meta: dict[str, Any],
    ) -> MainlineGraphVersion:
        version = await self.get_version(version_id)
        if version is None:
            raise ValueError("版本不存在")
        version.meta = {**(version.meta or {}), **meta}
        await self.session.flush()
        return version

    async def _require_draft(self, version_id: int) -> MainlineGraphVersion:
        version = await self.get_version(version_id)
        if version is None:
            raise ValueError("版本不存在")
        if version.kind != "draft" or version.status != "open":
            raise ValueError("仅草稿版本可编辑")
        return version

    async def _insert_nodes_edges(
        self,
        version_id: int,
        nodes: list[NodeWrite],
        edges: list[EdgeWrite],
    ) -> None:
        for node in nodes:
            self.session.add(
                MainlineGraphNode(
                    version_id=version_id,
                    theme_id=node.theme_id,
                    mainline_score=node.mainline_score,
                    strength_score=node.strength_score,
                    lifecycle_stage=node.lifecycle_stage,
                    role=node.role,
                    payload=node.payload,
                )
            )
        await self.session.flush()
        for edge in edges:
            self.session.add(
                MainlineGraphEdge(
                    version_id=version_id,
                    from_theme_id=edge.from_theme_id,
                    to_theme_id=edge.to_theme_id,
                    weight=edge.weight,
                    method=edge.method,
                    status=edge.status,
                    rationale=edge.rationale,
                    created_by=edge.created_by,
                )
            )
        await self.session.flush()
