"""本地产​​业链构建器。

基于已有题材成分股生成可追溯的三层结构，不依赖外部产业链接口。
"""

from typing import Any

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.industry_chain import IndustryChain
from app.models.stock import Stock
from app.models.theme import Theme
from app.models.theme_stock import ThemeStock
from app.scrapers.base import BaseScraper

logger = get_logger(__name__)

LEVEL_DEFINITIONS = (
    ("upstream", "基础支撑", "基础资源、技术与配套环节"),
    ("midstream", "核心环节", "题材核心产品、制造与集成环节"),
    ("downstream", "应用与服务", "下游应用、销售与服务环节"),
)


def _split_constituents(
    constituents: list[tuple[int, str]],
) -> list[list[tuple[int, str]]]:
    """按原始稳定顺序将成分股均衡分配到三层。"""
    count = len(constituents)
    if count == 1:
        return [[], constituents, []]
    if count == 2:
        return [[constituents[0]], [], [constituents[1]]]

    base_size, remainder = divmod(count, 3)
    sizes = [base_size + (1 if index < remainder else 0) for index in range(3)]
    groups: list[list[tuple[int, str]]] = []
    offset = 0
    for size in sizes:
        groups.append(constituents[offset : offset + size])
        offset += size
    return groups


def build_chain_groups(
    theme_name: str,
    constituents: list[tuple[int, str]],
) -> list[dict[str, Any]]:
    """根据题材成分股生成三层产业链数据。"""
    stock_groups = _split_constituents(constituents)
    chains: list[dict[str, Any]] = []

    for sort_order, ((level, suffix, summary), stocks) in enumerate(
        zip(LEVEL_DEFINITIONS, stock_groups, strict=True)
    ):
        company_names = list(dict.fromkeys(name for _, name in stocks if name))[:5]
        chains.append(
            {
                "level": level,
                "name": f"{theme_name}{suffix}",
                "description": f"{summary}（基于现有成分股结构推导）",
                "representative_companies": company_names,
                "sort_order": sort_order,
                "stock_ids": [stock_id for stock_id, _ in stocks],
            }
        )

    return chains


class LocalChainBuilder(BaseScraper):
    """根据本地题材成分股构建产业链。"""

    source_name = "local_chain"

    def parse(self, html: str) -> list[dict[str, Any]]:
        """本地构建器不解析网页。"""
        return []

    async def save(self, data: list[dict[str, Any]]) -> int:
        """构建过程在同一事务中直接保存。"""
        return 0

    async def run(
        self, url: str = "", params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """为全部有效题材幂等构建三层产业链。"""
        del url, params
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(
                        Theme.id,
                        Theme.name,
                        ThemeStock.stock_id,
                        Stock.name,
                    )
                    .join(ThemeStock, ThemeStock.theme_id == Theme.id)
                    .join(Stock, Stock.id == ThemeStock.stock_id)
                    .where(Theme.deleted_at.is_(None))
                    .order_by(Theme.id, ThemeStock.sort_order, ThemeStock.stock_id)
                )
            ).all()

            themes: dict[int, dict[str, Any]] = {}
            for theme_id, theme_name, stock_id, stock_name in rows:
                theme = themes.setdefault(
                    theme_id,
                    {"name": theme_name, "constituents": []},
                )
                theme["constituents"].append((stock_id, stock_name))

            existing_chains = (
                await session.execute(select(IndustryChain))
            ).scalars().all()
            existing_map = {
                (chain.theme_id, chain.level): chain for chain in existing_chains
            }

            output: list[dict[str, Any]] = []
            for theme_id, theme_data in themes.items():
                groups = build_chain_groups(
                    theme_data["name"], theme_data["constituents"]
                )
                for group in groups:
                    stock_ids = group.pop("stock_ids")
                    chain = existing_map.get((theme_id, group["level"]))
                    if chain is None:
                        chain = IndustryChain(theme_id=theme_id, **group)
                        session.add(chain)
                    else:
                        chain.name = group["name"]
                        chain.description = group["description"]
                        chain.representative_companies = group[
                            "representative_companies"
                        ]
                        chain.sort_order = group["sort_order"]

                    if stock_ids:
                        await session.execute(
                            ThemeStock.__table__.update()
                            .where(
                                ThemeStock.theme_id == theme_id,
                                ThemeStock.stock_id.in_(stock_ids),
                            )
                            .values(chain_level=group["level"])
                        )
                    output.append({"theme_id": theme_id, **group})

            await session.commit()

        logger.info(
            "[%s] 已为 %s 个题材生成 %s 个产业链环节",
            self.source_name,
            len(themes),
            len(output),
        )
        return output, len(output)
