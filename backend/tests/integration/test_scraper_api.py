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
    """创建测试客户端（进入 lifespan 以注册默认爬虫）。"""
    with TestClient(app) as test_client:
        yield test_client


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

    def test_list_scraper_sources(self, client):
        """测试列出爬虫数据源"""
        response = client.get("/api/v1/scraper/sources")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2
        source_ids = {item["id"] for item in data["sources"]}
        assert "eastmoney" in source_ids
        assert "akshare" in source_ids
        eastmoney = next(item for item in data["sources"] if item["id"] == "eastmoney")
        assert eastmoney["dashboard_selectable"] is True
        assert eastmoney["is_default"] is True

    def test_list_dashboard_scraper_sources_only(self, client):
        """测试仅返回看板可选数据源"""
        response = client.get("/api/v1/scraper/sources?dashboard_only=true")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert {item["id"] for item in data["sources"]} == {"eastmoney", "akshare"}

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

    @patch("app.api.scraper.scraper_scheduler")
    @patch("app.api.scraper.ScraperRunRepository")
    def test_run_scraper_attaches_when_already_running(
        self, mock_repo_class, mock_scheduler, client
    ):
        """同数据源已在运行时复用现有 run，便于前端附着轮询。"""
        existing = MagicMock(
            spec=["id", "source", "status", "started_at", "finished_at", "items_scraped", "error_message"]
        )
        existing.id = 26
        existing.source = "eastmoney"
        existing.status = "running"
        existing.started_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        existing.finished_at = None
        existing.items_scraped = 0
        existing.error_message = None
        mock_scheduler.run = AsyncMock(return_value=26)
        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=existing)
        mock_repo_class.return_value = mock_repo

        response = client.post("/api/v1/scraper/run/eastmoney")

        assert response.status_code == 200
        assert response.json()["status"] == "running"
        assert response.json()["run_id"] == 26

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
        assert data["run_id"] == 1
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
        assert data["count"] == 1
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
        mock_repo.list_by_source.assert_called_once_with(source="sina", limit=20, status=None)

    @patch("app.api.scraper.ScraperRunRepository")
    def test_list_scraper_runs_with_limit(self, mock_repo_class, client):
        """测试限制返回数量"""
        mock_repo = AsyncMock()
        mock_repo.list_by_source = AsyncMock(return_value=[])
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/scraper/runs?limit=5")

        assert response.status_code == 200
        mock_repo.list_by_source.assert_called_once_with(source=None, limit=5, status=None)

    @patch("app.api.scraper.race_theme_quotes", new_callable=AsyncMock)
    @patch("app.api.scraper.EastMoneyScraper")
    @patch("app.api.scraper.scraper_scheduler")
    def test_refresh_quotes_allowed_while_full_scrape_running(
        self, mock_scheduler, mock_scraper_cls, mock_race, client
    ):
        """全量采集进行中时，轻量行情刷新仍可用。"""
        from datetime import date

        from app.services.quotes_refresh_race import QuotesRaceResult

        mock_scheduler.is_quotes_refresh_running.return_value = False
        mock_scheduler.quotes_refresh_lock = MagicMock()
        mock_scheduler.quotes_refresh_lock.__aenter__ = AsyncMock(return_value=None)
        mock_scheduler.quotes_refresh_lock.__aexit__ = AsyncMock(return_value=None)

        scraper = AsyncMock()
        scraper.close = AsyncMock()
        mock_scraper_cls.return_value = scraper
        mock_race.return_value = QuotesRaceResult(
            source="eastmoney",
            trade_date=date(2026, 7, 27),
            themes=[{"code": f"BK{i:04d}"} for i in range(42)],
            updated_count=42,
        )

        response = client.post("/api/v1/scraper/refresh-quotes")

        assert response.status_code == 200
        data = response.json()
        assert data["themes_updated"] == 42
        mock_race.assert_awaited()

    @patch("app.api.scraper.scraper_scheduler")
    def test_refresh_quotes_conflict_when_quotes_refresh_running(
        self, mock_scheduler, client
    ):
        """仅当另一路轻量刷新进行中时返回 409。"""
        mock_scheduler.is_quotes_refresh_running.return_value = True

        response = client.post("/api/v1/scraper/refresh-quotes")

        assert response.status_code == 409
        assert "行情刷新进行中" in response.json()["detail"]

    @patch("app.api.scraper.get_race", new_callable=AsyncMock)
    @patch("app.api.scraper.start_full_race", new_callable=AsyncMock)
    def test_run_race_success(self, mock_start, mock_get, client):
        """启动全量多源竞速返回 200。"""
        mock_start.return_value = "race-abc"
        mock_get.return_value = {
            "race_id": "race-abc",
            "status": "racing",
            "phase": "collecting",
            "progress_pct": 0,
            "sources": [
                {"id": "eastmoney", "status": "running", "progress_pct": 0, "error": None},
                {"id": "akshare", "status": "running", "progress_pct": 0, "error": None},
            ],
            "winner": None,
            "error": None,
            "items_scraped": None,
        }

        response = client.post("/api/v1/scraper/run-race")

        assert response.status_code == 200
        data = response.json()
        assert data["race_id"] == "race-abc"
        assert data["status"] == "racing"
        assert len(data["sources"]) == 2
        mock_start.assert_awaited()

    @patch("app.api.scraper.get_race", new_callable=AsyncMock)
    def test_get_race_success(self, mock_get, client):
        mock_get.return_value = {
            "race_id": "race-abc",
            "status": "committing",
            "phase": "committing",
            "progress_pct": 80,
            "sources": [
                {
                    "id": "eastmoney",
                    "status": "completed",
                    "progress_pct": 100,
                    "error": None,
                }
            ],
            "winner": "eastmoney",
            "error": None,
            "items_scraped": None,
        }

        response = client.get("/api/v1/scraper/race/race-abc")

        assert response.status_code == 200
        assert response.json()["winner"] == "eastmoney"
        assert response.json()["progress_pct"] == 80

    @patch("app.api.scraper.get_race", new_callable=AsyncMock)
    def test_get_race_not_found(self, mock_get, client):
        mock_get.side_effect = KeyError("missing")

        response = client.get("/api/v1/scraper/race/missing")

        assert response.status_code == 404
        assert response.json()["detail"] == "竞速任务不存在"

    @patch("app.api.scraper.cancel_race", new_callable=AsyncMock)
    def test_cancel_race_success(self, mock_cancel, client):
        mock_cancel.return_value = {
            "race_id": "race-abc",
            "status": "cancelled",
            "phase": "done",
            "progress_pct": 0,
            "sources": [
                {
                    "id": "eastmoney",
                    "status": "cancelled",
                    "progress_pct": 0,
                    "error": None,
                }
            ],
            "winner": None,
            "error": None,
            "items_scraped": None,
        }

        response = client.post("/api/v1/scraper/race/race-abc/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        mock_cancel.assert_awaited_once_with("race-abc")

    @patch("app.api.scraper.cancel_race", new_callable=AsyncMock)
    def test_cancel_race_not_found(self, mock_cancel, client):
        mock_cancel.side_effect = KeyError("missing")

        response = client.post("/api/v1/scraper/race/missing/cancel")

        assert response.status_code == 404
        assert response.json()["detail"] == "竞速任务不存在"

    @patch("app.api.scraper.start_full_race", new_callable=AsyncMock)
    @patch("app.api.scraper.get_race", new_callable=AsyncMock)
    def test_run_race_success(self, mock_get_race, mock_start, client):
        """启动全量竞速返回 200。"""
        mock_start.return_value = "race-abc"
        mock_get_race.return_value = {
            "race_id": "race-abc",
            "status": "racing",
            "phase": "collecting",
            "progress_pct": 0.0,
            "sources": [
                {"id": "eastmoney", "status": "running", "progress_pct": 0.0, "error": None},
                {"id": "akshare", "status": "running", "progress_pct": 0.0, "error": None},
            ],
            "winner": None,
            "error": None,
            "items_scraped": None,
        }

        response = client.post("/api/v1/scraper/run-race")

        assert response.status_code == 200
        data = response.json()
        assert data["race_id"] == "race-abc"
        assert data["status"] == "racing"
        assert len(data["sources"]) == 2
        mock_start.assert_awaited()

    @patch("app.api.scraper.get_race", new_callable=AsyncMock)
    def test_get_race_success(self, mock_get_race, client):
        """查询竞速状态返回 200。"""
        mock_get_race.return_value = {
            "race_id": "race-abc",
            "status": "completed",
            "phase": "done",
            "progress_pct": 100.0,
            "sources": [
                {"id": "eastmoney", "status": "completed", "progress_pct": 100.0, "error": None},
            ],
            "winner": "eastmoney",
            "error": None,
            "items_scraped": 42,
        }

        response = client.get("/api/v1/scraper/race/race-abc")

        assert response.status_code == 200
        data = response.json()
        assert data["winner"] == "eastmoney"
        assert data["items_scraped"] == 42

    @patch("app.api.scraper.get_race", new_callable=AsyncMock)
    def test_get_race_not_found(self, mock_get_race, client):
        """不存在的 race_id 返回 404。"""
        mock_get_race.side_effect = KeyError("missing")

        response = client.get("/api/v1/scraper/race/missing")

        assert response.status_code == 404
        assert response.json()["detail"] == "竞速任务不存在"

    @patch("app.api.scraper.cancel_race", new_callable=AsyncMock)
    def test_cancel_race_success(self, mock_cancel, client):
        """取消竞速返回 200。"""
        mock_cancel.return_value = {
            "race_id": "race-abc",
            "status": "cancelled",
            "phase": "done",
            "progress_pct": 0.0,
            "sources": [
                {"id": "eastmoney", "status": "cancelled", "progress_pct": 0.0, "error": None},
            ],
            "winner": None,
            "error": None,
            "items_scraped": None,
        }

        response = client.post("/api/v1/scraper/race/race-abc/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        mock_cancel.assert_awaited_once_with("race-abc")

    @patch("app.api.scraper.cancel_race", new_callable=AsyncMock)
    def test_cancel_race_not_found(self, mock_cancel, client):
        """取消不存在的 race 返回 404。"""
        mock_cancel.side_effect = KeyError("missing")

        response = client.post("/api/v1/scraper/race/missing/cancel")

        assert response.status_code == 404
        assert response.json()["detail"] == "竞速任务不存在"
