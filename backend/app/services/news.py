"""真实财经新闻来源及聚合服务。"""

import asyncio
import math
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.core.logging import get_logger
from app.repositories.news import NewsRepository
from app.schemas.news import NewsRefreshResponse, NewsSourceResult
from app.scrapers.anti_scraping import AntiScrapingMiddleware

logger = get_logger(__name__)
MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")


def classify_news(text: str) -> str:
    mappings = {
        "科技": ("人工智能", "AI", "芯片", "算力", "机器人", "软件", "半导体"),
        "能源": ("新能源", "光伏", "储能", "电池", "石油", "天然气", "煤炭"),
        "政策": ("政策", "国务院", "发改委", "央行", "证监会", "监管"),
        "公司": ("公司", "财报", "业绩", "股东", "收购", "上市"),
        "市场": ("A股", "港股", "美股", "涨停", "指数", "大盘", "交易"),
    }
    for category, keywords in mappings.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "财经"


def normalize_url(url: str) -> str:
    return f"https://{url[7:]}" if url.startswith("http://") else url


def _normalized_title(title: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", title.lower())


def calculate_heat_scores(
    articles: list[dict[str, Any]], datetime_now: datetime | None = None, **kwargs: Any
) -> None:
    """按时效、来源指标和多源报道计算 0-100 综合热度。"""
    now = kwargs.get("now") or datetime_now or datetime.now(MARKET_TIMEZONE)
    normalized_titles = [
        _normalized_title(str(item.get("title", ""))) for item in articles
    ]
    source_counts = []
    for index, title in enumerate(normalized_titles):
        matching_sources = {
            str(other.get("source", ""))
            for other_index, other in enumerate(articles)
            if other_index != index
            and title
            and SequenceMatcher(None, title, normalized_titles[other_index]).ratio()
            >= 0.55
        }
        source_counts.append(len(matching_sources))

    for article, related_source_count in zip(articles, source_counts, strict=True):
        published_at = article.get("published_at")
        age_hours = (
            max(0.0, (now - published_at).total_seconds() / 3600)
            if published_at
            else 24
        )
        recency_score = max(5.0, 55.0 - min(age_hours, 24.0) * 2.1)
        source_heat = max(0, int(article.get("source_heat") or 0))
        source_score = min(20.0, math.log1p(source_heat) * 7.0)
        multi_source_score = min(20.0, related_source_count * 10.0)
        signal_score = (
            5.0
            if any(
                keyword in str(article.get("title", ""))
                for keyword in ("突发", "涨停", "大涨", "大跌", "政策", "发布", "公告")
            )
            else 0.0
        )
        article["heat_score"] = min(
            100, round(recency_score + source_score + multi_source_score + signal_score)
        )


class NewsSource(Protocol):
    name: str

    async def fetch(self) -> list[dict[str, Any]]: ...


class SinaNewsSource:
    name = "新浪财经"
    url = "https://feed.mix.sina.com.cn/api/roll/get"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )

    @staticmethod
    def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles = []
        for item in payload.get("result", {}).get("data", []):
            title = str(item.get("title", "")).strip()
            url = normalize_url(str(item.get("url", "")).strip())
            if not title or not url:
                continue
            timestamp = int(item.get("ctime") or item.get("intime") or 0)
            articles.append(
                {
                    "source": "新浪财经",
                    "category": classify_news(f"{title} {item.get('keywords', '')}"),
                    "title": title[:500],
                    "summary": str(item.get("summary", "")).strip() or None,
                    "url": url,
                    "published_at": datetime.fromtimestamp(
                        timestamp, tz=MARKET_TIMEZONE
                    ),
                    "crawled_at": crawled_at,
                    "source_heat": 0,
                }
            )
        return articles

    async def fetch(self) -> list[dict[str, Any]]:
        response = await self.middleware.get(
            self.url, params={"pageid": 153, "lid": 2516, "num": 40, "page": 1}
        )
        response.raise_for_status()
        return self.parse(response.json())


