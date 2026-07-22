"""概念知识图谱查询。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.concept_node import ConceptNode
from app.models.concept_node_stock import ConceptNodeStock


class ConceptGraphRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_nodes(self, theme_id: int) -> list[ConceptNode]:
        query = (
            select(ConceptNode)
            .where(ConceptNode.theme_id == theme_id)
            .options(selectinload(ConceptNode.stock_links).selectinload(ConceptNodeStock.stock))
            .order_by(ConceptNode.depth, ConceptNode.sort_order, ConceptNode.id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
