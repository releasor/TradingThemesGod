"""题材挖掘 API 测试。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.schemas.mining import (
    MiningBoardResponse,
    MiningCardItem,
    MiningEnsureResponse,
    MiningMemberItem,
    MiningNoteResponse,
)


def _auth_user():
    return SimpleNamespace(id=7, username="tester")


def _card_item() -> MiningCardItem:
    return MiningCardItem(
        id=10,
        trade_date=date(2026, 7, 25),
        theme_id=3,
        theme_name="机器人",
        mining_type="low_branch",
        score=70,
        rank=1,
        lifecycle_stage="fermentation",
        strength_score=60,
        rationale="滞后",
        member_count=1,
        members=[
            MiningMemberItem(
                stock_id=100,
                stock_code="000001",
                stock_name="平安",
                score=55,
                rank=1,
                role_tag="laggard",
                rise_fall_pct=1.2,
            )
        ],
    )


def test_get_mining_board_returns_200():
    service_response = MiningBoardResponse(
        trade_date=date(2026, 7, 25),
        low_branch=[_card_item()],
        catch_up=[],
        hidden_leader=[],
    )

    with patch("app.api.mining.MiningService") as service_class:
        service = service_class.return_value
        service.get_board = AsyncMock(return_value=service_response)

        response = TestClient(app).get("/api/v1/mining/board?trade_date=2026-07-25")

    assert response.status_code == 200
    body = response.json()
    assert body["trade_date"] == "2026-07-25"
    assert len(body["low_branch"]) == 1
    assert body["low_branch"][0]["theme_name"] == "机器人"
    assert body["catch_up"] == []
    service.get_board.assert_awaited_once_with(date(2026, 7, 25))


def test_get_mining_card_returns_200():
    service_response = _card_item()

    with patch("app.api.mining.MiningService") as service_class:
        service = service_class.return_value
        service.get_card = AsyncMock(return_value=service_response)

        response = TestClient(app).get("/api/v1/mining/cards/10")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 10
    assert body["members"][0]["role_tag"] == "laggard"
    service.get_card.assert_awaited_once_with(10, user_id=None)


def test_ensure_mining_returns_200():
    service_response = MiningEnsureResponse(
        trade_date=date(2026, 7, 25),
        theme_count=5,
        card_count=2,
        counts={"low_branch": 1, "catch_up": 1, "hidden_leader": 0},
    )

    with patch("app.api.mining.MiningService") as service_class:
        service = service_class.return_value
        service.ensure = AsyncMock(return_value=service_response)

        response = TestClient(app).post("/api/v1/mining/ensure?trade_date=2026-07-25")

    assert response.status_code == 200
    body = response.json()
    assert body["card_count"] == 2
    assert body["theme_count"] == 5
    assert body["counts"]["low_branch"] == 1
    service.ensure.assert_awaited_once_with(date(2026, 7, 25))


def test_ensure_mining_note_requires_auth_and_returns_200():
    service_response = MiningNoteResponse(
        id=1,
        card_id=10,
        user_id=7,
        status="pending",
        content_md="",
    )

    with patch("app.api.mining.MiningService") as service_class:
        service = service_class.return_value
        service.ensure_note = AsyncMock(return_value=service_response)
        app.dependency_overrides[get_current_user] = _auth_user
        try:
            response = TestClient(app).post("/api/v1/mining/cards/10/note/ensure")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["card_id"] == 10
    service.ensure_note.assert_awaited_once_with(10, 7)
