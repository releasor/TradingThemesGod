"""健康检查 API 端点测试

测试 GET /api/v1/health 端点的正常和异常场景。
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def mock_pool():
    """模拟连接池"""
    pool = MagicMock()
    pool.size.return_value = 10
    pool.checkedin.return_value = 8
    pool.checkedout.return_value = 2
    pool.overflow.return_value = 0
    return pool


@pytest.fixture
def mock_engine(mock_pool):
    """模拟数据库引擎"""
    engine = MagicMock()
    engine.pool = mock_pool
    return engine


@pytest.fixture
def mock_settings():
    """模拟应用配置"""
    settings = MagicMock()
    settings.APP_ENV = "testing"
    return settings


class TestHealthCheck:
    """GET /api/v1/health 测试"""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, client, mock_engine, mock_settings):
        """验证数据库正常时返回 200 和健康状态"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        with (
            patch("app.api.health.engine", mock_engine),
            patch("app.api.health.get_settings", return_value=mock_settings),
            patch("app.core.database.AsyncSessionLocal") as mock_session_local,
        ):
            mock_session_local.return_value.__aenter__ = AsyncMock(
                return_value=mock_db
            )
            mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)
            response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "testing"
        assert data["database"] == "connected"
        assert "response_time_ms" in data
        assert isinstance(data["response_time_ms"], (int, float))
        assert data["pool"]["size"] == 10
        assert data["pool"]["checked_in"] == 8
        assert data["pool"]["checked_out"] == 2
        assert data["pool"]["overflow"] == 0

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_db_error(
        self, client, mock_engine, mock_settings
    ):
        """验证数据库连接失败时返回 503 和异常状态"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("Connection refused"))

        with (
            patch("app.api.health.engine", mock_engine),
            patch("app.api.health.get_settings", return_value=mock_settings),
            patch("app.core.database.AsyncSessionLocal") as mock_session_local,
        ):
            mock_session_local.return_value.__aenter__ = AsyncMock(
                return_value=mock_db
            )
            mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)
            response = await client.get("/api/v1/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Connection refused" in data["database"]
        assert data["version"] == "testing"
        assert "response_time_ms" in data
        assert data["pool"]["size"] == 10
