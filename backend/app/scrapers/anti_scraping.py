"""反爬虫中间件

提供 User-Agent 轮换、请求间隔随机化、自动重试和代理支持。
"""

import asyncio
import random
import time
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# 50+ 真实 User-Agent 字符串
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.5",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Brave/120",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

# 需要重试的 HTTP 状态码
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class UserAgentRotator:
    """User-Agent 轮换器"""

    def __init__(self, user_agents: list[str] | None = None):
        self.user_agents = user_agents or USER_AGENTS

    def get_random_ua(self) -> str:
        """获取随机 User-Agent"""
        return random.choice(self.user_agents)


class AntiScrapingMiddleware:
    """反爬虫中间件

    封装 httpx.AsyncClient，提供 UA 轮换、请求间隔、自动重试和代理支持。
    """

    def __init__(
        self,
        proxy_url: str | None = None,
        min_interval: float = 1.0,
        max_interval: float = 3.0,
        max_retries: int = 3,
    ):
        self.ua_rotator = UserAgentRotator()
        self.proxy_url = proxy_url
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.max_retries = max_retries
        self._last_request_time: float = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 httpx 客户端"""
        if self._client is None or self._client.is_closed:
            # 构建客户端参数
            client_kwargs: dict[str, Any] = {
                "timeout": 30.0,
                "follow_redirects": True,
                "limits": httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                ),
            }
            # 如果配置了代理，添加代理参数
            if self.proxy_url:
                client_kwargs["proxy"] = self.proxy_url

            self._client = httpx.AsyncClient(**client_kwargs)
        return self._client

    async def _wait_for_interval(self) -> None:
        """等待请求间隔"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        interval = random.uniform(self.min_interval, self.max_interval)
        if elapsed < interval:
            await asyncio.sleep(interval - elapsed)
        self._last_request_time = time.monotonic()

    async def request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """发送 HTTP 请求，带反爬虫策略

        Args:
            method: HTTP 方法
            url: 请求 URL
            **kwargs: 传递给 httpx 的其他参数

        Returns:
            httpx.Response

        Raises:
            httpx.HTTPStatusError: 请求失败且重试耗尽
        """
        client = await self._get_client()

        # 设置随机 User-Agent
        headers = kwargs.pop("headers", {})
        headers["User-Agent"] = self.ua_rotator.get_random_ua()
        kwargs["headers"] = headers

        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            # 等待请求间隔（首次请求不等待）
            if attempt > 0:
                await self._wait_for_interval()

            try:
                response = await client.request(method, url, **kwargs)

                # 如果状态码可重试，抛出异常触发重试
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        backoff = (2**attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"请求返回 {response.status_code}，"
                            f"将在 {backoff:.1f}s 后重试 ({attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        response.raise_for_status()

                return response

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    backoff = (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"请求超时，将在 {backoff:.1f}s 后重试 ({attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise

            except httpx.ConnectError as e:
                last_exception = e
                if attempt < self.max_retries:
                    backoff = (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"连接失败，将在 {backoff:.1f}s 后重试 ({attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise

        # 不应到达这里，但作为安全网
        if last_exception:
            raise last_exception
        raise RuntimeError("请求失败：重试次数耗尽")

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """发送 GET 请求"""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """发送 POST 请求"""
        return await self.request("POST", url, **kwargs)

    async def close(self) -> None:
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
