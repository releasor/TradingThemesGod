"""扩展财经新闻来源适配器。"""

import re
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.services.news import MARKET_TIMEZONE, classify_news

DATE_PATTERN = re.compile(
    r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})(?:日)?"
    r"(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?"
)
URL_DATE_PATTERN = re.compile(r"/(20\d{2})/(\d{2})/(\d{2})/")


def _parse_datetime(text: str, url: str = "") -> datetime | None:
    match = DATE_PATTERN.search(text)
    if not match:
        now = datetime.now(MARKET_TIMEZONE)
        relative = re.search(r"(\d+)\s*(分钟|小时|天)前", text)
        if relative:
            value = int(relative.group(1))
            delta = {
                "分钟": timedelta(minutes=value),
                "小时": timedelta(hours=value),
                "天": timedelta(days=value),
            }[relative.group(2)]
            return now - delta
        url_date = URL_DATE_PATTERN.search(url)
        if url_date:
            return datetime(*map(int, url_date.groups()), tzinfo=MARKET_TIMEZONE)
        return None
    year, month, day, hour, minute, second = match.groups()
    try:
        return datetime(
            int(year),
            int(month),
            int(day),
            int(hour or 0),
            int(minute or 0),
            int(second or 0),
            tzinfo=MARKET_TIMEZONE,
        )
    except ValueError:
        return None


class HtmlNewsSource:
    """从限定列表区域提取带日期的新闻链接。"""

    def __init__(
        self,
        name: str,
        url: str,
        link_selector: str,
        *,
        middleware: AntiScrapingMiddleware | None = None,
        headers: dict[str, str] | None = None,
        limit: int = 40,
    ):
        self.name = name
        self.url = url
        self.link_selector = link_selector
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )
        self.headers = headers or {}
        self.limit = limit

    def parse(self, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for link in soup.select(self.link_selector):
            if not isinstance(link, Tag):
                continue
            title = " ".join(link.get_text(" ", strip=True).split())
            href = str(link.get("href") or "").strip()
            if not title or href.startswith(("javascript:", "#")):
                continue
            url = urljoin(self.url, href)
            if not url.startswith(("http://", "https://")) or url in seen_urls:
                continue

            container = link.find_parent(["li", "tr", "div", "article"]) or link.parent
            context = container.get_text(" ", strip=True) if container else title
            published_at = _parse_datetime(context, url)
            if published_at is None:
                continue
            seen_urls.add(url)
            articles.append(
                {
                    "source": self.name,
                    "category": classify_news(title),
                    "title": title[:500],
                    "summary": None,
                    "url": url,
                    "published_at": published_at,
                    "crawled_at": crawled_at,
                    "source_heat": 0,
                }
            )
        articles.sort(key=lambda item: item["published_at"], reverse=True)
        return articles[: self.limit]

    async def fetch(self) -> list[dict[str, Any]]:
        response = await self.middleware.get(self.url, headers=self.headers.copy())
        response.raise_for_status()
        return self.parse(response.text)


class YiCaiNewsSource:
    name = "第一财经"
    url = "https://www.yicai.com/api/ajax/getlatest"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )

    @staticmethod
    def parse(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles = []
        for item in payload:
            title = str(item.get("NewsTitle") or "").strip()
            path = str(item.get("url") or "").strip()
            published_at = _parse_datetime(str(item.get("CreateDate") or ""))
            if not title or not path or published_at is None:
                continue
            summary = str(item.get("NewsNotes") or "").strip()
            articles.append(
                {
                    "source": "第一财经",
                    "category": classify_news(f"{title} {summary}"),
                    "title": title[:500],
                    "summary": summary[:1000] or None,
                    "url": urljoin("https://www.yicai.com", path),
                    "published_at": published_at,
                    "crawled_at": crawled_at,
                    "source_heat": int(item.get("CommentCount") or 0)
                    + int(item.get("NewsHot") or 0),
                }
            )
        return articles

    async def fetch(self) -> list[dict[str, Any]]:
        response = await self.middleware.get(
            self.url, params={"page": 1, "pagesize": 40}
        )
        response.raise_for_status()
        return self.parse(response.json())


class ClsNewsSource:
    name = "财联社"
    url = "https://www.cls.cn/api/cache"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )

    @staticmethod
    def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles = []
        for item in payload.get("data", {}).get("roll_data", []):
            title = str(item.get("title") or item.get("brief") or "").strip()
            item_id = item.get("id")
            timestamp = int(item.get("ctime") or 0)
            if not title or not item_id or not timestamp:
                continue
            summary = str(item.get("brief") or "").strip()
            articles.append(
                {
                    "source": "财联社",
                    "category": classify_news(f"{title} {summary}"),
                    "title": title[:500],
                    "summary": summary[:1000] or None,
                    "url": f"https://www.cls.cn/detail/{item_id}",
                    "published_at": datetime.fromtimestamp(
                        timestamp, tz=MARKET_TIMEZONE
                    ),
                    "crawled_at": crawled_at,
                    "source_heat": int(item.get("comment_num") or 0),
                }
            )
        return articles

    async def fetch(self) -> list[dict[str, Any]]:
        response = await self.middleware.get(
            self.url,
            params={"rn": 40, "lastTime": int(time.time()), "name": "telegraph"},
            headers={"Referer": "https://www.cls.cn/telegraph"},
        )
        response.raise_for_status()
        return self.parse(response.json())


