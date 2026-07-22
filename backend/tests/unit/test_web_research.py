"""公开网页研究服务测试。"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.web_research import (
    WebResearchService,
    _extract_search_urls,
    _merge_urls,
    _search_redirect_url,
    extract_page_text,
    validate_public_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:8000/api",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com/file",
    ],
)
@pytest.mark.asyncio
async def test_validate_public_url_rejects_unsafe_targets(url):
    with pytest.raises(ValueError, match="公网"):
        await validate_public_url(url)


def test_extract_page_text_removes_scripts_and_navigation():
    html = """
    <html><head><title>机器人产业链</title><script>secret()</script></head>
    <body><nav>菜单</nav><article><h1>灵巧手</h1><p>触觉传感包含电子皮肤。</p></article></body></html>
    """

    title, text = extract_page_text(html)

    assert title == "机器人产业链"
    assert "电子皮肤" in text
    assert "secret" not in text
    assert "菜单" not in text


@pytest.mark.parametrize(
    ("html", "selector"),
    [
        (
            '<a class="result__a" href="https://example.com/duck">Duck</a>',
            "a.result__a",
        ),
        (
            '<li class="b_algo"><h2><a href="https://example.com/bing">Bing</a></h2></li>',
            "li.b_algo h2 a",
        ),
        (
            '<li class="res-list"><h3><a href="https://example.com/so">360</a></h3></li>',
            ".res-list h3 a",
        ),
    ],
)
def test_extract_search_urls_supports_search_providers(html, selector):
    assert _extract_search_urls(html, selector, 10) == [
        f"https://example.com/{'duck' if 'Duck' in html else 'bing' if 'Bing' in html else 'so'}"
    ]


def test_merge_urls_deduplicates_and_filters_search_navigation():
    urls = ["https://example.com/one"]

    _merge_urls(
        urls,
        [
            "https://image.so.com/i?q=test",
            "https://example.com/one",
            "https://example.com/two",
        ],
        10,
    )

    assert urls == ["https://example.com/one", "https://example.com/two"]


def test_search_redirect_url_extracts_known_provider_script_redirect():
    html = (
        '<script>window.location.replace("https://news.example.com/article")</script>'
    )

    assert _search_redirect_url("https://www.so.com/link?m=token", html) == (
        "https://news.example.com/article"
    )
    assert _search_redirect_url("https://unknown.example/link", html) is None


@pytest.mark.asyncio
async def test_driver_event_research_uses_theme_and_stock_queries():
    service = WebResearchService()
    service.search = AsyncMock(return_value=[])

    assert await service.research_driver_events("机器人", ["拓斯达", "埃斯顿"]) == []

    queries = [call.args[0] for call in service.search.await_args_list]
    assert any("机器人" in query and "政策" in query for query in queries)
    assert any("拓斯达" in query for query in queries)


@pytest.mark.asyncio
async def test_search_uses_injected_anti_scraping_middleware():
    response = MagicMock()
    response.text = ""
    response.raise_for_status.return_value = None
    middleware = MagicMock()
    middleware.get = AsyncMock(return_value=response)
    service = WebResearchService(middleware=middleware)

    assert await service.search("机器人") == []

    assert middleware.get.await_count == 3


@pytest.mark.asyncio
async def test_search_continues_with_other_providers_when_one_fails():
    so_response = MagicMock()
    so_response.text = (
        '<li class="res-list"><h3><a href="https://example.com/so">360</a></h3></li>'
    )
    so_response.raise_for_status.return_value = None
    bing_response = MagicMock()
    bing_response.text = ""
    bing_response.raise_for_status.return_value = None
    middleware = MagicMock()
    middleware.get = AsyncMock(
        side_effect=[httpx.ReadTimeout("timeout"), so_response, bing_response]
    )
    service = WebResearchService(middleware=middleware)

    urls = await service.search("机器人")

    assert urls == ["https://example.com/so"]
    assert service.failed_sources == {"DuckDuckGo"}
