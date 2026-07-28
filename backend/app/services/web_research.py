"""公开网页搜索与受限正文抓取。"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.scrapers.anti_scraping import AntiScrapingMiddleware

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
)


@dataclass(slots=True)
class ResearchSource:
    title: str
    url: str
    text: str
    publisher: str | None = None
    published_at: datetime | None = None


def _is_public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return bool(address.is_global)


async def validate_public_url(url: str) -> str:
    """校验 URL 及其 DNS 结果，避免抓取内网和本机资源。"""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("仅允许访问公网 HTTP/HTTPS 地址")
    if parsed.username or parsed.password:
        raise ValueError("仅允许访问公网 HTTP/HTTPS 地址")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("仅允许访问公网地址")
    try:
        if not _is_public_ip(hostname):
            raise ValueError("仅允许访问公网地址")
        return url
    except ValueError as exc:
        if "公网" in str(exc):
            raise

    loop = asyncio.get_running_loop()
    try:
        records = await loop.getaddrinfo(
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError("公网地址无法解析") from exc
    addresses = {record[4][0] for record in records}
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise ValueError("仅允许访问公网地址")
    return url


def extract_page_text(html: str, max_chars: int = 24_000) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        tag.decompose()
    content = soup.find("article") or soup.find("main") or soup.body or soup
    lines = [" ".join(line.split()) for line in content.get_text("\n").splitlines()]
    text = "\n".join(line for line in lines if len(line) >= 2)
    return title[:300], text[:max_chars]


def _search_result_url(href: str) -> str | None:
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in (parsed.hostname or ""):
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        return unquote(target) if target else None
    return href if parsed.scheme in {"http", "https"} else None


def _extract_search_urls(html: str, selector: str, limit: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for anchor in soup.select(selector):
        url = _search_result_url(anchor.get("href", ""))
        if url and url not in urls:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def _merge_urls(target: list[str], candidates: list[str], limit: int) -> None:
    blocked_hosts = {"image.so.com", "image.baidu.com", "cn.bing.com"}
    for url in candidates:
        if urlparse(url).hostname in blocked_hosts or url in target:
            continue
        target.append(url)
        if len(target) >= limit:
            break


def _search_redirect_url(page_url: str, html: str) -> str | None:
    if urlparse(page_url).hostname not in {"www.so.com", "so.com"}:
        return None
    match = re.search(r'window\.location\.replace\(["\']([^"\']+)', html)
    if match:
        return match.group(1)
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.select_one('meta[http-equiv="refresh" i]')
    if not meta:
        return None
    content = meta.get("content", "")
    match = re.search(r"url=['\"]?([^'\";]+)", content, flags=re.I)
    return match.group(1) if match else None


class WebResearchService:
    def __init__(
        self,
        timeout_seconds: int = 12,
        max_sources: int = 6,
        middleware: AntiScrapingMiddleware | None = None,
        research_budget_seconds: float = 150.0,
        fetch_concurrency: int = 4,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_sources = max_sources
        self.middleware = middleware or AntiScrapingMiddleware()
        # 整轮检索+抓取的硬预算：query 多、上游慢时按预算截断，
        # 返回已拿到的部分结果，避免详情页刷新无限挂起
        self.research_budget_seconds = research_budget_seconds
        self.fetch_concurrency = max(1, fetch_concurrency)
        self.failed_sources: set[str] = set()

    def reset_failures(self) -> None:
        self.failed_sources.clear()

    async def search(self, query: str, limit: int = 10) -> list[str]:
        urls: list[str] = []
        providers = (
            (
                "DuckDuckGo",
                "https://html.duckduckgo.com/html/",
                {"q": query},
                "a.result__a",
            ),
            (
                "360搜索",
                "https://www.so.com/s",
                {"q": query, "pn": 1},
                ".res-list h3 a",
            ),
            (
                "Bing",
                "https://cn.bing.com/search",
                {"q": query, "count": limit},
                "li.b_algo h2 a",
            ),
        )
        for name, url, params, selector in providers:
            if len(urls) >= limit:
                break
            try:
                response = await self.middleware.get(
                    url,
                    params=params,
                    follow_redirects=False,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
            except httpx.HTTPError:
                self.failed_sources.add(name)
                continue
            _merge_urls(
                urls,
                _extract_search_urls(response.text, selector, limit),
                limit,
            )
        return urls

    async def fetch(self, url: str) -> ResearchSource | None:
        await validate_public_url(url)
        response = await self.middleware.get(
            url,
            timeout=self.timeout_seconds,
            follow_redirects=False,
        )
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                return None
            redirected = str(response.url.join(location))
            await validate_public_url(redirected)
            response = await self.middleware.get(
                redirected,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            )
            url = redirected
        elif redirected := _search_redirect_url(url, response.text):
            await validate_public_url(redirected)
            response = await self.middleware.get(
                redirected,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            )
            url = str(response.url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower():
            return None
        title, text = extract_page_text(response.text)
        if len(text) < 120:
            return None
        return ResearchSource(
            title=title or urlparse(url).hostname or url,
            url=url,
            text=text,
            publisher=urlparse(url).hostname,
        )

    async def research_theme(self, theme_name: str) -> list[ResearchSource]:
        return await self.research_profile(theme_name)

    async def research_concept_graph(
        self,
        theme_name: str,
        stock_names: list[str] | None = None,
    ) -> list[ResearchSource]:
        """概念树专用检索：偏产业链结构与龙头业务，避免只搜到泛资讯。"""
        queries = [
            f"{theme_name} 产业链 上中下游 结构",
            f"{theme_name} 核心技术 设备 材料 应用",
            f"{theme_name} 龙头公司 竞争格局",
        ]
        for stock_name in (stock_names or [])[:5]:
            queries.append(f"{theme_name} {stock_name} 产品 业务")
        return await self._research_queries(queries)

    async def _research_queries(self, queries: list[str]) -> list[ResearchSource]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.research_budget_seconds
        # 搜索阶段最多占用约一半预算，给正文抓取留足时间
        search_deadline = loop.time() + self.research_budget_seconds * 0.5

        async def _search_one(query: str) -> list[str]:
            remaining = search_deadline - loop.time()
            if remaining <= 0:
                return []
            try:
                return await asyncio.wait_for(self.search(query), timeout=remaining)
            except asyncio.TimeoutError:
                return []
            except httpx.HTTPError:
                return []

        # 多 query 并发检索；节流锁会序列化请求发起，慢 query 不再阻塞整体
        search_results = await asyncio.gather(
            *(_search_one(query) for query in queries)
        )
        candidates: list[str] = []
        for urls in search_results:
            for url in urls:
                if url not in candidates:
                    candidates.append(url)

        semaphore = asyncio.Semaphore(self.fetch_concurrency)

        async def _fetch_one(url: str) -> ResearchSource | None:
            async with semaphore:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return None
                try:
                    return await asyncio.wait_for(self.fetch(url), timeout=remaining)
                except asyncio.TimeoutError:
                    self.failed_sources.add(urlparse(url).hostname or url)
                    return None
                except (httpx.HTTPError, ValueError):
                    self.failed_sources.add(urlparse(url).hostname or url)
                    return None

        # 抓取阶段：限流并发，凑够 max_sources 或预算耗尽即停（保留部分结果）
        sources: list[ResearchSource] = []
        pending = list(candidates)
        batch_size = self.fetch_concurrency * 2
        while pending and len(sources) < self.max_sources:
            if deadline - loop.time() <= 0:
                break
            batch, pending = pending[:batch_size], pending[batch_size:]
            for source in await asyncio.gather(*(_fetch_one(u) for u in batch)):
                if source is not None:
                    sources.append(source)
                    if len(sources) >= self.max_sources:
                        break
        return sources

    async def research_profile(self, theme_name: str) -> list[ResearchSource]:
        queries = [
            f"{theme_name} 概念 定义 产业链 应用",
            f"{theme_name} 核心逻辑 催化因素 风险",
        ]
        return await self._research_queries(queries)

    async def research_driver_events(
        self, theme_name: str, stock_names: list[str]
    ) -> list[ResearchSource]:
        queries = [
            f"{theme_name} 政策 订单 发布 突破 涨价 扩产 业绩",
            *[f"{theme_name} {stock_name} 最新消息" for stock_name in stock_names[:10]],
        ]
        return await self._research_queries(queries)
