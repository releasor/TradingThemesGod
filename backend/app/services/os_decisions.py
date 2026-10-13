"""个人 AI OS 多模型决策服务。"""

from __future__ import annotations

import asyncio
import json
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_os import OsDecisionOption, OsDecisionRun, OsDecisionThread
from app.schemas.personal_os import (
    OsDecisionChooseRequest,
    OsDecisionCreate,
    OsDecisionOptionFeedback,
    OsDecisionOptionResponse,
    OsDecisionRunRequest,
    OsDecisionRunResponse,
    OsDecisionThreadResponse,
)
from app.services.os_profile import OsProfileService
from app.services.prompt_llm import PromptLLMService

_TIERS = ("upper", "mid", "lower")
_TIER_LABELS = {"upper": "上策", "mid": "中策", "lower": "下策"}


class OsDecisionsService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.llm = PromptLLMService(session, user_id)
        self.profiles = OsProfileService(session, user_id)

    async def list_threads(self, limit: int = 50) -> list[OsDecisionThreadResponse]:
        await self.profiles.require_module("decisions")
        result = await self.session.execute(
            select(OsDecisionThread)
            .where(OsDecisionThread.user_id == self.user_id)
            .order_by(OsDecisionThread.updated_at.desc())
            .limit(min(limit, 100))
        )
        threads = list(result.scalars())
        out: list[OsDecisionThreadResponse] = []
        for t in threads:
            out.append(await self._to_response(t, include_run=True))
        return out

    async def create(self, payload: OsDecisionCreate) -> OsDecisionThreadResponse:
        await self.profiles.require_module("decisions")
        thread = OsDecisionThread(
            user_id=self.user_id,
            question=payload.question.strip(),
            constraints=payload.constraints,
            status="open",
        )
        self.session.add(thread)
        await self.session.commit()
        await self.session.refresh(thread)
        return await self._to_response(thread, include_run=False)

    async def get(self, thread_id: int) -> OsDecisionThreadResponse:
        await self.profiles.require_module("decisions")
        thread = await self._get_owned(thread_id)
        return await self._to_response(thread, include_run=True)

    async def _get_owned(self, thread_id: int) -> OsDecisionThread:
        thread = await self.session.get(OsDecisionThread, thread_id)
        if thread is None or thread.user_id != self.user_id:
            raise HTTPException(404, "决策不存在")
        return thread

    async def _latest_run(self, thread_id: int) -> OsDecisionRun | None:
        result = await self.session.execute(
            select(OsDecisionRun)
            .where(OsDecisionRun.thread_id == thread_id)
            .order_by(OsDecisionRun.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _options_for_run(self, run_id: int) -> list[OsDecisionOption]:
        result = await self.session.execute(
            select(OsDecisionOption)
            .where(OsDecisionOption.run_id == run_id)
            .order_by(OsDecisionOption.id.asc())
        )
        return list(result.scalars())

    async def _to_response(
        self, thread: OsDecisionThread, *, include_run: bool
    ) -> OsDecisionThreadResponse:
        latest = None
        if include_run:
            run = await self._latest_run(thread.id)
            if run is not None:
                options = await self._options_for_run(run.id)
                latest = OsDecisionRunResponse(
                    id=run.id,
                    thread_id=run.thread_id,
                    summary=run.summary,
                    provider_ids=list(run.provider_ids or []),
                    options=[
                        OsDecisionOptionResponse.model_validate(o) for o in options
                    ],
                    created_at=run.created_at,
                    updated_at=run.updated_at,
                )
        base = OsDecisionThreadResponse.model_validate(thread)
        return base.model_copy(update={"latest_run": latest})

    async def run(
        self, thread_id: int, payload: OsDecisionRunRequest
    ) -> OsDecisionThreadResponse:
        await self.profiles.require_module("decisions")
        thread = await self._get_owned(thread_id)
        profile = await self.profiles.ensure_profile()
        prefs = profile.model_prefs or {}
        provider_ids = payload.provider_ids or list(
            prefs.get("compare_provider_ids") or []
        )
        if not provider_ids:
            default_id = prefs.get("default_provider_id")
            if default_id is not None:
                provider_ids = [default_id]
        if not provider_ids:
            raise HTTPException(
                400, "请先在 OS 设置中配置对比模型，或指定 provider_ids"
            )

        user_prompt = (
            f"决策问题：{thread.question}\n"
            f"约束条件：{thread.constraints or '无'}\n\n"
            "请先指出信息是否足够「开图」（资源/约束/样本/版本），"
            "再给出清晰建议：结论、理由、风险与下一步。控制在 400 字内。"
            "你只出草案，最终拍板权在用户。"
        )
        system = (
            "你是决策参谋。结合用户问题给出可执行建议，不要空话。"
            "优先「开图」：信息不足时先列探测清单，再谈下注。"
            f"用户人设提示：{(profile.system_prompt or '')[:500]}"
        )
        decision_appendix = (getattr(profile, "decision_prompt_appendix", None) or "").strip()
        if decision_appendix:
            system += f"\n\n【用户历史决策调参】\n{decision_appendix[-2000:]}"

        async def _one(pid: int) -> tuple[int, str]:
            try:
                text = await self.llm.run_completion(
                    system, user_prompt, provider_id=pid
                )
                return pid, (text or "").strip()
            except Exception as exc:  # noqa: BLE001
                return pid, f"（模型调用失败：{exc}）"

        replies = await asyncio.gather(*[_one(pid) for pid in provider_ids])

        summarize_pid = payload.summarize_provider_id or provider_ids[0]
        packed = "\n\n".join(
            f"### 模型 provider_id={pid}\n{text}" for pid, text in replies
        )
        summarize_system = (
            "你将多模型建议归一为上中下三策。"
            "严格输出 JSON（不要 markdown 围栏）："
            '{"summary":"...","options":['
            '{"tier":"upper","title":"...","content":"..."},'
            '{"tier":"mid","title":"...","content":"..."},'
            '{"tier":"lower","title":"...","content":"..."}]}'
        )
        summarize_user = (
            f"原问题：{thread.question}\n约束：{thread.constraints or '无'}\n\n"
            f"各模型原文：\n{packed}"
        )
        try:
            summary_raw = await self.llm.run_completion(
                summarize_system, summarize_user, provider_id=summarize_pid
            )
            parsed = _parse_tiers(summary_raw)
        except Exception:  # noqa: BLE001
            parsed = _fallback_tiers(replies)

        run = OsDecisionRun(
            thread_id=thread.id,
            summary=parsed.get("summary") or "多模型决策汇总",
            provider_ids=provider_ids,
        )
        self.session.add(run)
        await self.session.flush()

        for opt in parsed.get("options") or []:
            tier = opt.get("tier") or "mid"
            if tier not in _TIERS:
                tier = "mid"
            self.session.add(
                OsDecisionOption(
                    run_id=run.id,
                    tier=tier,
                    title=(opt.get("title") or _TIER_LABELS[tier])[:200],
                    content=opt.get("content") or "",
                    provider_id=summarize_pid,
                    raw_reply=packed[:8000],
                    selected=False,
                )
            )
        thread.status = "analyzed"
        await self.session.commit()
        await self.session.refresh(thread)
        return await self._to_response(thread, include_run=True)

    async def choose(
        self, thread_id: int, payload: OsDecisionChooseRequest
    ) -> OsDecisionThreadResponse:
        await self.profiles.require_module("decisions")
        thread = await self._get_owned(thread_id)
        option = await self.session.get(OsDecisionOption, payload.option_id)
        if option is None:
            raise HTTPException(404, "选项不存在")
        run = await self.session.get(OsDecisionRun, option.run_id)
        if run is None or run.thread_id != thread.id:
            raise HTTPException(400, "选项不属于该决策")
        for o in await self._options_for_run(run.id):
            o.selected = o.id == option.id
        thread.chosen_option_id = option.id
        thread.outcome_note = payload.outcome_note
        thread.status = "chosen"
        await self.session.commit()
        await self.session.refresh(thread)
        return await self._to_response(thread, include_run=True)

    async def option_feedback(
        self, option_id: int, payload: OsDecisionOptionFeedback
    ) -> OsDecisionOptionResponse:
        await self.profiles.require_module("decisions")
        option = await self.session.get(OsDecisionOption, option_id)
        if option is None:
            raise HTTPException(404, "选项不存在")
        run = await self.session.get(OsDecisionRun, option.run_id)
        if run is None:
            raise HTTPException(404, "运行不存在")
        thread = await self._get_owned(run.thread_id)
        option.feedback_score = payload.score
        option.feedback_note = payload.note
        if thread.status == "chosen":
            thread.status = "reviewed"
        await self.session.commit()
        await self.session.refresh(option)
        if payload.apply_to_prompt:
            note = (payload.note or "").strip() or "（用户未写说明，仅按评分调参）"
            snippet = (thread.question or "")[:80]
            await self.profiles.append_tuning_note(
                field="decision_prompt_appendix",
                line=(
                    f"[决策#{thread.id} · {option.tier} · 评分{payload.score}] "
                    f"{snippet} → {note}"
                ),
            )
        return OsDecisionOptionResponse.model_validate(option)


def _parse_tiers(raw: str) -> dict:
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    options = data.get("options") or []
    # normalize to 3 tiers
    by_tier = {o.get("tier"): o for o in options if isinstance(o, dict)}
    normalized = []
    for tier in _TIERS:
        o = by_tier.get(tier) or {}
        normalized.append(
            {
                "tier": tier,
                "title": o.get("title") or _TIER_LABELS[tier],
                "content": o.get("content") or "（暂无内容）",
            }
        )
    return {"summary": data.get("summary") or "", "options": normalized}


def _fallback_tiers(replies: list[tuple[int, str]]) -> dict:
    texts = [t for _, t in replies]
    while len(texts) < 3:
        texts.append("（补充：暂无更多模型回复，可基于已有信息保守决策）")
    options = []
    for tier, content in zip(_TIERS, texts[:3], strict=True):
        options.append(
            {
                "tier": tier,
                "title": _TIER_LABELS[tier],
                "content": content[:2000],
            }
        )
    return {"summary": "已按模型回复顺序映射为上中下三策（汇总解析失败时的回退）", "options": options}
