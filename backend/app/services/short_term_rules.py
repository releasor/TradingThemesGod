"""短线机会雷达规则引擎。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketStrengthInput:
    """市场强弱判断输入。"""

    index_score: float | None
    emotion_score: float | None
    consecutive_board_count: float | None = None
    rotation_score: float | None = None
    period_label: str | None = None


@dataclass(frozen=True)
class MarketStrategyCard:
    """指数与情绪组合后的短线策略卡片。"""

    title: str
    index_strength: str
    emotion_strength: str
    primary_strategy: str
    secondary_strategy: str
    operation_advice: str
    focus_targets: list[str]
    rationale: list[str]


class ShortTermRuleEngine:
    """根据指数、情绪和轮动状态输出短线策略。"""

    INDEX_STRONG_THRESHOLD = 0.3
    EMOTION_STRONG_THRESHOLD = 60
    EMOTION_ICE_THRESHOLD = 30
    ROTATION_ACTIVE_THRESHOLD = 60

    def evaluate_market_strategy(
        self, strength: MarketStrengthInput
    ) -> MarketStrategyCard:
        """生成指数/情绪组合策略卡。"""
        index_score = strength.index_score or 0
        emotion_score = strength.emotion_score or 0
        board_count = strength.consecutive_board_count or 0
        board_count_text = f"{board_count:.1f}"
        rotation_score = strength.rotation_score or 0
        period_label = strength.period_label or "当前周期"

        index_strength = (
            "strong" if index_score >= self.INDEX_STRONG_THRESHOLD else "weak"
        )
        emotion_strength = (
            "strong" if emotion_score >= self.EMOTION_STRONG_THRESHOLD else "weak"
        )

        if index_strength == "strong" and emotion_strength == "strong":
            primary = "连板接力"
            advice = f"{period_label}指数强、情绪强，做连板；情绪参考日均连板 {board_count_text}，优先主线内换手晋级。"
            focus = [f"{period_label}连板梯队", "主线题材前排", "换手充分的二板以上"]
        elif index_strength == "strong" and emotion_strength == "weak":
            if emotion_score <= self.EMOTION_ICE_THRESHOLD:
                primary = "冰点反核与切换"
                advice = f"{period_label}指数强但情绪接近冰点，优先做反核观察和高低切换；日均连板 {board_count_text} 偏低，不追一致连板。"
                focus = [f"{period_label}冰点反核", "低位新题材切换", "放量修复前排"]
            elif rotation_score >= self.ROTATION_ACTIVE_THRESHOLD:
                primary = "轮动低吸与趋势切换"
                advice = f"{period_label}指数强但情绪弱，轮动强度较高，做轮动低吸、趋势承接和高低切换；日均连板 {board_count_text} 仅作风险参考。"
                focus = [f"{period_label}轮动低吸", "趋势承接", "新题材切换"]
            else:
                primary = "补涨趋势与切换"
                advice = f"{period_label}指数强但情绪弱，做补涨、趋势和高低切换，避免追缩量一致；日均连板 {board_count_text} 偏低。"
                focus = [f"{period_label}低位补涨", "趋势承接", "新题材切换"]
        elif index_strength == "weak" and emotion_strength == "strong":
            primary = "高标博弈"
            advice = f"{period_label}指数弱但情绪强，做高标辨识度，仓位向核心龙头集中；日均连板 {board_count_text} 支撑高标博弈。"
            focus = [f"{period_label}市场高标", "抱团核心", "分歧后回封"]
        else:
            primary = "老龙抱团或空仓"
            advice = f"{period_label}指数弱、情绪弱，做老龙、抱团，空仓更好；只观察冰点反核信号，日均连板 {board_count_text} 不支持接力。"
            focus = [f"{period_label}老龙回流", "抱团承接", "空仓等待"]

        secondary = self._secondary_strategy(emotion_score, rotation_score)
        rationale = [
            f"指数强度 {index_score:.2f}，判定为{'强' if index_strength == 'strong' else '弱'}。",
            f"情绪强度 {emotion_score:.0f}，日均连板 {board_count_text}，判定为{'强' if emotion_strength == 'strong' else '弱'}。",
            f"轮动强度 {rotation_score:.0f}，辅助策略为{secondary}。",
        ]

        return MarketStrategyCard(
            title=f"指数情绪策略卡 · {period_label}",
            index_strength=index_strength,
            emotion_strength=emotion_strength,
            primary_strategy=primary,
            secondary_strategy=secondary,
            operation_advice=advice,
            focus_targets=focus,
            rationale=rationale,
        )

    def _secondary_strategy(self, emotion_score: float, rotation_score: float) -> str:
        if emotion_score <= self.EMOTION_ICE_THRESHOLD:
            return "情绪冰点反核"
        if emotion_score >= self.EMOTION_STRONG_THRESHOLD:
            return "主升分歧接力"
        if rotation_score >= self.ROTATION_ACTIVE_THRESHOLD:
            return "轮动低吸"
        return "等待确认"
