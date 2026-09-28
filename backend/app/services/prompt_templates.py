"""Prompt 工作台系统提示模板（无外部品牌词）。"""

from __future__ import annotations

FRAMEWORKS = ("CRISPE", "CO-STAR", "APE", "BROKE", "TRACE", "RTF")

_FRAMEWORK_HINTS: dict[str, str] = {
    "CRISPE": (
        "按 CRISPE 组织：Capacity/Role（角色）、Insight（背景）、"
        "Statement（任务）、Personality（风格）、Experiment（示例/约束）。"
    ),
    "CO-STAR": (
        "按 CO-STAR 组织：Context、Objective、Style、Tone、Audience、Response。"
    ),
    "APE": "按 APE 组织：Action、Purpose、Expectation。保持简短直接。",
    "BROKE": (
        "按 BROKE 组织：Background、Role、Objectives、Key results、Evolve（可迭代约束）。"
    ),
    "TRACE": (
        "按 TRACE 组织：Task、Request、Action、Context、Example；用示例带动结构。"
    ),
    "RTF": "按 RTF 组织：Role、Task、Format。尽量简短。",
}


def build_design_system() -> str:
    return (
        "你是 Prompt 设计助手。根据用户的任务目标，写出一份可复用、结构清晰的 Prompt。"
        "必要时使用 {{variable_name}} 占位符表示可变部分。"
        "只输出 Prompt 正文，不要解释，不要用 Markdown 代码围栏包裹。"
    )


def build_design_user(goal: str, notes: str | None) -> str:
    parts = [f"任务目标：\n{goal.strip()}"]
    if notes and notes.strip():
        parts.append(f"补充约束：\n{notes.strip()}")
    return "\n\n".join(parts)


def build_optimize_system(
    *,
    mode: str,
    framework: str | None,
    extra_goal: str | None,
) -> str:
    base = (
        "你是 Prompt 优化助手。在保留原意的前提下，改写得更清楚、完整、便于模型执行。"
        "只输出优化后的 Prompt 正文，不要解释，不要用 Markdown 代码围栏包裹。"
    )
    if mode == "framework" and framework:
        key = framework.upper()
        hint = _FRAMEWORK_HINTS.get(key, f"按 {key} 框架重组结构。")
        base = f"{base}\n请{hint}"
    else:
        base = (
            f"{base}\n采用 Smart 方式：保留原意，补全缺失的角色/约束/输出格式，"
            "让表述更清晰可执行。"
        )
        if extra_goal and extra_goal.strip():
            base = f"{base}\n额外目标：{extra_goal.strip()}"
    return base


def build_optimize_user(source: str) -> str:
    return f"原始 Prompt：\n{source.strip()}"


def build_iterate_system() -> str:
    return (
        "你是 Prompt 改写助手。根据用户的修改指令，在当前 Prompt 基础上改写。"
        "只输出改写后的完整 Prompt，不要解释。"
    )


def build_iterate_user(current: str, instruction: str) -> str:
    return (
        f"当前 Prompt：\n{current.strip()}\n\n"
        f"修改指令：\n{instruction.strip()}"
    )


def build_chat_system() -> str:
    return (
        "你是有帮助的助手。回答清晰、具体。若用户粘贴了 Prompt，可直接按该 Prompt 执行。"
    )
