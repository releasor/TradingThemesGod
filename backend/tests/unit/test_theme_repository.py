"""ThemeRepository 单元测试

测试题材仓储的数据库查询操作。
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import mysql

from app.models.industry_chain import IndustryChain
from app.models.theme import Theme
from app.repositories.theme import ThemeRepository, _tag_contains


@pytest.fixture
def mock_session():
    """创建模拟的 AsyncSession"""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_themes():
    """示例题材数据"""
    return [
        Theme(
            id=1,
            name="人工智能",
            code="AI",
            description="AI 相关题材",
            heat_index=Decimal("95.50"),
            rise_fall_pct=Decimal("2.35"),
            stock_count=50,
            category="科技",
            tags=["AI", "机器学习"],
            source="东方财富",
        ),
        Theme(
            id=2,
            name="新能源",
            code="NE",
            description="新能源汽车和光伏",
            heat_index=Decimal("88.00"),
            rise_fall_pct=Decimal("-1.20"),
            stock_count=30,
            category="能源",
            tags=["新能源", "光伏"],
            source="东方财富",
        ),
    ]


@pytest.fixture
def sample_chains():
    """示例产业链数据"""
    return [
        IndustryChain(
            id=1,
            theme_id=1,
            level="upstream",
            name="芯片设计",
            description="上游芯片设计环节",
            representative_companies=["华为海思"],
            sort_order=1,
        ),
        IndustryChain(
            id=2,
            theme_id=1,
            level="midstream",
            name="芯片制造",
            description="中游芯片制造环节",
            representative_companies=["中芯国际"],
            sort_order=2,
        ),
    ]


class TestThemeRepository:
    """ThemeRepository 测试"""

    def test_init(self, mock_session):
        """测试初始化"""
        repo = ThemeRepository(mock_session)
        assert repo.session is mock_session

    def test_tag_filter_compiles_to_mysql_json_contains(self):
        statement = select(Theme).where(_tag_contains("AI"))
        compiled = statement.compile(dialect=mysql.dialect(paramstyle="named"))
        sql = str(compiled).lower()

        assert "json_contains" in sql
        assert "json_quote" in sql
        assert "@>" not in sql
        assert "AI" in compiled.params.values()

    @pytest.mark.asyncio
    async def test_list_paginated_basic(self, mock_session, sample_themes):
        """测试基本分页查询"""
        repo = ThemeRepository(mock_session)

        # 模拟 count 查询结果
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # 模拟数据查询结果
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = sample_themes

        # 设置 execute 返回值
        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        themes, total = await repo.list_paginated(page=1, page_size=20)

        assert total == 2
        assert len(themes) == 2
        assert themes[0].name == "人工智能"

    @pytest.mark.asyncio
    async def test_list_paginated_with_category(self, mock_session, sample_themes):
        """测试按分类筛选"""
        repo = ThemeRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_themes[0]]

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        themes, total = await repo.list_paginated(page=1, page_size=20, category="科技")

        assert total == 1
        assert themes[0].category == "科技"

    @pytest.mark.asyncio
    async def test_list_paginated_empty_result(self, mock_session):
        """测试空结果"""
        repo = ThemeRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        themes, total = await repo.list_paginated(page=1, page_size=20)

        assert total == 0
        assert len(themes) == 0

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_session, sample_themes):
        """测试按 ID 查询（找到）"""
        repo = ThemeRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_themes[0]
        mock_session.execute.return_value = mock_result

        theme = await repo.get_by_id(1)

        assert theme is not None
        assert theme.id == 1
        assert theme.name == "人工智能"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session):
        """测试按 ID 查询（未找到）"""
        repo = ThemeRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        theme = await repo.get_by_id(999)

        assert theme is None

    @pytest.mark.asyncio
    async def test_search_basic(self, mock_session, sample_themes):
        """测试基本搜索"""
        repo = ThemeRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_themes[0]]

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        themes, total = await repo.search(query="人工智能", page=1, page_size=20)

        assert total == 1
        assert themes[0].name == "人工智能"

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_session):
        """测试搜索无结果"""
        repo = ThemeRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        themes, total = await repo.search(query="不存在", page=1, page_size=20)

        assert total == 0
        assert len(themes) == 0

    @pytest.mark.asyncio
    async def test_get_categories(self, mock_session):
        """测试获取分类列表"""
        repo = ThemeRepository(mock_session)

        mock_result = MagicMock()
        mock_result.all.return_value = [("科技",), ("能源",), (None,)]
        mock_session.execute.return_value = mock_result

        categories = await repo.get_categories()

        assert len(categories) == 2
        assert "科技" in categories
        assert "能源" in categories

    @pytest.mark.asyncio
    async def test_get_ranking(self, mock_session, sample_themes):
        """测试获取排名"""
        repo = ThemeRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_themes
        mock_session.execute.return_value = mock_result

        themes = await repo.get_ranking(limit=10)

        assert len(themes) == 2
        # 验证按热度降序
        assert themes[0].heat_index >= themes[1].heat_index

    @pytest.mark.asyncio
    async def test_get_industry_chains_by_theme(self, mock_session, sample_chains):
        """测试获取产业链数据"""
        repo = ThemeRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_chains
        mock_session.execute.return_value = mock_result

        chains = await repo.get_industry_chains_by_theme(theme_id=1)

        assert len(chains) == 2
        assert chains[0].level == "upstream"
        assert chains[1].level == "midstream"
