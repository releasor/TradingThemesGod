"""题材挖掘 ORM 模型测试。"""

from app.models.theme_mining import ThemeMiningCard, ThemeMiningMember, ThemeMiningNote


def _constraint_names(table):
    return {c.name for c in table.constraints if c.name}


def test_theme_mining_card_columns_and_constraints():
    cols = {c.name for c in ThemeMiningCard.__table__.columns}
    assert {
        "id",
        "trade_date",
        "theme_id",
        "mining_type",
        "score",
        "rank",
        "lifecycle_stage",
        "strength_score",
        "rationale",
        "score_breakdown",
        "degraded",
        "missing_metrics",
    } <= cols

    assert "uq_theme_mining_cards_date_theme_type" in _constraint_names(
        ThemeMiningCard.__table__
    )

    index_names = {i.name for i in ThemeMiningCard.__table__.indexes}
    assert "idx_theme_mining_cards_date_type_rank" in index_names


def test_theme_mining_member_columns_and_constraints():
    cols = {c.name for c in ThemeMiningMember.__table__.columns}
    assert {
        "id",
        "card_id",
        "stock_id",
        "concept_node_id",
        "score",
        "rank",
        "role_tag",
        "metrics",
    } <= cols

    assert "uq_theme_mining_members_card_stock" in _constraint_names(
        ThemeMiningMember.__table__
    )

    index_names = {i.name for i in ThemeMiningMember.__table__.indexes}
    assert "idx_theme_mining_members_card_rank" in index_names


def test_theme_mining_note_columns_and_constraints():
    cols = {c.name for c in ThemeMiningNote.__table__.columns}
    assert {
        "id",
        "card_id",
        "user_id",
        "status",
        "content_md",
        "model_name",
        "error",
        "created_at",
        "updated_at",
    } <= cols

    assert "uq_theme_mining_notes_card_user" in _constraint_names(
        ThemeMiningNote.__table__
    )
