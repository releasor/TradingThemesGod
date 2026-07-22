"""Anti-scraping middleware extended unit tests."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.anti_scraping import AntiScrapingMiddleware, RETRYABLE_STATUS_CODES


def test_retryable_status_codes():
    assert 429 in RETRYABLE_STATUS_CODES
    assert 500 in RETRYABLE_STATUS_CODES
    assert 502 in RETRYABLE_STATUS_CODES
    assert 503 in RETRYABLE_STATUS_CODES
    assert 504 in RETRYABLE_STATUS_CODES
    assert 200 not in RETRYABLE_STATUS_CODES
    assert 404 not in RETRYABLE_STATUS_CODES


@pytest.mark.asyncio
async def test_middleware_post_method():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    with patch.object(middleware, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        mock_get_client.return_value = mock_client
        response = await middleware.post("http://example.com/api", json={"key": "value"})
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "http://example.com/api"
    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_retry_on_timeout():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0, max_retries=2)
    response_200 = MagicMock()
    response_200.status_code = 200
    with patch.object(middleware, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[httpx.TimeoutException("timeout"), response_200])
        mock_client.is_closed = False
        mock_get_client.return_value = mock_client
        with patch("app.scrapers.anti_scraping.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.get("http://example.com")
        assert response.status_code == 200
        assert mock_client.request.call_count == 2
    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_retry_on_connect_error():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0, max_retries=1)
    response_200 = MagicMock()
    response_200.status_code = 200
    with patch.object(middleware, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[httpx.ConnectError("fail"), response_200])
        mock_client.is_closed = False
        mock_get_client.return_value = mock_client
        with patch("app.scrapers.anti_scraping.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.get("http://example.com")
        assert response.status_code == 200
        assert mock_client.request.call_count == 2
    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_retry_exhaustion_on_timeout():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0, max_retries=1)
    with patch.object(middleware, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.is_closed = False
        mock_get_client.return_value = mock_client
        with patch("app.scrapers.anti_scraping.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.TimeoutException):
                await middleware.get("http://example.com")
        assert mock_client.request.call_count == 2
    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_retry_exhaustion_on_connect_error():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0, max_retries=2)
    with patch.object(middleware, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("fail"))
        mock_client.is_closed = False
        mock_get_client.return_value = mock_client
        with patch("app.scrapers.anti_scraping.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.ConnectError):
                await middleware.get("http://example.com")
        assert mock_client.request.call_count == 3
    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_close():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0)
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    mock_client.is_closed = False
    middleware._client = mock_client
    await middleware.close()
    mock_client.aclose.assert_called_once()
    assert middleware._client is None


@pytest.mark.asyncio
async def test_middleware_close_when_no_client():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0)
    middleware._client = None
    await middleware.close()


@pytest.mark.asyncio
async def test_middleware_close_when_already_closed():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0)
    mock_client = AsyncMock()
    mock_client.is_closed = True
    middleware._client = mock_client
    await middleware.close()
    mock_client.aclose.assert_not_called()


def test_middleware_default_parameters():
    middleware = AntiScrapingMiddleware()
    assert middleware.min_interval == 1.0
    assert middleware.max_interval == 3.0
    assert middleware.max_retries == 3
    assert middleware.proxy_url is None


def test_middleware_custom_parameters():
    middleware = AntiScrapingMiddleware(proxy_url="http://proxy:3128", min_interval=0.5, max_interval=2.0, max_retries=5)
    assert middleware.proxy_url == "http://proxy:3128"
    assert middleware.min_interval == 0.5
    assert middleware.max_interval == 2.0
    assert middleware.max_retries == 5
