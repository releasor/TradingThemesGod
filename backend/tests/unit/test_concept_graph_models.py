"""概念知识图谱模型测试。"""

from sqlalchemy import JSON

from app.models.concept_node import ConceptNode
from app.models.concept_node_stock import ConceptNodeStock


def test_concept_node_has_recursive_graph_fields():
    columns = ConceptNode.__table__.c

    assert next(iter(columns.theme_id.foreign_keys)).target_fullname == "themes.id"
    assert next(iter(columns.parent_id.foreign_keys)).target_fullname == "concept_nodes.id"
    assert isinstance(columns.catalysts.type, JSON)
    assert isinstance(columns.risks.type, JSON)
    assert isinstance(columns.sources.type, JSON)
    assert {
        "name",
        "slug",
        "path_key",
        "node_type",
        "description",
        "chain_level",
        "market_logic",
        "confidence",
        "depth",
        "sort_order",
    }.issubset(columns.keys())


def test_concept_node_has_stable_path_and_parent_indexes():
    indexes = {index.name: index for index in ConceptNode.__table__.indexes}

    assert "idx_concept_node_theme_parent" in indexes
    assert indexes["idx_concept_node_theme_path"].unique is True


def test_concept_node_stock_has_composite_key_and_stock_index():
    primary_key = [column.name for column in ConceptNodeStock.__table__.primary_key]
    indexes = {index.name for index in ConceptNodeStock.__table__.indexes}

    assert primary_key == ["node_id", "stock_id"]
    assert "idx_concept_node_stock_stock_id" in indexes
    assert isinstance(ConceptNodeStock.__table__.c.sources.type, JSON)
