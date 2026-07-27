"""主线图谱 API 测试。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user, get_optional_user
from app.main import app
from app.schemas.concept_graph import ConceptGraphResponse
from app.schemas.mainline_graph import (
    MainlineGraphEdgeItem,
    MainlineGraphEnsureResponse,
    MainlineGraphNodeItem,
    MainlineGraphThemeConceptResponse,
    MainlineGraphVersionListResponse,
    MainlineGraphVersionMeta,
    MainlineGraphViewResponse,
)


def _auth_user():
    return SimpleNamespace(id=7, username="tester")


def _version_meta(**overrides) -> MainlineGraphVersionMeta:
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
    )
    base.update(overrides)
    return MainlineGraphVersionMeta(**base)


def test_get_view_returns_200():
    service_response = MainlineGraphViewResponse(
        trade_date=date(2026, 7, 25),
        version=_version_meta(),
        nodes=[
            MainlineGraphNodeItem(
                id=10,
                theme_id=3,
                theme_name="机器人",
                mainline_score=90,
                strength_score=70,
                lifecycle_stage="climax",
                role="mainline",
            )
        ],
        edges=[
            MainlineGraphEdgeItem(
                id=20,
                from_theme_id=3,
                to_theme_id=4,
                weight=0.35,
                method="rules",
                status="active",
            )
        ],
    )

    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.view = AsyncMock(return_value=service_response)

        response = TestClient(app).get(
            "/api/v1/mainline-graph/view?trade_date=2026-07-25"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["trade_date"] == "2026-07-25"
    assert body["nodes"][0]["theme_name"] == "机器人"
    assert body["edges"][0]["weight"] == 0.35
    service.view.assert_awaited_once_with(date(2026, 7, 25), None)


def test_list_versions_returns_200():
    service_response = MainlineGraphVersionListResponse(
        trade_date=date(2026, 7, 25),
        items=[_version_meta(), _version_meta(id=2, kind="draft")],
    )

    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.list_versions = AsyncMock(return_value=service_response)

        response = TestClient(app).get(
            "/api/v1/mainline-graph/versions?trade_date=2026-07-25"
        )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    service.list_versions.assert_awaited_once_with(date(2026, 7, 25))


def test_ensure_returns_200():
    service_response = MainlineGraphEnsureResponse(
        trade_date=date(2026, 7, 25),
        version_id=9,
        node_count=5,
        edge_count=2,
        model_queued=False,
    )

    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.ensure = AsyncMock(return_value=service_response)

        response = TestClient(app).post(
            "/api/v1/mainline-graph/ensure",
            json={"trade_date": "2026-07-25", "use_model": False},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["version_id"] == 9
    assert body["edge_count"] == 2
    service.ensure.assert_awaited_once_with(
        date(2026, 7, 25), use_model=False, user_id=None
    )


def test_create_draft_requires_auth():
    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.create_draft = AsyncMock(
            return_value=_version_meta(id=3, kind="draft", created_by=7)
        )
        app.dependency_overrides[get_current_user] = _auth_user
        try:
            response = TestClient(app).post(
                "/api/v1/mainline-graph/versions",
                json={"trade_date": "2026-07-25", "title": "我的草稿"},
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["kind"] == "draft"
    service.create_draft.assert_awaited_once()


def test_patch_edges_requires_auth():
    service_response = MainlineGraphViewResponse(
        trade_date=date(2026, 7, 25),
        version=_version_meta(id=3, kind="draft"),
        nodes=[],
        edges=[],
    )

    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.patch_edges = AsyncMock(return_value=service_response)
        app.dependency_overrides[get_current_user] = _auth_user
        try:
            response = TestClient(app).patch(
                "/api/v1/mainline-graph/versions/3/edges",
                json={
                    "edges": [
                        {
                            "op": "upsert",
                            "from_theme_id": 1,
                            "to_theme_id": 2,
                            "weight": 0.5,
                        }
                    ]
                },
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    service.patch_edges.assert_awaited_once()


def test_publish_requires_auth():
    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.publish = AsyncMock(
            return_value=_version_meta(id=3, kind="published", status="published")
        )
        app.dependency_overrides[get_current_user] = _auth_user
        try:
            response = TestClient(app).post(
                "/api/v1/mainline-graph/versions/3/publish"
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["kind"] == "published"
    service.publish.assert_awaited_once_with(3)


def test_accept_edge_requires_auth():
    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.accept_edge = AsyncMock(
            return_value=MainlineGraphEdgeItem(
                id=55,
                from_theme_id=1,
                to_theme_id=2,
                weight=0.4,
                method="model",
                status="active",
            )
        )
        app.dependency_overrides[get_current_user] = _auth_user
        try:
            response = TestClient(app).post(
                "/api/v1/mainline-graph/edges/40/accept",
                json={"draft_version_id": 3},
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["id"] == 55
    service.accept_edge.assert_awaited_once()


def test_theme_concept_returns_200():
    service_response = MainlineGraphThemeConceptResponse(
        theme_id=3,
        theme_name="机器人",
        trade_date=date(2026, 7, 25),
        lifecycle_stage="fermentation",
        strength_score=60,
        mainline_score=80,
        concept_graph=ConceptGraphResponse(),
    )

    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.get_theme_concept = AsyncMock(return_value=service_response)

        response = TestClient(app).get(
            "/api/v1/mainline-graph/themes/3/concept?trade_date=2026-07-25"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["theme_name"] == "机器人"
    assert body["concept_graph"]["node_count"] == 0
    service.get_theme_concept.assert_awaited_once_with(3, date(2026, 7, 25))


def test_ensure_with_model_passes_optional_user():
    service_response = MainlineGraphEnsureResponse(
        trade_date=date(2026, 7, 25),
        version_id=9,
        node_count=0,
        edge_count=0,
        model_queued=True,
    )

    with patch("app.api.mainline_graph.MainlineGraphService") as service_class:
        service = service_class.return_value
        service.ensure = AsyncMock(return_value=service_response)
        app.dependency_overrides[get_optional_user] = _auth_user
        try:
            response = TestClient(app).post(
                "/api/v1/mainline-graph/ensure",
                json={"trade_date": "2026-07-25", "use_model": True},
            )
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    assert response.status_code == 200
    assert response.json()["model_queued"] is True
    service.ensure.assert_awaited_once_with(
        date(2026, 7, 25), use_model=True, user_id=7
    )
