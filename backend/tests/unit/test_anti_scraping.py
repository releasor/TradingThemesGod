"""反爬虫中间件单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.anti_scraping import AntiScrapingMiddleware, UserAgentRotator


def test_user_agent_rotator():
    """测试 UA 轮换器返回随机 UA"""
    rotator = UserAgentRotator()

    ua1 = rotator.get_random_ua()
    ua2 = rotator.get_random_ua()

    assert isinstance(ua1, str)
    assert len(ua1) > 0
    assert "Mozilla" in ua1


def test_user_agent_rotator_custom_list():
    """测试自定义 UA 列表"""
    custom_uas = ["TestAgent/1.0", "TestAgent/2.0"]
    rotator = UserAgentRotator(user_agents=custom_uas)

    ua = rotator.get_random_ua()
    assert ua in custom_uas


@pytest.mark.asyncio
async def test_middleware_sets_user_agent():
    """测试中间件设置随机 User-Agent"""
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch.object(middleware, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        mock_get_client.return_value = mock_client

        response = await middleware.get("http://example.com")

        # 验证请求被调用且 headers 包含 User-Agent
        call_args = mock_client.request.call_args
        headers = call_args[1].get("headers", call_args.kwargs.get("headers", {}))
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]

    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_retry_on_429():
    """测试 429 状态码触发重试"""
    middleware = AntiScrapingMiddleware(
        min_interval=0, max_interval=0, max_retries=2
    )

    # 模拟第一次返回 429，第二次返回 200
    response_429 = MagicMock()
    response_429.status_code = 429
    response_429.raise_for_status = MagicMock()

    response_200 = MagicMock()
    response_200.status_code = 200
    response_200.raise_for_status = MagicMock()

    with patch.object(middleware, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            side_effect=[response_429, response_200]
        )
        mock_client.is_closed = False
        mock_get_client.return_value = mock_client

        with patch("app.scrapers.anti_scraping.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.get("http://example.com")

        assert response.status_code == 200
        assert mock_client.request.call_count == 2

    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_retry_on_503():
    """测试 503 状态码触发重试"""
    middleware = AntiScrapingMiddleware(
        min_interval=0, max_interval=0, max_retries=1
    )

    response_503 = MagicMock()
    response_503.status_code = 503
    response_503.raise_for_status = MagicMock()

    response_200 = MagicMock()
    response_200.status_code = 200
    response_200.raise_for_status = MagicMock()

    with patch.object(middleware, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            side_effect=[response_503, response_200]
        )
        mock_client.is_closed = False
        mock_get_client.return_value = mock_client

        with patch("app.scrapers.anti_scraping.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.get("http://example.com")

        assert response.status_code == 200

    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_proxy_configuration():
    """测试代理配置"""
    middleware = AntiScrapingMiddleware(proxy_url="http://proxy:8080")

    assert middleware.proxy_url == "http://proxy:8080"
