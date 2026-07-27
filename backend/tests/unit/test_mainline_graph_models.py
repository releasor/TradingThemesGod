"""主线图谱 ORM 模型测试。"""

from app.models.mainline_graph import (
    MainlineGraphEdge,
    MainlineGraphNode,
    MainlineGraphVersion,
)


def _constraint_names(table):
    return {c.name for c in table.constraints if c.name}


def test_mainline_graph_version_columns_and_indexes():
    cols = {c.name for c in MainlineGraphVersion.__table__.columns}
    assert {
        "id",
        "trade_date",
        "kind",
        "title",
        "status",
        "parent_version_id",
        "created_by",
        "published_at",
        "meta",
        "created_at",
        "updated_at",
    } <= cols

    index_names = {i.name for i in MainlineGraphVersion.__table__.indexes}
    assert "idx_mainline_graph_versions_date_kind_status" in index_names


def test_mainline_graph_node_columns_and_constraints():
    cols = {c.name for c in MainlineGraphNode.__table__.columns}
    assert {
        "id",
        "version_id",
        "theme_id",
        "mainline_score",
        "strength_score",
        "lifecycle_stage",
        "role",
        "payload",
    } <= cols

    assert "uq_mainline_graph_nodes_version_theme" in _constraint_names(
        MainlineGraphNode.__table__
    )


def test_mainline_graph_edge_columns_and_constraints():
    cols = {c.name for c in MainlineGraphEdge.__table__.columns}
    assert {
        "id",
        "version_id",
        "from_theme_id",
        "to_theme_id",
        "weight",
        "method",
        "status",
        "rationale",
        "created_by",
    } <= cols

    assert "uq_mainline_graph_edges_version_from_to" in _constraint_names(
        MainlineGraphEdge.__table__
    )
