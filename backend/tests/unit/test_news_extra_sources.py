"""扩展新闻来源测试。"""

from app.services.news_sources_extra import (
    ClsNewsSource,
    HtmlNewsSource,
    StcnNewsSource,
    YiCaiNewsSource,
    build_extra_sources,
)


def test_html_source_parses_scoped_links_dates_and_absolute_urls():
    source = HtmlNewsSource(
        name="国家统计局",
        url="https://www.stats.gov.cn/sj/zxfb/",
        link_selector=".list-content li a[href]",
    )
    html = """
    <div class="nav"><a href="/about">网站介绍</a></div>
    <div class="list-content"><ul><li>
      <a href="./202607/t20260716_1.html">2026年上半年经济数据发布</a>
      <span>2026-07-16</span>
    </li></ul></div>
    """

    item = source.parse(html)[0]

    assert item["source"] == "国家统计局"
    assert item["url"] == "https://www.stats.gov.cn/sj/zxfb/202607/t20260716_1.html"
    assert item["published_at"].year == 2026


def test_yicai_source_parses_public_api_payload():
    payload = [
        {
            "NewsTitle": "脑机接口板块盘中上涨",
            "NewsNotes": "多只相关股票跟涨。",
            "CreateDate": "2026-07-16T11:02:48",
            "url": "/news/103277545.html",
            "CommentCount": 5,
            "NewsHot": 3,
        }
    ]

    item = YiCaiNewsSource.parse(payload)[0]

    assert item["source"] == "第一财经"
    assert item["url"] == "https://www.yicai.com/news/103277545.html"
    assert item["source_heat"] == 8


def test_cls_source_parses_cache_payload():
    payload = {
        "errno": 0,
        "data": {
            "roll_data": [
                {
                    "id": 2428105,
                    "title": "半导体设备最新消息",
                    "brief": "财联社电，产业链出现新进展。",
                    "ctime": 1784171481,
                    "comment_num": 7,
                }
            ]
        },
    }

    item = ClsNewsSource.parse(payload)[0]

    assert item["source"] == "财联社"
    assert item["url"] == "https://www.cls.cn/detail/2428105"
    assert item["source_heat"] == 7


def test_stcn_source_parses_ajax_payload():
    payload = {
        "data": [
            {
                "id": "4022559",
                "title": "A股市场盘中快讯",
                "url": "/article/detail/4022559.html",
                "time": 1784170968000,
            }
        ]
    }

    item = StcnNewsSource.parse(payload)[0]

    assert item["source"] == "证券时报"
    assert item["url"] == "https://www.stcn.com/article/detail/4022559.html"
    assert item["published_at"].year == 2026


def test_extra_source_registry_contains_all_requested_channels():
    names = {source.name for source in build_extra_sources(xueqiu_cookie="")}

    assert {
        "财联社",
        "证券时报",
        "上海证券报",
        "中国证券报",
        "第一财经",
        "央视财经",
        "巨潮资讯",
        "上交所",
        "深交所",
        "北交所",
        "证监会",
        "中国人民银行",
        "国家统计局",
        "国家发改委",
        "雪球",
    } <= names
