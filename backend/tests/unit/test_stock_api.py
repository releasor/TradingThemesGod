"""股票和事件 API 端点测试

使用 mock 服务层测试 API 路由行为。
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.stock import (
    StockBrief,
    StockDetailResponse,
    StockListResponse,
    EventBrief,
    EventListResponse,
)


@pytest.fixture
def sample_stock_brief():
    """示例股票简要数据"""
    return StockBrief(
        id=1,
        code="600000",
        name="浦发银行",
        industry="银行",
        market_cap=Decimal("1000000.00"),
        current_price=Decimal("10.50"),
        rise_fall_pct=Decimal("1.25"),
        exchange="SH",
    )


@pytest.fixture
def sample_stock_list_response(sample_stock_brief):
    """示例股票列表响应"""
    return StockListResponse(
        items=[sample_stock_brief],
        total=1,
        page=1,
        page_size=20,
        total_pages=1,
    )


@pytest.fixture
def sample_event_brief():
    """示例事件简要数据"""
    return EventBrief(
        id=1,
        title="浦发银行发布年报",
        content="详细内容",
        source="东方财富",
        event_type="公告",
        published_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_stock_detail_response(sample_event_brief):
    """示例股票详情响应"""
    now = datetime.now(timezone.utc)
    return StockDetailResponse(
        id=1,
        code="600000",
        name="浦发银行",
        industry="银行",
        market_cap=Decimal("1000000.00"),
        current_price=Decimal("10.50"),
        rise_fall_pct=Decimal("1.25"),
        exchange="SH",
        created_at=now,
        updated_at=now,
        recent_events=[sample_event_brief],
    )


@pytest.fixture
def sample_event_list_response(sample_event_brief):
    """示例事件列表响应"""
    return EventListResponse(
        items=[sample_event_brief],
        total=1,
        page=1,
        page_size=20,
        total_pages=1,
    )


class TestListStocks:
    """GET /api/v1/stocks 测试"""

    @pytest.mark.asyncio
    async def test_list_stocks_returns_paginated_response(
        self, client, sample_stock_list_response
    ):
        """验证返回分页股票列表"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.list_stocks = AsyncMock(
                return_value=sample_stock_list_response
            )
            response = await client.get("/api/v1/stocks?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["code"] == "600000"
        assert data["items"][0]["name"] == "浦发银行"
        assert data["items"][0]["industry"] == "银行"

    @pytest.mark.asyncio
    async def test_list_stocks_with_industry_filter(
        self, client, sample_stock_list_response
    ):
        """验证按行业筛选"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.list_stocks = AsyncMock(
                return_value=sample_stock_list_response
            )
            response = await client.get("/api/v1/stocks?industry=银行")

        assert response.status_code == 200
        mock_instance.list_stocks.assert_called_once()
        call_kwargs = mock_instance.list_stocks.call_args
        assert call_kwargs[1]["industry"] == "银行"

    @pytest.mark.asyncio
    async def test_list_stocks_with_exchange_filter(
        self, client, sample_stock_list_response
    ):
        """验证按交易所筛选"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.list_stocks = AsyncMock(
                return_value=sample_stock_list_response
            )
            response = await client.get("/api/v1/stocks?exchange=SH")

        assert response.status_code == 200
        call_kwargs = mock_instance.list_stocks.call_args
        assert call_kwargs[1]["exchange"] == "SH"

    @pytest.mark.asyncio
    async def test_list_stocks_default_params(self, client, sample_stock_list_response):
        """验证默认参数"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.list_stocks = AsyncMock(
                return_value=sample_stock_list_response
            )
            response = await client.get("/api/v1/stocks")

        assert response.status_code == 200
        call_kwargs = mock_instance.list_stocks.call_args
        assert call_kwargs[1]["page"] == 1
        assert call_kwargs[1]["page_size"] == 20
        assert call_kwargs[1]["sort_by"] == "code"
        assert call_kwargs[1]["order"] == "asc"


class TestGetStockDetail:
    """GET /api/v1/stocks/{code} 测试"""

    @pytest.mark.asyncio
    async def test_get_stock_detail_returns_detail(
        self, client, sample_stock_detail_response
    ):
        """验证返回股票详情（含最近5条事件）"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_stock_detail = AsyncMock(
                return_value=sample_stock_detail_response
            )
            response = await client.get("/api/v1/stocks/600000")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "600000"
        assert data["name"] == "浦发银行"
        assert "recent_events" in data
        assert len(data["recent_events"]) == 1

    @pytest.mark.asyncio
    async def test_get_stock_detail_404_for_invalid_code(self, client):
        """验证不存在的股票代码返回 404"""
        from fastapi import HTTPException

        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_stock_detail = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="股票不存在")
            )
            response = await client.get("/api/v1/stocks/INVALID")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "股票不存在" in data["detail"]


