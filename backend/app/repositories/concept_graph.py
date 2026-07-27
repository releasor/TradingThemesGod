"""概念知识图谱查询。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.concept_node import ConceptNode
from app.models.concept_node_stock import ConceptNodeStock


class ConceptGraphRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_nodes(
        self,
        theme_id: int,
        *,
        include_stocks: bool = True,
    ) -> list[ConceptNode]:
        query = (
            select(ConceptNode)
            .where(ConceptNode.theme_id == theme_id)
            .order_by(ConceptNode.depth, ConceptNode.sort_order, ConceptNode.id)
        )
        if include_stocks:
            query = query.options(
                selectinload(ConceptNode.stock_links).selectinload(ConceptNodeStock.stock)
            )
        result = await self.session.execute(query)
        return list(result.scalars().all())
