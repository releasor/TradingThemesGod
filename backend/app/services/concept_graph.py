"""概念知识图谱树构建服务。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept_node import ConceptNode
from app.repositories.concept_graph import ConceptGraphRepository
from app.schemas.concept_graph import (
    ConceptGraphResponse,
    ConceptNodeResponse,
    ConceptStockLink,
)


class ConceptGraphService:
    def __init__(self, session: AsyncSession):
        self.repo = ConceptGraphRepository(session)

    async def get_graph(self, theme_id: int) -> ConceptGraphResponse:
        nodes = await self.repo.list_nodes(theme_id)
        if not nodes:
            return ConceptGraphResponse()

        children_by_parent: dict[int | None, list[ConceptNode]] = {}
        for node in nodes:
            children_by_parent.setdefault(node.parent_id, []).append(node)

        def build(node: ConceptNode) -> ConceptNodeResponse:
            return ConceptNodeResponse(
                id=node.id,
                name=node.name,
                node_type=node.node_type,
                description=node.description,
                chain_level=node.chain_level,
                market_logic=node.market_logic,
                catalysts=node.catalysts or [],
                risks=node.risks or [],
                sources=node.sources or [],
                confidence=node.confidence,
                depth=node.depth,
                stocks=[ConceptStockLink(code=link.stock.code, name=link.stock.name, relation_type=link.relation_type, rationale=link.rationale, relevance_score=link.relevance_score, is_core=link.is_core, sources=link.sources or []) for link in node.stock_links],
                children=[build(child) for child in children_by_parent.get(node.id, [])],
            )

        stock_ids = {link.stock_id for node in nodes for link in node.stock_links}
        return ConceptGraphResponse(
            roots=[build(node) for node in children_by_parent.get(None, [])],
            node_count=len(nodes),
            stock_count=len(stock_ids),
            max_depth=max(node.depth for node in nodes),
            updated_at=max(node.updated_at for node in nodes),
        )
