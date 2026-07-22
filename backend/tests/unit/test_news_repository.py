"""新闻仓储分页测试。"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.news import NewsRepository


@pytest.mark.asyncio
async def test_list_latest_applies_offset_for_infinite_scrolling():
    session = AsyncMock()
    session.scalar.return_value = 120
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repository = NewsRepository(session)

    await repository.list_latest(limit=50, offset=50)

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "LIMIT 50 OFFSET 50" in " ".join(sql.split())


@pytest.mark.asyncio
async def test_theme_candidates_filter_by_keywords_and_date():
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repository = NewsRepository(session)

    await repository.list_theme_candidates(
        ["机器人", "埃斯顿"], datetime(2026, 6, 20, tzinfo=UTC)
    )

    statement = session.execute.await_args.args[0]
    sql = " ".join(
        str(statement.compile(compile_kwargs={"literal_binds": True})).split()
    )
    assert "2026-06-20" in sql
    assert "机器人" in sql
    assert "埃斯顿" in sql


@pytest.mark.asyncio
async def test_theme_candidates_with_no_keywords_skips_database():
    session = AsyncMock()
    repository = NewsRepository(session)

    assert await repository.list_theme_candidates([], datetime.now(UTC)) == []
    session.execute.assert_not_awaited()
