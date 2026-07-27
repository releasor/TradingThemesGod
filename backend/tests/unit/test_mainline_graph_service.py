"""MainlineGraphService 单元测试。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.repositories.mainline_graph import EdgeWrite, GraphViewPayload, NodeWrite
from app.schemas.concept_graph import ConceptGraphResponse
from app.schemas.mainline_graph import (
    MainlineGraphAcceptEdgeRequest,
    MainlineGraphCreateDraftRequest,
    MainlineGraphEdgePatch,
    MainlineGraphEnsureResponse,
    MainlineGraphPatchEdgesRequest,
)
from app.services.mainline_graph import MainlineGraphService
from app.services.mainline_graph_rules import EdgeDraft


def _version(**overrides):
    base = dict(
        id=1,
        trade_date=date(2026, 7, 25),
        kind="auto",
        title=None,
        status="open",
        parent_version_id=None,
        created_by=None,
        published_at=None,
        meta={},
        created_at=None,
        updated_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _node(**overrides):
    base = dict(
        id=10,
        theme_id=3,
        mainline_score=80,
        strength_score=60,
        lifecycle_stage="fermentation",
        role="mainline",
        payload=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _edge(**overrides):
    base = dict(
        id=20,
        from_theme_id=3,
        to_theme_id=4,
        weight=0.4,
        method="rules",
        status="active",
        rationale="Jaccard=0.4000",
        created_by=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_ensure_builds_auto_version_and_commits():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    service = MainlineGraphService(session)
    service.repo = AsyncMock()
    version = _version(id=99)
    service.repo.create_auto_version.return_value = version

    snapshot = SimpleNamespace(
        theme_id=3,
        mainline_score=90,
        strength_score=70,
        lifecycle_stage="climax",
    )
    with (
        patch(
            "app.services.mainline_graph.ShortTermService.resolve_trade_date",
            side_effect=lambda d=None: d or date(2026, 7, 25),
        ),
        patch.object(
            service, "_load_top_snapshots", AsyncMock(return_value=[snapshot])
        ),
        patch.object(
            service, "_load_stock_sets", AsyncMock(return_value={3: {1, 2}})
        ),
        patch(
            "app.services.mainline_graph.build_edges",
            return_value=[
                EdgeDraft(
                    from_theme_id=3,
                    to_theme_id=4,
                    weight=0.3,
                )
            ],
        ),
    ):
        result = await service.ensure(date(2026, 7, 25))

    assert isinstance(result, MainlineGraphEnsureResponse)
    assert result.version_id == 99
    assert result.node_count == 1
    assert result.edge_count == 1
    assert result.model_queued is False
    assert result.elapsed_ms >= 0
    service.repo.create_auto_version.assert_awaited_once()
    args = service.repo.create_auto_version.await_args
    assert args.args[0] == date(2026, 7, 25)
    assert isinstance(args.args[1][0], NodeWrite)
    assert isinstance(args.args[2][0], EdgeWrite)
    session.commit.assert_awaited()
    session.refresh.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_queues_model_when_requested():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    service = MainlineGraphService(session)
    service.repo = AsyncMock()
    service.repo.create_auto_version.return_value = _version(id=5)
    service.repo.update_version_meta.return_value = _version(id=5)

    def _consume_coro(coro):
        coro.close()
        return MagicMock()

    with (
        patch.object(service, "_load_top_snapshots", AsyncMock(return_value=[])),
        patch.object(service, "_load_stock_sets", AsyncMock(return_value={})),
        patch(
            "app.services.mainline_graph.asyncio.create_task",
            side_effect=_consume_coro,
        ) as create_task,
    ):
        result = await service.ensure(
            date(2026, 7, 25), use_model=True, user_id=7
        )

    assert result.model_queued is True
    service.repo.update_version_meta.assert_awaited()
    create_task.assert_called_once()


@pytest.mark.asyncio
async def test_view_empty_when_no_version():
    session = AsyncMock()
    service = MainlineGraphService(session)
    service.repo = AsyncMock()
    service.repo.resolve_view.return_value = None

    with patch(
        "app.services.mainline_graph.ShortTermService.resolve_trade_date",
        side_effect=lambda d=None: d or date(2026, 7, 25),
    ):
        result = await service.view(date(2026, 7, 25))

    assert result.empty is True
    assert result.nodes == []
    assert result.trade_date == date(2026, 7, 25)


@pytest.mark.asyncio
async def test_view_returns_nodes_and_edges():
    session = AsyncMock()
    service = MainlineGraphService(session)
    service.repo = AsyncMock()
    payload = GraphViewPayload(
        version=_version(),
        nodes=[_node()],
        edges=[_edge()],
    )
    service.repo.resolve_view.return_value = payload

    with patch.object(
        service, "_load_theme_names", AsyncMock(return_value={3: "机器人"})
    ):
        result = await service.view(date(2026, 7, 25))

    assert result.empty is False
    assert result.version is not None
    assert result.nodes[0].theme_name == "机器人"
    assert result.edges[0].weight == 0.4


@pytest.mark.asyncio
async def test_create_draft_clones_resolved_source():
    session = AsyncMock()
    session.commit = AsyncMock()
    service = MainlineGraphService(session)
    service.repo = AsyncMock()
    service.repo.resolve_view.return_value = GraphViewPayload(
        version=_version(id=11),
        nodes=[],
        edges=[],
    )
    service.repo.clone_version.return_value = _version(
        id=22, kind="draft", parent_version_id=11, created_by=7
    )

    result = await service.create_draft(
        7, MainlineGraphCreateDraftRequest(trade_date=date(2026, 7, 25))
    )

    assert result.id == 22
    assert result.kind == "draft"
    service.repo.clone_version.assert_awaited_once_with(11, 7, title=None)
    session.refresh.assert_awaited()


@pytest.mark.asyncio
async def test_patch_edges_upsert_then_returns_view():
    session = AsyncMock()
    session.commit = AsyncMock()
    service = MainlineGraphService(session)
    service.repo = AsyncMock()
    service.repo.upsert_edge.return_value = _edge()
    service.repo.get_view_payload.return_value = GraphViewPayload(
        version=_version(id=3, kind="draft"),
        nodes=[],
        edges=[_edge()],
    )

    with patch.object(service, "_load_theme_names", AsyncMock(return_value={})):
        result = await service.patch_edges(
            3,
            7,
            MainlineGraphPatchEdgesRequest(
                edges=[
                    MainlineGraphEdgePatch(
                        op="upsert",
                        from_theme_id=1,
                        to_theme_id=2,
                        weight=0.5,
                    )
                ]
            ),
        )

    service.repo.upsert_edge.assert_awaited_once()
    assert result.version is not None
    assert result.version.id == 3


@pytest.mark.asyncio
async def test_publish_raises_http_on_repo_error():
    session = AsyncMock()
    service = MainlineGraphService(session)
    service.repo = AsyncMock()
    service.repo.publish_version.side_effect = ValueError("仅草稿版本可发布")

    with pytest.raises(HTTPException) as exc_info:
        await service.publish(9)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_accept_edge_returns_item():
    session = AsyncMock()
    session.commit = AsyncMock()
    service = MainlineGraphService(session)
    service.repo = AsyncMock()
    service.repo.accept_suggested_edge.return_value = _edge(
        id=55, method="model", status="active"
    )

    result = await service.accept_edge(
        40, 7, MainlineGraphAcceptEdgeRequest(draft_version_id=3)
    )

    assert result.id == 55
    assert result.status == "active"
    service.repo.accept_suggested_edge.assert_awaited_once_with(
        40, 3, user_id=7
    )


@pytest.mark.asyncio
async def test_get_theme_concept_empty_graph_ok():
    session = AsyncMock()
    theme = SimpleNamespace(id=3, name="机器人")
    session.get = AsyncMock(return_value=theme)
    session.scalar = AsyncMock(return_value=None)
    service = MainlineGraphService(session)

    with patch(
        "app.services.mainline_graph.ConceptGraphService"
    ) as concept_cls:
        concept_cls.return_value.get_graph = AsyncMock(
            return_value=ConceptGraphResponse()
        )
        result = await service.get_theme_concept(3, date(2026, 7, 25))

    assert result.theme_name == "机器人"
    assert result.concept_graph.node_count == 0
    assert result.lifecycle_stage is None
    concept_cls.return_value.get_graph.assert_awaited_once_with(
        3, include_stocks=False
    )
