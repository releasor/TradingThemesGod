"""主线图谱规则引擎测试。"""

from app.services.mainline_graph_rules import (
    ThemeSnap,
    assign_roles,
    build_edges,
    jaccard,
)


def test_jaccard_basic():
    assert jaccard({1, 2, 3}, {2, 3, 4}) == 0.5
    assert jaccard(set(), set()) == 0.0
    assert jaccard({1}, set()) == 0.0
    assert jaccard({1, 2}, {1, 2}) == 1.0


def test_build_edges_directs_from_higher_mainline():
    themes = [
        ThemeSnap(theme_id=10, mainline_score=90),
        ThemeSnap(theme_id=20, mainline_score=50),
        ThemeSnap(theme_id=30, mainline_score=40),
    ]
    overlap = {(10, 20): 0.4, (10, 30): 0.2}

    edges = build_edges(themes, overlap, jaccard_min=0.12, top_main=1)

    assert len(edges) == 2
    by_to = {edge.to_theme_id: edge for edge in edges}
    assert by_to[20].from_theme_id == 10
    assert by_to[20].weight == 0.4
    assert by_to[30].from_theme_id == 10
    assert all(edge.method == "rules" and edge.status == "active" for edge in edges)


def test_build_edges_filters_below_threshold():
    themes = [
        ThemeSnap(theme_id=1, mainline_score=80),
        ThemeSnap(theme_id=2, mainline_score=40),
    ]
    overlap = {(1, 2): 0.05}

    edges = build_edges(themes, overlap, jaccard_min=0.12, top_main=1)

    assert edges == []


def test_build_edges_tie_uses_lower_theme_id_as_from():
    themes = [
        ThemeSnap(theme_id=5, mainline_score=70),
        ThemeSnap(theme_id=8, mainline_score=70),
    ]
    overlap = {(5, 8): 0.25}

    edges = build_edges(themes, overlap, jaccard_min=0.12, top_main=2)

    assert len(edges) == 1
    assert edges[0].from_theme_id == 5
    assert edges[0].to_theme_id == 8


def test_build_edges_skips_pairs_without_top_main():
    themes = [
        ThemeSnap(theme_id=1, mainline_score=100),
        ThemeSnap(theme_id=2, mainline_score=50),
        ThemeSnap(theme_id=3, mainline_score=40),
        ThemeSnap(theme_id=4, mainline_score=30),
    ]
    # only branch-branch overlap for 3-4; main is theme 1
    overlap = {(3, 4): 0.9, (1, 2): 0.3}

    edges = build_edges(themes, overlap, jaccard_min=0.12, top_main=1)

    assert len(edges) == 1
    assert edges[0].from_theme_id == 1
    assert edges[0].to_theme_id == 2


def test_assign_roles_marks_top_mainline():
    themes = [
        ThemeSnap(theme_id=1, mainline_score=10),
        ThemeSnap(theme_id=2, mainline_score=90),
        ThemeSnap(theme_id=3, mainline_score=50),
    ]
    roles = assign_roles(themes, top_main=2)
    assert roles[2] == "mainline"
    assert roles[3] == "mainline"
    assert roles[1] == "branch"
