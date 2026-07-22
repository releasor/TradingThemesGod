"""知识包幂等导入服务。"""

from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.robotics import NODES, ROOT_SOURCE, STOCK_LINKS
from app.models.concept_node import ConceptNode
from app.models.concept_node_stock import ConceptNodeStock
from app.models.industry_chain import IndustryChain
from app.models.stock import Stock
from app.models.theme import Theme
from app.models.theme_stock import ThemeStock


async def import_robotics_graph(session: AsyncSession, theme_name: str = "人形机器人") -> dict[str, int]:
    theme = (await session.execute(select(Theme).where(Theme.name == theme_name, Theme.deleted_at.is_(None)))).scalar_one_or_none()
    if theme is None:
        raise ValueError(f"找不到题材：{theme_name}")

    existing = {node.path_key: node for node in (await session.execute(select(ConceptNode).where(ConceptNode.theme_id == theme.id))).scalars()}
    nodes: dict[str, ConceptNode] = {}
    for order, (path, parent_path, name, node_type, description, chain_level) in enumerate(NODES):
        node = existing.get(path) or ConceptNode(theme_id=theme.id, path_key=path, slug=path.rsplit("/", 1)[-1])
        node.parent = nodes.get(parent_path)
        node.name, node.node_type, node.description = name, node_type, description
        node.chain_level, node.depth, node.sort_order = chain_level, path.count("/"), order
        node.market_logic = "机器人渗透率提升将带动该环节需求，实际节奏取决于量产、成本与可靠性验证。"
        node.catalysts = ["整机量产进度", "核心部件降本", "应用场景验证"]
        node.risks = ["技术路线变化", "商业化不及预期", "估值波动"]
        node.sources, node.confidence = [ROOT_SOURCE], Decimal("0.900")
        session.add(node)
        nodes[path] = node
    await session.flush()

    stock_map = {stock.code: stock for stock in (await session.execute(select(Stock).where(Stock.code.in_([item[1] for item in STOCK_LINKS])))).scalars()}
    linked = 0
    for path, code, relation_type, rationale, score, is_core, url in STOCK_LINKS:
        stock = stock_map.get(code)
        if stock is None:
            continue
        node = nodes[path]
        link = await session.get(ConceptNodeStock, (node.id, stock.id))
        if link is None:
            link = ConceptNodeStock(node_id=node.id, stock_id=stock.id)
        link.relation_type, link.rationale = relation_type, rationale
        link.relevance_score, link.is_core = Decimal(str(score)), is_core
        link.sources = [{"title": f"{stock.name}官方网站与公开信息", "url": url, "publisher": stock.name}]
        session.add(link)
        linked += 1
    await session.commit()
    return {"theme_id": theme.id, "nodes": len(nodes), "stocks": linked}


async def remove_generated_equal_split_chains(session: AsyncSession) -> int:
    generated_ids = list((await session.execute(select(IndustryChain.id).where(IndustryChain.description.like("%基于现有成分股结构推导%")))).scalars())
    if not generated_ids:
        return 0
    await session.execute(delete(IndustryChain).where(IndustryChain.id.in_(generated_ids)))
    await session.execute(update(ThemeStock).where(ThemeStock.chain_level.in_(("upstream", "midstream", "downstream"))).values(chain_level=None))
    await session.commit()
    return len(generated_ids)
