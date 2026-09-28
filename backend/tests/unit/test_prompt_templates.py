"""prompt_templates 单元测试。"""

from app.services.prompt_templates import (
    FRAMEWORKS,
    build_design_system,
    build_optimize_system,
)


def test_frameworks_include_crispe():
    assert "CRISPE" in FRAMEWORKS


def test_smart_system_mentions_clarity_and_extra_goal():
    text = build_optimize_system(mode="smart", framework=None, extra_goal="更短")
    assert "清楚" in text or "清晰" in text
    assert "更短" in text


def test_crispe_system_includes_framework_hint():
    text = build_optimize_system(mode="framework", framework="CRISPE", extra_goal=None)
    assert "CRISPE" in text.upper() or "角色" in text


def test_design_system_mentions_variables():
    text = build_design_system()
    assert "{{" in text or "变量" in text or "可复用" in text


def test_no_third_party_brand():
    blob = " ".join(
        [
            build_design_system(),
            build_optimize_system(mode="smart", framework=None, extra_goal=None),
            *[
                build_optimize_system(mode="framework", framework=f, extra_goal=None)
                for f in FRAMEWORKS
            ],
        ]
    ).lower()
    assert "prizm" not in blob
