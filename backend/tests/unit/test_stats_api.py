"""数据统计 API 端点测试

测试 GET /api/v1/stats 端点。
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestGetStats:
    """GET /api/v1/stats 测试"""

    @pytest.mark.asyncio
    async def test_get_stats_returns_all_counts(self, client):
        """验证返回所有统计数据"""
        with (
            patch("app.api.stats._query_theme_count", new_callable=AsyncMock, return_value=100),
            patch("app.api.stats._query_stock_count", new_callable=AsyncMock, return_value=500),
            patch("app.api.stats._query_event_count", new_callable=AsyncMock, return_value=1000),
            patch("app.api.stats._query_chain_count", new_callable=AsyncMock, return_value=50),
            patch("app.api.stats._query_last_scraper", new_callable=AsyncMock, return_value={
                "id": 1, "source": "eastmoney", "status": "completed", "created_at": "2026-01-01T00:00:00"
            }),
            patch("app.api.stats._query_category_stats", new_callable=AsyncMock, return_value=[
                {"category": "科技", "count": 30},
                {"category": "医药", "count": 20},
            ]),
        ):
            response = await client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["themes"]["total"] == 100
        assert data["stocks"]["total"] == 500
        assert data["events"]["total"] == 1000
        assert data["chains"]["total"] == 50
        assert data["scraper"]["last_run"]["source"] == "eastmoney"
        assert len(data["themes"]["categories"]) == 2

    @pytest.mark.asyncio
    async def test_get_stats_with_no_scraper_runs(self, client):
        """验证没有爬虫运行记录时 last_run 为 null"""
        with (
            patch("app.api.stats._query_theme_count", new_callable=AsyncMock, return_value=0),
            patch("app.api.stats._query_stock_count", new_callable=AsyncMock, return_value=0),
            patch("app.api.stats._query_event_count", new_callable=AsyncMock, return_value=0),
            patch("app.api.stats._query_chain_count", new_callable=AsyncMock, return_value=0),
            patch("app.api.stats._query_last_scraper", new_callable=AsyncMock, return_value=None),
            patch("app.api.stats._query_category_stats", new_callable=AsyncMock, return_value=[]),
        ):
            response = await client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["scraper"]["last_run"] is None
        assert data["themes"]["total"] == 0