class TestGetStockEvents:
    """GET /api/v1/stocks/{code}/events 测试"""

    @pytest.mark.asyncio
    async def test_get_stock_events_returns_sorted_events(
        self, client, sample_event_list_response
    ):
        """验证返回按 published_at 降序排列的事件"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_stock_events = AsyncMock(
                return_value=sample_event_list_response
            )
            response = await client.get("/api/v1/stocks/600000/events")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "浦发银行发布年报"

    @pytest.mark.asyncio
    async def test_get_stock_events_404_for_invalid_code(self, client):
        """验证不存在的股票代码返回 404"""
        from fastapi import HTTPException

        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_stock_events = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="股票不存在")
            )
            response = await client.get("/api/v1/stocks/INVALID/events")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_stock_events_pagination(self, client, sample_event_list_response):
        """验证分页参数"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_stock_events = AsyncMock(
                return_value=sample_event_list_response
            )
            response = await client.get(
                "/api/v1/stocks/600000/events?page=2&page_size=10"
            )

        assert response.status_code == 200
        call_kwargs = mock_instance.get_stock_events.call_args
        assert call_kwargs[1]["page"] == 2
        assert call_kwargs[1]["page_size"] == 10


class TestListEvents:
    """GET /api/v1/events 测试"""

    @pytest.mark.asyncio
    async def test_list_events_returns_paginated_response(
        self, client, sample_event_list_response
    ):
        """验证返回分页事件列表"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.list_events = AsyncMock(
                return_value=sample_event_list_response
            )
            response = await client.get("/api/v1/events")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_events_with_event_type_filter(
        self, client, sample_event_list_response
    ):
        """验证按事件类型筛选"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.list_events = AsyncMock(
                return_value=sample_event_list_response
            )
            response = await client.get("/api/v1/events?event_type=公告")

        assert response.status_code == 200
        call_kwargs = mock_instance.list_events.call_args
        assert call_kwargs[1]["event_type"] == "公告"

    @pytest.mark.asyncio
    async def test_list_events_default_sort_by_published_at_desc(
        self, client, sample_event_list_response
    ):
        """验证默认按 published_at 降序"""
        with patch("app.api.stock.StockService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.list_events = AsyncMock(
                return_value=sample_event_list_response
            )
            response = await client.get("/api/v1/events")

        assert response.status_code == 200
        call_kwargs = mock_instance.list_events.call_args
        assert call_kwargs[1]["sort_by"] == "published_at"
        assert call_kwargs[1]["order"] == "desc"


class TestThemeStocks:
    """GET /api/v1/themes/{theme_id}/stocks 测试"""

    @pytest.mark.asyncio
    async def test_get_theme_stocks_returns_stock_list(
        self, client, sample_stock_list_response
    ):
        """验证返回题材关联的股票列表"""
        with patch("app.api.theme.ThemeService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_theme_stocks = AsyncMock(
                return_value=sample_stock_list_response
            )
            response = await client.get("/api/v1/themes/1/stocks")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_theme_stocks_with_chain_level_filter(
        self, client, sample_stock_list_response
    ):
        """验证按 chain_level 筛选"""
        with patch("app.api.theme.ThemeService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_theme_stocks = AsyncMock(
                return_value=sample_stock_list_response
            )
            response = await client.get(
                "/api/v1/themes/1/stocks?chain_level=upstream"
            )

        assert response.status_code == 200
        call_kwargs = mock_instance.get_theme_stocks.call_args
        assert call_kwargs[1]["chain_level"] == "upstream"

    @pytest.mark.asyncio
    async def test_get_theme_stocks_404_for_invalid_theme(self, client):
        """验证不存在的题材返回 404"""
        from fastapi import HTTPException

        with patch("app.api.theme.ThemeService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get_theme_stocks = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="题材不存在")
            )
            response = await client.get("/api/v1/themes/999/stocks")

        assert response.status_code == 404
        data = response.json()
        assert "题材不存在" in data["detail"]
