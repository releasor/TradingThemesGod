"""MiningService 单元测试。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.repositories.theme_mining import CardWrite
from app.schemas.mining import MiningBoardResponse, MiningEnsureResponse, MiningNoteResponse
from app.services.mining import MiningService
from app.services.mining_rules import CardDraft, MemberDraft


def _card_row(**overrides):
    base = dict(
        id=10,
        trade_date=date(2026, 7, 25),
        theme_id=3,
        mining_type="low_branch",
        score=70,
        rank=1,
        lifecycle_stage="fermentation",
        strength_score=60,
        rationale="滞后",
        score_breakdown={"a": 1},
        degraded=False,
        missing_metrics=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _member_row(**overrides):
    base = dict(
        card_id=10,
        stock_id=100,
        concept_node_id=None,
        score=55,
        rank=1,
        role_tag="laggard",
        metrics={"rise_fall_pct": 1.2},
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_ensure_mines_and_replaces_day_cards():
    session = AsyncMock()
    session.commit = AsyncMock()

    snapshot = SimpleNamespace(
        theme_id=3,
        lifecycle_stage="fermentation",
        strength_score=60,
        leader_clarity_score=50,
        flow_score=40,
    )
    stock = SimpleNamespace(id=100, name="测", rise_fall_pct=0.5)
    service = MiningService(session)
    service.repo = AsyncMock()
    service.repo.replace_day_cards.return_value = 1

    draft = CardDraft(
        mining_type="low_branch",
        score=72,
        lifecycle_stage="fermentation",
        strength_score=60,
        rationale="滞后股",
        members=[
            MemberDraft(
                stock_id=100,
                score=55,
                rank=1,
                role_tag="laggard",
                metrics={"rise_fall_pct": 0.5},
            )
        ],
    )

    with (
        patch.object(
            service, "_load_top_snapshots", AsyncMock(return_value=[snapshot])
        ),
        patch.object(
            service,
            "_load_theme_stocks",
            AsyncMock(return_value={3: [stock]}),
        ),
        patch.object(
            service,
            "_load_one_node_per_stock",
            AsyncMock(return_value={100: 9}),
        ),
        patch("app.services.mining.mine_theme", return_value=[draft]) as mine,
    ):
        result = await service.ensure(date(2026, 7, 25))

    assert isinstance(result, MiningEnsureResponse)
    assert result.trade_date == date(2026, 7, 25)
    assert result.theme_count == 1
    assert result.card_count == 1
    assert result.counts["low_branch"] == 1
    mine.assert_called_once()
    service.repo.replace_day_cards.assert_awaited_once()
    written = service.repo.replace_day_cards.await_args.args[1]
    assert len(written) == 1
    assert isinstance(written[0], CardWrite)
    assert written[0].rank == 1
    assert written[0].members[0].concept_node_id == 9
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_get_board_groups_three_columns():
    session = AsyncMock()
    service = MiningService(session)
    service.repo = AsyncMock()
    card = _card_row()
    member = _member_row()
    service.repo.list_board.return_value = {
        "low_branch": [card],
        "catch_up": [],
        "hidden_leader": [],
    }
    service.repo.list_members.return_value = [member]

    stock = SimpleNamespace(id=100, code="000001", name="平安", rise_fall_pct=1.2)
    with (
        patch.object(
            service, "_load_theme_names", AsyncMock(return_value={3: "机器人"})
        ),
        patch.object(service, "_load_stocks", AsyncMock(return_value={100: stock})),
        patch.object(service, "_load_nodes", AsyncMock(return_value={})),
    ):
        result = await service.get_board(date(2026, 7, 25))

    assert isinstance(result, MiningBoardResponse)
    assert result.trade_date == date(2026, 7, 25)
    assert len(result.low_branch) == 1
    assert result.low_branch[0].theme_name == "机器人"
    assert result.low_branch[0].members[0].stock_code == "000001"
    assert result.low_branch[0].member_count == 1
    assert result.catch_up == []
    assert result.hidden_leader == []


@pytest.mark.asyncio
async def test_get_card_not_found():
    session = AsyncMock()
    service = MiningService(session)
    service.repo = AsyncMock()
    service.repo.get_card.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await service.get_card(999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_card_includes_note_when_user():
    session = AsyncMock()
    service = MiningService(session)
    service.repo = AsyncMock()
    card = _card_row(id=10)
    service.repo.get_card.return_value = card
    service.repo.list_members.return_value = [_member_row()]
    service.repo.get_note.return_value = SimpleNamespace(
        id=1,
        card_id=10,
        user_id=7,
        status="success",
        content_md="点评",
        model_name="gpt",
        error=None,
    )

    stock = SimpleNamespace(id=100, code="000001", name="平安", rise_fall_pct=1.2)
    with (
        patch.object(
            service, "_load_theme_names", AsyncMock(return_value={3: "机器人"})
        ),
        patch.object(service, "_load_stocks", AsyncMock(return_value={100: stock})),
        patch.object(service, "_load_nodes", AsyncMock(return_value={})),
    ):
        result = await service.get_card(10, user_id=7)

    assert result.note is not None
    assert result.note.content_md == "点评"
    service.repo.get_note.assert_awaited_once_with(10, 7)


@pytest.mark.asyncio
async def test_ensure_note_marks_pending_and_schedules():
    session = AsyncMock()
    session.commit = AsyncMock()
    service = MiningService(session)
    service.repo = AsyncMock()
    service.repo.get_card.return_value = _card_row(id=10)
    service.repo.get_note.return_value = None
    pending = SimpleNamespace(
        id=1,
        card_id=10,
        user_id=7,
        status="pending",
        content_md="",
        model_name=None,
        error=None,
    )
    service.repo.upsert_note.return_value = pending

    mock_task = MagicMock()
    with patch(
        "app.services.mining.asyncio.create_task", return_value=mock_task
    ) as create_task:
        result = await service.ensure_note(10, 7)

    assert isinstance(result, MiningNoteResponse)
    assert result.status == "pending"
    kwargs = service.repo.upsert_note.await_args.kwargs
    assert kwargs["status"] == "pending"
    assert kwargs["user_id"] == 7
    session.commit.assert_awaited()
    create_task.assert_called_once()
    coro = create_task.call_args.args[0]
    assert hasattr(coro, "cr_code") or hasattr(coro, "send")
    coro.close()


@pytest.mark.asyncio
async def test_ensure_note_skips_existing_success():
    session = AsyncMock()
    service = MiningService(session)
    service.repo = AsyncMock()
    service.repo.get_card.return_value = _card_row(id=10)
    service.repo.get_note.return_value = SimpleNamespace(
        id=1,
        card_id=10,
        user_id=7,
        status="success",
        content_md="已有",
        model_name="m",
        error=None,
    )

    with patch("app.services.mining.asyncio.create_task") as create_task:
        result = await service.ensure_note(10, 7)

    assert result.status == "success"
    assert result.content_md == "已有"
    create_task.assert_not_called()
    service.repo.upsert_note.assert_not_called()
