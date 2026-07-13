"""Scraper API 集成测试

测试爬虫 API 端点的完整请求流程。
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.scraper import (
    ScraperRunResponse,
    ScraperRunListResponse,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_scraper_run():
    """示例爬虫运行记录"""
    return ScraperRunResponse(
        id=1,
        source="eastmoney",
        status="completed",
        started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
        items_scraped=150,
        error_message=None,
    )


@pytest.fixture
def sample_scraper_run_list(sample_scraper_run):
    """示例爬虫运行记录列表"""
    return ScraperRunListResponse(
        runs=[sample_scraper_run],
        total=1,
    )


class TestScraperAPI:
    """Scraper API 测试"""

    @patch("app.api.scraper.scraper_scheduler")
    @patch("app.api.scraper.ScraperRunRepository")
    def test_run_scraper_success(
        self, mock_repo_class, mock_scheduler, client, sample_scraper_run
    ):
        """测试成功触发爬虫运行"""
        # Mock scheduler
        mock_scheduler.run = AsyncMock(return_value=1)

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=MagicMock(
            id=1,
            source="eastmoney",
            status="completed",
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            items_scraped=150,
            error_message=None,
        ))
        mock_repo_class.return_value = mock_repo

        response = client.post("/api/v1/scraper/run/eastmoney")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "eastmoney"
        assert data["status"] == "completed"

    @patch("app.api.scraper.scraper_scheduler")
    def test_run_scraper_not_found(self, mock_scheduler, client):
        """测试触发不存在的爬虫"""
        mock_scheduler.run = AsyncMock(
            side_effect=ValueError("未知的数据源: invalid_source")
        )

        response = client.post("/api/v1/scraper/run/invalid_source")

        assert response.status_code == 404
        assert "未知的数据源" in response.json()["detail"]

    @patch("app.api.scraper.ScraperRunRepository")
    def test_get_scraper_status(self, mock_repo_class, client, sample_scraper_run):
        """测试获取爬虫运行状态"""
        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=MagicMock(
            id=1,
            source="eastmoney",
            status="completed",
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            items_scraped=150,
            error_message=None,
        ))
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/scraper/status/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "completed"

    @patch("app.api.scraper.ScraperRunRepository")
    def test_get_scraper_status_not_found(self, mock_repo_class, client):
        """测试获取不存在的运行记录"""
        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/scraper/status/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "运行记录不存在"

    @patch("app.api.scraper.ScraperRunRepository")
    def test_list_scraper_runs(self, mock_repo_class, client):
        """测试列出爬虫运行记录"""
        mock_repo = AsyncMock()
        mock_repo.list_by_source = AsyncMock(return_value=[
            MagicMock(
                id=1,
                source="eastmoney",
                status="completed",
                started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
                items_scraped=150,
                error_message=None,
            )
        ])
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/scraper/runs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["runs"]) == 1
        assert data["runs"][0]["source"] == "eastmoney"

    @patch("app.api.scraper.ScraperRunRepository")
    def test_list_scraper_runs_with_source_filter(self, mock_repo_class, client):
        """测试按数据源筛选运行记录"""
        mock_repo = AsyncMock()
        mock_repo.list_by_source = AsyncMock(return_value=[])
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/scraper/runs?source=sina")

        assert response.status_code == 200
        mock_repo.list_by_source.assert_called_once_with(source="sina", limit=20)

    @patch("app.api.scraper.ScraperRunRepository")
    def test_list_scraper_runs_with_limit(self, mock_repo_class, client):
        """测试限制返回数量"""
        mock_repo = AsyncMock()
        mock_repo.list_by_source = AsyncMock(return_value=[])
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/scraper/runs?limit=5")

        assert response.status_code == 200
        mock_repo.list_by_source.assert_called_once_with(source=None, limit=5)