class EastMoneyNewsSource:
    name = "东方财富"
    url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )

    @staticmethod
    def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles = []
        for item in payload.get("data", {}).get("list", []):
            title = str(item.get("title", "")).strip()
            url = normalize_url(
                str(item.get("uniqueUrl") or item.get("url") or "").strip()
            )
            if not title or not url:
                continue
            published_at = datetime.strptime(
                item["showTime"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=MARKET_TIMEZONE)
            summary = str(item.get("summary", "")).strip()
            articles.append(
                {
                    "source": "东方财富",
                    "category": classify_news(f"{title} {summary}"),
                    "title": title[:500],
                    "summary": summary or None,
                    "url": url,
                    "published_at": published_at,
                    "crawled_at": crawled_at,
                    "source_heat": 0,
                }
            )
        return articles

    async def fetch(self) -> list[dict[str, Any]]:
        response = await self.middleware.get(
            self.url,
            params={
                "client": "web",
                "biz": "web_news_col",
                "column": "745",
                "order": "1",
                "needInteractData": "0",
                "page_index": 1,
                "page_size": 40,
                "req_trace": uuid4().hex,
            },
        )
        response.raise_for_status()
        return self.parse(response.json())


class WallStreetCNNewsSource:
    name = "华尔街见闻"
    url = "https://api-one.wallstcn.com/apiv1/content/lives"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )

    @staticmethod
    def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles = []
        for item in payload.get("data", {}).get("items", []):
            summary = str(item.get("content_text", "")).strip()
            title = str(item.get("title", "")).strip() or summary[:120]
            url = normalize_url(str(item.get("uri", "")).strip())
            timestamp = int(item.get("display_time") or 0)
            if not title or not url or not timestamp:
                continue
            articles.append(
                {
                    "source": "华尔街见闻",
                    "category": classify_news(f"{title} {summary}"),
                    "title": title[:500],
                    "summary": summary[:1000] or None,
                    "url": url,
                    "published_at": datetime.fromtimestamp(
                        timestamp, tz=MARKET_TIMEZONE
                    ),
                    "crawled_at": crawled_at,
                    "source_heat": int(item.get("score") or 0)
                    + int(item.get("comment_count") or 0),
                }
            )
        return articles

    async def fetch(self) -> list[dict[str, Any]]:
        response = await self.middleware.get(
            self.url,
            params={"channel": "global-channel", "client": "pc", "limit": 40},
        )
        response.raise_for_status()
        return self.parse(response.json())


class TongHuaShunNewsSource:
    name = "同花顺"
    url = "https://news.10jqka.com.cn/tapp/news/push/stock/"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )

    @staticmethod
    def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles = []
        for item in payload.get("data", {}).get("list", []):
            title = str(item.get("title", "")).strip()
            summary = str(item.get("digest") or item.get("short") or "").strip()
            url = normalize_url(str(item.get("url", "")).strip())
            timestamp = int(item.get("ctime") or 0)
            if not title or not url or not timestamp:
                continue
            articles.append(
                {
                    "source": "同花顺",
                    "category": classify_news(
                        f"{title} {summary} {item.get('tag', '')}"
                    ),
                    "title": title[:500],
                    "summary": summary[:1000] or None,
                    "url": url,
                    "published_at": datetime.fromtimestamp(
                        timestamp, tz=MARKET_TIMEZONE
                    ),
                    "crawled_at": crawled_at,
                    "source_heat": int(item.get("import") or 0),
                }
            )
        return articles

    async def fetch(self) -> list[dict[str, Any]]:
        response = await self.middleware.get(
            self.url,
            params={"page": 1, "tag": "", "track": "website", "pagesize": 40},
        )
        response.raise_for_status()
        return self.parse(response.json())


class NewsService:
    def __init__(
        self, repository: NewsRepository, sources: list[NewsSource] | None = None
    ):
        self.repository = repository
        if sources is not None:
            self.sources = sources
        else:
            from app.core.config import get_settings
            from app.services.news_sources_extra import build_extra_sources

            self.sources = [
                SinaNewsSource(),
                EastMoneyNewsSource(),
                WallStreetCNNewsSource(),
                TongHuaShunNewsSource(),
                *build_extra_sources(get_settings().XUEQIU_COOKIE),
            ]

    @property
    def available_source_names(self) -> list[str]:
        return [source.name for source in self.sources]

    def select_sources(self, source_names: set[str] | None) -> list[NewsSource]:
        if source_names is None:
            return self.sources
        unknown_names = source_names.difference(self.available_source_names)
        if unknown_names:
            raise ValueError(f"未知新闻渠道：{'、'.join(sorted(unknown_names))}")
        return [source for source in self.sources if source.name in source_names]

    async def refresh(
        self, source_names: set[str] | None = None
    ) -> NewsRefreshResponse:
        selected_sources = self.select_sources(source_names)
        results = await asyncio.gather(
            *(source.fetch() for source in selected_sources), return_exceptions=True
        )
        all_articles: list[dict[str, Any]] = []
        source_results = []
        for source, result in zip(selected_sources, results, strict=True):
            if isinstance(result, BaseException):
                logger.warning(
                    "news_source_failed", source=source.name, error=str(result)
                )
                source_results.append(
                    NewsSourceResult(
                        source=source.name, success=False, error=str(result)
                    )
                )
                continue
            if not result:
                error = "未抓取到有效新闻，来源接口可能不可用或页面结构已变更"
                logger.warning("news_source_empty", source=source.name)
                source_results.append(
                    NewsSourceResult(source=source.name, success=False, error=error)
                )
                continue
            all_articles.extend(result)
            source_results.append(
                NewsSourceResult(
                    source=source.name, success=True, fetched_count=len(result)
                )
            )

        if all_articles:
            calculate_heat_scores(all_articles)
        inserted_count = (
            await self.repository.upsert_many(all_articles) if all_articles else 0
        )
        return NewsRefreshResponse(
            success=bool(all_articles),
            fetched_count=len(all_articles),
            inserted_count=inserted_count,
            refreshed_at=datetime.now(UTC),
            sources=source_results,
        )
