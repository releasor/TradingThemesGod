"""MainlineGraphRepository.create_auto_version 原地复用测试。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.mainline_graph import (
    EdgeWrite,
    MainlineGraphRepository,
    NodeWrite,
)


@pytest.mark.asyncio
async def test_create_auto_version_reuses_existing_auto_id():
    session = AsyncMock()
    existing = SimpleNamespace(
        id=9,
        trade_date=date(2026, 7, 24),
        kind="auto",
        status="open",
        title=None,
        parent_version_id=None,
        created_by=None,
        published_at=None,
        meta={},
    )
    # first scalar → existing auto; second scalars → no extras
    session.scalar = AsyncMock(return_value=existing)
    extras_result = MagicMock()
    extras_result.all.return_value = []
    session.scalars = AsyncMock(return_value=extras_result)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()

    repo = MainlineGraphRepository(session)
    repo._insert_nodes_edges = AsyncMock()  # type: ignore[method-assign]

    version = await repo.create_auto_version(
        date(2026, 7, 24),
        [
            NodeWrite(
                theme_id=1,
                mainline_score=10,
                strength_score=10,
                lifecycle_stage="germination",
                role="mainline",
            )
        ],
        [
            EdgeWrite(
                from_theme_id=1,
                to_theme_id=2,
                weight=0.5,
            )
        ],
        meta={"source": "rules"},
    )

    assert version.id == 9
    session.add.assert_not_called()
    assert session.execute.await_count >= 2
    repo._insert_nodes_edges.assert_awaited_once()
