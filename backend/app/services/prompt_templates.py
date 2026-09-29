"""Prompt 工作台系统提示模板（无外部品牌词）。"""

from __future__ import annotations

FRAMEWORKS = ("CRISPE", "CO-STAR", "APE", "BROKE", "TRACE", "RTF")

_FRAMEWORK_HINTS: dict[str, str] = {
    "CRISPE": (
        "按 CRISPE 重组，并尽量使用这些可见小标题（可中英混排）："
        "\n- Capacity/Role（角色与能力）"
        "\n- Insight（背景与洞察）"
        "\n- Statement（具体任务）"
        "\n- Personality（语气与风格）"
        "\n- Experiment（示例、约束或自检）"
    ),
    "CO-STAR": (
        "按 CO-STAR 重组，并尽量使用这些小标题："
        "\n- Context（情境）\n- Objective（目标）\n- Style（风格）"
        "\n- Tone（语气）\n- Audience（受众）\n- Response（期望回复格式）"
    ),
    "APE": (
        "按 APE 重组，结构简洁直给："
        "\n- Action（要做什么）\n- Purpose（为何做）\n- Expectation（交付标准）"
    ),
    "BROKE": (
        "按 BROKE 重组，适合多步任务："
        "\n- Background（背景）\n- Role（角色）\n- Objectives（目标）"
        "\n- Key results（关键结果/验收）\n- Evolve（可迭代约束）"
    ),
    "TRACE": (
        "按 TRACE 重组，强调示例与结构："
        "\n- Task（任务）\n- Request（具体请求）\n- Action（执行步骤）"
        "\n- Context（上下文）\n- Example（示例）"
    ),
    "RTF": (
        "按 RTF 重组，保持简短："
        "\n- Role（角色）\n- Task（任务）\n- Format（输出格式）"
    ),
}


def build_design_system() -> str:
    return (
        "你是 Prompt 设计助手。根据用户给出的目标，写出一份可复用、结构清晰的 Prompt。"
        "需要时使用 {{variable_name}} 占位符表示可变部分。"
        "只输出 Prompt 正文，不要解释，不要用 Markdown 代码围栏包裹。"
    )


def build_design_user(goal: str, notes: str | None) -> str:
    parts = [f"设计目标：\n{goal.strip()}"]
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
        "你是 Prompt 优化助手。在保留原意的前提下，改写得更清晰、可执行、便于复用。"
        "优先补全：角色、输入、约束、输出格式、失败兜底；保留已有 {{variable}} 占位符。"
        "只输出优化后的 Prompt 正文，不要解释，不要用 Markdown 代码围栏包裹。"
    )
    if mode == "framework" and framework:
        key = framework.upper()
        hint = _FRAMEWORK_HINTS.get(key, f"按 {key} 框架重组结构。")
        base = f"{base}\n{hint}"
    else:
        base = (
            f"{base}\n采用 Smart 方式：补全缺失的角色/约束/输出格式，"
            "让普通人也能直接执行；不要空话套话。"
        )
    if extra_goal and extra_goal.strip():
        base = f"{base}\n额外目标：{extra_goal.strip()}"
    return base


def build_optimize_user(source: str) -> str:
    return f"原始 Prompt：\n{source.strip()}"


def build_iterate_system() -> str:
    return (
        "你是 Prompt 改写助手。按用户的修改指令，在当前 Prompt 上做最小必要改动。"
        "保留原有结构、标题层级与 {{variable}} 占位符；不要无故重写全文。"
        "只输出改写后的完整 Prompt，不要解释，不要用代码围栏包裹。"
    )


def build_iterate_user(current: str, instruction: str) -> str:
    return (
        f"当前 Prompt：\n{current.strip()}\n\n"
        f"修改指令：\n{instruction.strip()}"
    )


def build_chat_system() -> str:
    return (
        "你是有帮助的助手。回答清晰具体。若用户粘贴了 Prompt，请直接按照 Prompt 执行。"
    )
