"""概念知识图谱服务测试。"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.concept_node import ConceptNode
from app.models.concept_node_stock import ConceptNodeStock
from app.models.stock import Stock
from app.services.concept_graph import ConceptGraphService


@pytest.mark.asyncio
async def test_get_graph_builds_recursive_tree_with_stock_rationale():
    service = ConceptGraphService(AsyncMock())
    root = ConceptNode(
        id=1,
        theme_id=294,
        parent_id=None,
        name="机器人",
        slug="robotics",
        path_key="robotics",
        node_type="domain",
        catalysts=[],
        risks=[],
        sources=[],
        confidence=Decimal("0.980"),
        depth=0,
        sort_order=0,
        updated_at=datetime(2026, 7, 16, tzinfo=UTC),
    )
    child = ConceptNode(
        id=2,
        theme_id=294,
        parent_id=1,
        name="电子皮肤",
        slug="electronic-skin",
        path_key="robotics/dexterous-hand/sensing/electronic-skin",
        node_type="technology",
        catalysts=["人形机器人触觉需求提升"],
        risks=["商业化进度不确定"],
        sources=[],
        confidence=Decimal("0.850"),
        depth=4,
        sort_order=0,
        updated_at=datetime(2026, 7, 16, tzinfo=UTC),
    )
    stock = Stock(id=9, code="605488", name="福莱新材")
    link = ConceptNodeStock(
        node_id=2,
        stock_id=9,
        relation_type="材料布局",
        rationale="布局柔性传感器相关材料，关注电子皮肤方向。",
        relevance_score=Decimal("0.880"),
        is_core=True,
        sources=[],
    )
    link.stock = stock
    child.stock_links = [link]
    root.stock_links = []
    service.repo.list_nodes = AsyncMock(return_value=[root, child])

    result = await service.get_graph(294)

    assert result.node_count == 2
    assert result.stock_count == 1
    assert result.max_depth == 4
    assert result.roots[0].children[0].name == "电子皮肤"
    assert result.roots[0].children[0].stocks[0].code == "605488"
    assert "柔性传感器" in result.roots[0].children[0].stocks[0].rationale


@pytest.mark.asyncio
async def test_get_graph_returns_empty_graph_without_guesses():
    service = ConceptGraphService(AsyncMock())
    service.repo.list_nodes = AsyncMock(return_value=[])

    result = await service.get_graph(999)

    assert result.roots == []
    assert result.node_count == 0
    assert result.stock_count == 0
    assert result.updated_at is None
