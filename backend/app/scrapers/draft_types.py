"""全量爬虫草稿类型：采集与落库分离。"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class FullScrapeDraft:
    """全量爬取草稿：先内存采集，胜出后再 commit 落库。"""

    source: str
    trade_date: date | None
    themes: list[dict[str, Any]]
    stocks_by_code: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
