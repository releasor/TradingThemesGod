"""新闻来源解析测试。"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.news import (
    EastMoneyNewsSource,
    SinaNewsSource,
    TongHuaShunNewsSource,
    WallStreetCNNewsSource,
)


def test_parse_sina_news_keeps_original_url_and_time():
    payload = {
        "result": {
            "data": [
                {
                    "title": "人工智能产业最新进展",
                    "url": "https://finance.sina.com.cn/test.shtml",
                    "ctime": "1784168400",
                    "keywords": "人工智能,产业",
                }
            ]
        }
    }

    item = SinaNewsSource.parse(payload)[0]

    assert item["source"] == "新浪财经"
    assert item["url"] == "https://finance.sina.com.cn/test.shtml"
    assert item["published_at"] == datetime.fromtimestamp(
        1784168400, tz=ZoneInfo("Asia/Shanghai")
    )
    assert item["category"] == "科技"
    assert item["source_heat"] == 0


def test_parse_eastmoney_news_uses_unique_original_url():
    payload = {
        "data": {
            "list": [
                {
                    "title": "新能源行业迎来政策利好",
                    "summary": "行业最新消息",
                    "uniqueUrl": "http://finance.eastmoney.com/a/1.html",
                    "url": "http://stock.eastmoney.com/news/1.html",
                    "showTime": "2026-07-16 08:45:00",
                    "mediaName": "东方财富网",
                }
            ]
        }
    }

    item = EastMoneyNewsSource.parse(payload)[0]

    assert item["url"] == "https://finance.eastmoney.com/a/1.html"
    assert item["summary"] == "行业最新消息"
    assert item["category"] == "能源"
    assert item["published_at"].tzinfo is not None
    assert item["source_heat"] == 0


def test_parse_wallstreetcn_news_keeps_live_link_and_source_heat():
    payload = {
        "data": {
            "items": [
                {
                    "id": 3134763,
                    "title": "半导体行业出现最新进展",
                    "content_text": "行业快讯摘要",
                    "display_time": 1784169698,
                    "uri": "https://wallstreetcn.com/livenews/3134763",
                    "score": 4,
                    "comment_count": 12,
                }
            ]
        }
    }

    item = WallStreetCNNewsSource.parse(payload)[0]

    assert item["source"] == "华尔街见闻"
    assert item["url"] == "https://wallstreetcn.com/livenews/3134763"
    assert item["summary"] == "行业快讯摘要"
    assert item["source_heat"] == 16
    assert item["published_at"].tzinfo is not None


def test_parse_tonghuashun_news_uses_public_article_url_and_importance():
    payload = {
        "data": {
            "list": [
                {
                    "title": "人工智能板块快速走强",
                    "digest": "多只相关股票上涨",
                    "url": "https://news.10jqka.com.cn/20260716/c678216312.shtml",
                    "ctime": "1784169589",
                    "import": "3",
                    "tag": "异动,A股",
                }
            ]
        }
    }

    item = TongHuaShunNewsSource.parse(payload)[0]

    assert item["source"] == "同花顺"
    assert item["category"] == "科技"
    assert item["source_heat"] == 3
    assert item["url"].startswith("https://news.10jqka.com.cn/")
