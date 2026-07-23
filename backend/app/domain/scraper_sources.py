"""爬虫数据源目录与展示元数据。"""

from dataclasses import dataclass

from app.scrapers.registry import scraper_registry


@dataclass(frozen=True)
class ScraperSourceMeta:
    """数据源说明。"""

    id: str
    label: str
    description: str
    dashboard_selectable: bool
    is_default: bool = False


SCRAPER_SOURCE_CATALOG: tuple[ScraperSourceMeta, ...] = (
    ScraperSourceMeta(
        id="eastmoney",
        label="东方财富",
        description="题材列表、涨跌幅、成分股与市场快照（看板推荐）",
        dashboard_selectable=True,
        is_default=True,
    ),
    ScraperSourceMeta(
        id="akshare",
        label="AKShare",
        description="A 股实时行情、涨跌幅与市值数据",
        dashboard_selectable=True,
    ),
    ScraperSourceMeta(
        id="ths",
        label="同花顺",
        description="单题材产业链结构（需在题材详情中使用）",
        dashboard_selectable=False,
    ),
    ScraperSourceMeta(
        id="sina",
        label="新浪财经",
        description="单只股票新闻与事件（需指定股票代码）",
        dashboard_selectable=False,
    ),
)


def list_registered_scraper_sources(
    *, dashboard_only: bool = False
) -> list[ScraperSourceMeta]:
    """返回已注册且存在于目录中的数据源。"""
    registered = set(scraper_registry.list_sources())
    sources = [item for item in SCRAPER_SOURCE_CATALOG if item.id in registered]
    if dashboard_only:
        return [item for item in sources if item.dashboard_selectable]
    return sources


def get_default_dashboard_source() -> str:
    dashboard_sources = list_registered_scraper_sources(dashboard_only=True)
    for item in dashboard_sources:
        if item.is_default:
            return item.id
    return dashboard_sources[0].id if dashboard_sources else "eastmoney"
