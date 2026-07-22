"""仓储基类测试

测试 BaseRepository 的通用分页查询方法。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, select

from app.repositories.base import BaseRepository

# 创建测试用表
metadata = MetaData()
test_table = Table(
    "test_items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
)


class TestBaseRepositoryPaginate:
    """_paginate 方法测试"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟数据库会话"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """创建 BaseRepository 实例"""
        return BaseRepository(mock_session)

    @pytest.mark.asyncio
    async def test_paginate_returns_items_and_total(self, repo, mock_session):
        """测试分页返回数据列表和总数"""
        count_result = MagicMock()
        count_result.scalar.return_value = 10

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = ["item1", "item2"]

        mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

        query = select(test_table)
        items, total = await repo._paginate(query, page=1, page_size=20)

        assert total == 10
        assert items == ["item1", "item2"]

    @pytest.mark.asyncio
    async def test_paginate_default_params(self, repo, mock_session):
        """测试分页默认参数"""
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

        query = select(test_table)
        items, total = await repo._paginate(query)

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_paginate_with_sort_desc(self, repo, mock_session):
        """测试降序排序"""
        count_result = MagicMock()
        count_result.scalar.return_value = 5

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = ["a", "b"]

        mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

        query = select(test_table)
        items, total = await repo._paginate(
            query, page=1, page_size=10, sort_column=test_table.c.id, sort_order="desc"
        )

        assert total == 5
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_paginate_with_sort_asc(self, repo, mock_session):
        """测试升序排序"""
        count_result = MagicMock()
        count_result.scalar.return_value = 3

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = ["x", "y", "z"]

        mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

        query = select(test_table)
        items, total = await repo._paginate(
            query, page=1, page_size=10, sort_column=test_table.c.name, sort_order="asc"
        )

        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_paginate_page_offset(self, repo, mock_session):
        """测试分页偏移量计算"""
        count_result = MagicMock()
        count_result.scalar.return_value = 100

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

        query = select(test_table)
        items, total = await repo._paginate(query, page=3, page_size=10)

        assert total == 100

    @pytest.mark.asyncio
    async def test_paginate_count_returns_none(self, repo, mock_session):
        """测试 count 返回 None 的情况"""
        count_result = MagicMock()
        count_result.scalar.return_value = None

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

        query = select(test_table)
        items, total = await repo._paginate(query)

        # None 应该被转换为 0
        assert total == 0

    @pytest.mark.asyncio
    async def test_paginate_executes_queries_sequentially(self, repo, mock_session):
        """同一异步会话上的查询必须顺序执行"""
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = ["item"]

        active_queries = 0
        results = iter([count_result, data_result])

        async def execute(_query):
            nonlocal active_queries
            active_queries += 1
            assert active_queries == 1
            result = next(results)
            active_queries -= 1
            return result

        mock_session.execute = AsyncMock(side_effect=execute)

        query = select(test_table)
        await repo._paginate(query)

        assert mock_session.execute.await_count == 2
