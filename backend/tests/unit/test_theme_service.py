"""ThemeService 单元测试

测试题材服务的业务逻辑。
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.models.theme import Theme
from app.models.industry_chain import IndustryChain
from app.services.theme import ThemeService
from app.schemas.theme import (
    ThemeBrief,
    ThemeDetailResponse,
    ThemeListResponse,
    ThemeRankingResponse,
    ThemeCategoriesResponse,
    IndustryChainBrief,
)


@pytest.fixture
def mock_session():
    """创建模拟的 AsyncSession"""
    return AsyncMock()


@pytest.fixture
def sample_theme():
    """示例题材"""
    return Theme(
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
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )


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
        IndustryChain(
            id=3,
            theme_id=1,
            level="downstream",
            name="终端应用",
            description="下游终端应用环节",
            representative_companies=["小米"],
            sort_order=3,
        ),
    ]


class TestThemeService:
    """ThemeService 测试"""

    def test_init(self, mock_session):
        """测试初始化"""
        service = ThemeService(mock_session)
        assert service.session is mock_session
        assert service.repo is not None

    @pytest.mark.asyncio
    async def test_list_themes_basic(self, mock_session, sample_theme):
        """测试基本列表查询"""
        service = ThemeService(mock_session)

        # Mock repository
        service.repo.list_paginated = AsyncMock(return_value=([sample_theme], 1))

        result = await service.list_themes(page=1, page_size=20)

        assert isinstance(result, ThemeListResponse)
        assert len(result.items) == 1
        assert result.total == 1
        assert result.page == 1
        assert result.page_size == 20
        assert result.total_pages == 1
        assert result.items[0].name == "人工智能"

    @pytest.mark.asyncio
    async def test_list_themes_empty(self, mock_session):
        """测试空列表"""
        service = ThemeService(mock_session)

        service.repo.list_paginated = AsyncMock(return_value=([], 0))

        result = await service.list_themes(page=1, page_size=20)

        assert isinstance(result, ThemeListResponse)
        assert len(result.items) == 0
        assert result.total == 0
        assert result.total_pages == 0

    @pytest.mark.asyncio
    async def test_get_theme_detail_found(self, mock_session, sample_theme, sample_chains):
        """测试获取详情（找到）"""
        service = ThemeService(mock_session)

        # 设置 theme 的 industry_chains 关系
        sample_theme.industry_chains = sample_chains
        service.repo.get_by_id = AsyncMock(return_value=sample_theme)

        result = await service.get_theme_detail(theme_id=1)

        assert isinstance(result, ThemeDetailResponse)
        assert result.id == 1
        assert result.name == "人工智能"
        assert "upstream" in result.industry_chains
        assert "midstream" in result.industry_chains
        assert "downstream" in result.industry_chains
        assert len(result.industry_chains["upstream"]) == 1
        assert result.industry_chains["upstream"][0].name == "芯片设计"

    @pytest.mark.asyncio
    async def test_get_theme_detail_not_found(self, mock_session):
        """测试获取详情（未找到）"""
        service = ThemeService(mock_session)

        service.repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_theme_detail(theme_id=999)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "题材不存在"

    @pytest.mark.asyncio
    async def test_search_themes_basic(self, mock_session, sample_theme):
        """测试基本搜索"""
        service = ThemeService(mock_session)

        service.repo.search = AsyncMock(return_value=([sample_theme], 1))

        result = await service.search_themes(query="人工智能", page=1, page_size=20)

        assert isinstance(result, ThemeListResponse)
        assert len(result.items) == 1
        assert result.total == 1
        assert result.items[0].name == "人工智能"

    @pytest.mark.asyncio
    async def test_get_categories(self, mock_session):
        """测试获取分类列表"""
        service = ThemeService(mock_session)

        service.repo.get_categories = AsyncMock(return_value=["科技", "能源"])

        result = await service.get_categories()

        assert isinstance(result, ThemeCategoriesResponse)
        assert len(result.categories) == 2
        assert "科技" in result.categories
        assert "能源" in result.categories

    @pytest.mark.asyncio
    async def test_get_ranking(self, mock_session, sample_theme):
        """测试获取排名"""
        service = ThemeService(mock_session)

        service.repo.get_ranking = AsyncMock(return_value=[sample_theme])

        result = await service.get_ranking(limit=10)

        assert isinstance(result, ThemeRankingResponse)
        assert len(result.items) == 1
        assert result.limit == 10
        assert result.items[0].name == "人工智能"

    @pytest.mark.asyncio
    async def test_get_theme_detail_groups_chains_by_level(
        self, mock_session, sample_theme, sample_chains
    ):
        """测试详情接口按层级分组产业链"""
        service = ThemeService(mock_session)

        sample_theme.industry_chains = sample_chains
        service.repo.get_by_id = AsyncMock(return_value=sample_theme)

        result = await service.get_theme_detail(theme_id=1)

        # 验证每个层级都有数据
        assert len(result.industry_chains["upstream"]) == 1
        assert len(result.industry_chains["midstream"]) == 1
        assert len(result.industry_chains["downstream"]) == 1

        # 验证层级数据正确
        assert result.industry_chains["upstream"][0].level == "upstream"
        assert result.industry_chains["midstream"][0].level == "midstream"
        assert result.industry_chains["downstream"][0].level == "downstream"

    @pytest.mark.asyncio
    async def test_get_theme_detail_empty_chains(self, mock_session, sample_theme):
        """测试详情接口（无产业链数据）"""
        service = ThemeService(mock_session)

        sample_theme.industry_chains = []
        service.repo.get_by_id = AsyncMock(return_value=sample_theme)

        result = await service.get_theme_detail(theme_id=1)

        assert isinstance(result, ThemeDetailResponse)
        assert len(result.industry_chains["upstream"]) == 0
        assert len(result.industry_chains["midstream"]) == 0
        assert len(result.industry_chains["downstream"]) == 0