class StcnNewsSource:
    name = "证券时报"
    url = "https://www.stcn.com/article/list.html"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )

    @staticmethod
    def parse(payload: dict[str, Any]) -> list[dict[str, Any]]:
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles = []
        for item in payload.get("data", []):
            title = str(item.get("title") or item.get("content") or "").strip()
            path = str(item.get("url") or "").strip()
            raw_time = item.get("time") or item.get("show_time") or item.get("showTime")
            if isinstance(raw_time, (int, float)) or str(raw_time).isdigit():
                timestamp = int(raw_time)
                published_at = datetime.fromtimestamp(
                    timestamp / 1000 if timestamp > 10_000_000_000 else timestamp,
                    tz=MARKET_TIMEZONE,
                )
            else:
                published_at = _parse_datetime(str(raw_time or ""), path)
            if not title or not path or published_at is None:
                continue
            summary = str(item.get("digest") or item.get("content") or "").strip()
            articles.append(
                {
                    "source": "证券时报",
                    "category": classify_news(f"{title} {summary}"),
                    "title": BeautifulSoup(title, "html.parser").get_text(
                        " ", strip=True
                    )[:500],
                    "summary": BeautifulSoup(summary, "html.parser").get_text(
                        " ", strip=True
                    )[:1000]
                    or None,
                    "url": urljoin("https://www.stcn.com", path),
                    "published_at": published_at,
                    "crawled_at": crawled_at,
                    "source_heat": 0,
                }
            )
        return articles

    async def fetch(self) -> list[dict[str, Any]]:
        response = await self.middleware.get(
            self.url,
            params={"type": "kx"},
            headers={
                "Referer": "https://www.stcn.com/article/list/kx.html",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        response.raise_for_status()
        return self.parse(response.json())


class XueQiuNewsSource:
    name = "雪球"
    url = "https://xueqiu.com/statuses/hot/listV2.json"

    def __init__(self, cookie: str, middleware: AntiScrapingMiddleware | None = None):
        self.cookie = cookie.strip()
        self.middleware = middleware or AntiScrapingMiddleware(
            min_interval=0.2, max_interval=0.5
        )

    async def fetch(self) -> list[dict[str, Any]]:
        if not self.cookie:
            raise RuntimeError("未配置 XUEQIU_COOKIE")
        response = await self.middleware.get(
            self.url,
            params={"since_id": -1, "max_id": -1, "size": 20},
            headers={"Cookie": self.cookie, "Referer": "https://xueqiu.com/"},
        )
        response.raise_for_status()
        crawled_at = datetime.now(MARKET_TIMEZONE)
        articles = []
        for row in response.json().get("items", []):
            item = row.get("original_status") or row
            title = str(item.get("title") or item.get("description") or "").strip()
            status_id = item.get("id")
            user_id = (item.get("user") or {}).get("id")
            timestamp = int(item.get("created_at") or 0)
            if not title or not status_id or not user_id or not timestamp:
                continue
            articles.append(
                {
                    "source": self.name,
                    "category": classify_news(title),
                    "title": BeautifulSoup(title, "html.parser").get_text(
                        " ", strip=True
                    )[:500],
                    "summary": None,
                    "url": f"https://xueqiu.com/{user_id}/{status_id}",
                    "published_at": datetime.fromtimestamp(
                        timestamp / 1000, tz=MARKET_TIMEZONE
                    ),
                    "crawled_at": crawled_at,
                    "source_heat": int(item.get("like_count") or 0)
                    + int(item.get("reply_count") or 0),
                }
            )
        return articles


def build_extra_sources(xueqiu_cookie: str = "") -> list[Any]:
    """构建用户要求的扩展来源列表。"""
    html_sources = [
        (
            "上海证券报",
            "https://www.cnstock.com/",
            "a.index_item__GpLlY[href*='/commonDetail/']",
        ),
        (
            "中国证券报",
            "https://www.cs.com.cn/yaowen.html",
            "a[href*='/202'][href$='.html']",
        ),
        ("央视财经", "https://finance.cctv.com/", "a[href*='finance.cctv.com/202']"),
        (
            "巨潮资讯",
            "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch",
            "a[href*='announcement']",
        ),
        (
            "上交所",
            "https://www.sse.com.cn/aboutus/mediacenter/hotandd/",
            "a[href*='.shtml']",
        ),
        ("深交所", "https://www.szse.cn/aboutus/trends/news/", "a[href*='.html']"),
        (
            "北交所",
            "https://www.bse.cn/disclosure/tradingtips.html",
            "#table a[href]",
        ),
        (
            "证监会",
            "https://www.csrc.gov.cn/csrc/c100028/common_list.shtml",
            "#list a[href]",
        ),
        (
            "中国人民银行",
            "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html",
            ".newslist_style a[href]",
        ),
        ("国家统计局", "https://www.stats.gov.cn/sj/zxfb/", ".list-content li a[href]"),
        (
            "国家发改委",
            "https://www.ndrc.gov.cn/xwdt/xwfb/",
            "li a[href*='t20'][href$='.html']",
        ),
    ]
    sources: list[Any] = [ClsNewsSource(), StcnNewsSource()]
    sources.extend(
        HtmlNewsSource(name, url, selector) for name, url, selector in html_sources
    )
    sources.extend([YiCaiNewsSource(), XueQiuNewsSource(xueqiu_cookie)])
    return sources
