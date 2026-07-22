"""Theme API 集成测试

测试题材 API 端点的完整请求流程。
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.theme import (
    IndustryChainBrief,
    ThemeBrief,
    ThemeCategoriesResponse,
    ThemeDetailResponse,
    ThemeListResponse,
    ThemeRankingResponse,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_theme_brief():
    """示例题材简要数据"""
    return ThemeBrief(
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
    )


@pytest.fixture
def sample_theme_list_response(sample_theme_brief):
    """示例题材列表响应"""
    return ThemeListResponse(
        items=[sample_theme_brief],
        total=1,
        page=1,
        page_size=20,
        total_pages=1,
    )


@pytest.fixture
def sample_theme_detail():
    """示例题材详情响应"""
    return ThemeDetailResponse(
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
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 15, tzinfo=UTC),
        industry_chains={
            "upstream": [
                IndustryChainBrief(
                    id=1,
                    level="upstream",
                    name="芯片设计",
                    description="上游芯片设计环节",
                    representative_companies=["华为海思"],
                    sort_order=1,
                )
            ],
            "midstream": [],
            "downstream": [],
        },
        chain_stock_counts={
            "upstream": 0,
            "midstream": 0,
            "downstream": 0,
        },
    )


@pytest.fixture
def sample_ranking_response(sample_theme_brief):
    """示例排名响应"""
    return ThemeRankingResponse(
        items=[sample_theme_brief],
        limit=10,
    )


@pytest.fixture
def sample_categories_response():
    """示例分类响应"""
    return ThemeCategoriesResponse(categories=["科技", "能源"])


class TestThemeAPI:
    """Theme API 测试"""

    @patch("app.api.theme.ThemeInsightRefreshService")
    def test_refresh_theme_insights(self, mock_service_class, client):
        service = mock_service_class.return_value
        service.refresh = AsyncMock(
            return_value={
                "theme_id": 1,
                "theme_name": "机器人",
                "profile_updated": True,
                "candidate_events": 2,
                "inserted_events": 1,
                "updated_events": 0,
                "ignored_events": 1,
                "successful_sources": ["示例网"],
                "failed_sources": [],
                "degraded": False,
                "refreshed_at": datetime(2026, 7, 20, tzinfo=UTC),
                "message": "题材资料已更新",
            }
        )
        service.research.middleware.close = AsyncMock()

        response = client.post("/api/v1/themes/1/insights/refresh")

        assert response.status_code == 200
        assert response.json()["message"] == "题材资料已更新"
        service.research.middleware.close.assert_awaited_once()

    @patch("app.api.theme.ThemeInsightRefreshService")
    def test_refresh_theme_insights_closes_client_after_failure(
        self, mock_service_class, client
    ):
        service = mock_service_class.return_value
        service.refresh = AsyncMock(
            side_effect=HTTPException(status_code=502, detail="公开来源不可用")
        )
        service.research.middleware.close = AsyncMock()

        response = client.post("/api/v1/themes/1/insights/refresh")

        assert response.status_code == 502
        service.research.middleware.close.assert_awaited_once()

    @patch("app.api.theme.ThemeService")
    def test_list_themes_basic(
        self, mock_service_class, client, sample_theme_list_response
    ):
        """测试基本列表查询"""
        mock_service = AsyncMock()
        mock_service.list_themes.return_value = sample_theme_list_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "人工智能"

    @patch("app.api.theme.ThemeService")
    def test_list_themes_with_pagination(
        self, mock_service_class, client, sample_theme_list_response
    ):
        """测试分页参数"""
        mock_service = AsyncMock()
        mock_service.list_themes.return_value = sample_theme_list_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes?page=2&page_size=10")

        assert response.status_code == 200
        mock_service.list_themes.assert_called_once_with(
            page=2,
            page_size=10,
            sort_by="heat_index",
            sort_order="desc",
            category=None,
            tags=None,
        )

    @patch("app.api.theme.ThemeService")
    def test_list_themes_with_category(
        self, mock_service_class, client, sample_theme_list_response
    ):
        """测试按分类筛选"""
        mock_service = AsyncMock()
        mock_service.list_themes.return_value = sample_theme_list_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes?category=科技")

        assert response.status_code == 200
        mock_service.list_themes.assert_called_once_with(
            page=1,
            page_size=20,
            sort_by="heat_index",
            sort_order="desc",
            category="科技",
            tags=None,
        )

    @patch("app.api.theme.ThemeService")
    def test_list_themes_with_sorting(
        self, mock_service_class, client, sample_theme_list_response
    ):
        """测试排序参数"""
        mock_service = AsyncMock()
        mock_service.list_themes.return_value = sample_theme_list_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes?sort_by=rise_fall_pct&sort_order=asc")

        assert response.status_code == 200
        mock_service.list_themes.assert_called_once_with(
            page=1,
            page_size=20,
            sort_by="rise_fall_pct",
            sort_order="asc",
            category=None,
            tags=None,
        )

    @patch("app.api.theme.ThemeService")
    def test_get_theme_ranking(
        self, mock_service_class, client, sample_ranking_response
    ):
        """测试获取排名"""
        mock_service = AsyncMock()
        mock_service.get_ranking.return_value = sample_ranking_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes/ranking?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["limit"] == 10

    @patch("app.api.theme.ThemeService")
    def test_get_market_signals(
        self, mock_service_class, client, sample_ranking_response
    ):
        mock_service = AsyncMock()
        mock_service.get_market_signals.return_value = sample_ranking_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes/market-signals")

        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == 1
        mock_service.get_market_signals.assert_awaited_once_with()

    @patch("app.api.theme.ThemeService")
    def test_get_indicator_signals(
        self, mock_service_class, client, sample_ranking_response
    ):
        mock_service = AsyncMock()
        mock_service.get_indicator_signals.return_value = sample_ranking_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes/indicator-signals")

        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == 1
        mock_service.get_indicator_signals.assert_awaited_once_with()

    @patch("app.api.theme.ThemeService")
    def test_get_theme_categories(
        self, mock_service_class, client, sample_categories_response
    ):
        """测试获取分类列表"""
        mock_service = AsyncMock()
        mock_service.get_categories.return_value = sample_categories_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes/categories")

        assert response.status_code == 200
        data = response.json()
        assert len(data["categories"]) == 2
        assert "科技" in data["categories"]

    @patch("app.api.theme.ThemeService")
    def test_search_themes(
        self, mock_service_class, client, sample_theme_list_response
    ):
        """测试搜索题材"""
        mock_service = AsyncMock()
        mock_service.search_themes.return_value = sample_theme_list_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes/search?q=人工智能")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "人工智能"

    @patch("app.api.theme.ThemeService")
    def test_get_theme_detail(self, mock_service_class, client, sample_theme_detail):
        """测试获取题材详情"""
        mock_service = AsyncMock()
        mock_service.get_theme_detail.return_value = sample_theme_detail
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "人工智能"
        assert "industry_chains" in data
        assert "upstream" in data["industry_chains"]

    @patch("app.api.theme.ThemeService")
    def test_get_theme_detail_not_found(self, mock_service_class, client):
        """测试获取题材详情（不存在）"""
        from fastapi import HTTPException

        mock_service = AsyncMock()
        mock_service.get_theme_detail.side_effect = HTTPException(
            status_code=404, detail="题材不存在"
        )
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "题材不存在"

    @patch("app.api.theme.ThemeService")
    def test_search_themes_empty(self, mock_service_class, client):
        """测试搜索无结果"""
        empty_response = ThemeListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )

        mock_service = AsyncMock()
        mock_service.search_themes.return_value = empty_response
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/themes/search?q=不存在")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
