"""个人 AI OS 默认配置。"""

from __future__ import annotations

DEFAULT_SYSTEM_PROMPT = (
    "你是用户的个人 AI 操作系统助手。"
    "基于用户档案、笔记与近期上下文，给出务实、可执行的建议。"
    "你出草案与选项，由用户做最终拍板；不要假装替用户做人生决定。"
    "不确定时先澄清，不要编造用户未提供的事实。"
    "涉及健康或财务时提醒：仅供参考，不构成医嘱或投资建议。"
)

# 决策「开图」脚手架：先探清资源/约束/样本，再让多模型出上中下策
SCOUT_TEMPLATES: list[dict] = [
    {
        "id": "career",
        "title": "职业 / 方向",
        "question": "我在考虑下一阶段职业方向，请先帮我开图再给上中下策。",
        "constraints": (
            "【资源】我已有的技能/人脉/时间预算：\n"
            "【约束】不可破底线（城市/收入/家庭）：\n"
            "【已看样本】至少列出对比过的选项或案例：\n"
            "【版本】当前市场/行业变化我注意到的：\n"
            "请先指出信息缺口，再给可执行方案。"
        ),
        "hint": "适合换赛道、选专业、是否跳槽",
    },
    {
        "id": "project",
        "title": "项目 / 投入",
        "question": "这个项目值不值得继续投入？请开图后给上中下策。",
        "constraints": (
            "【资源】已投入与还能投入的时间/金钱：\n"
            "【约束】最坏情况我能承受什么：\n"
            "【已看样本】同类项目或竞品我研究过的：\n"
            "【验证指标】两周内可观测的信号：\n"
            "请区分「继续探」与「重注」。"
        ),
        "hint": "适合副业、产品、学习计划是否加码",
    },
    {
        "id": "habit",
        "title": "习惯 / 健康节奏",
        "question": "我想调整日常节奏（睡眠/训练/饮食），请基于约束给上中下策。",
        "constraints": (
            "【现状】最近两周大致作息与感觉：\n"
            "【目标】可量化指标（非医疗诊断）：\n"
            "【约束】不可破底线（伤病、时间窗）：\n"
            "【已试过】失败过的方法：\n"
            "提醒：非医嘱，只给可执行生活实验。"
        ),
        "hint": "适合作息调参，不做处方式医疗建议",
    },
]

DEFAULT_MEMORY_POLICY: dict = {
    "inject_profile": True,
    "note_top_k": 5,
    "recent_turns": 20,
}

DEFAULT_MODULE_FLAGS: dict = {
    "chat": True,
    "memory": True,
    "journal": True,
    "reports": True,
    "decisions": True,
}

DEFAULT_MODEL_PREFS: dict = {
    "default_provider_id": None,
    "compare_provider_ids": [],
}

DEFAULT_HEALTH_BASELINE: dict = {}
