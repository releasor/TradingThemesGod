"""解析用户模型并调用 LLM。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm.base import BaseLLMAdapter
from app.integrations.llm.factory import build_llm_adapter
from app.models.model_provider import ModelProvider
from app.services.secret_store import SecretStore



def _llm_call_error_message(exc: Exception) -> str:
    raw = str(exc)
    lower = raw.lower()
    if "do_request_failed" in lower or "new_api_error" in lower or "upstream error" in lower:
        return (
            "中转站上游请求失败（do_request_failed）。常见原因："
            "渠道未启用/余额不足、模型名与渠道不匹配、或上游暂时不可用。"
            "请在中转控制台核对该模型渠道后重试。"
            f" 原始信息：{raw[:180]}"
        )
    if "short-input distillation" in lower or "heartbeat probing" in lower:
        return (
            "中转站判定输入过短（防蒸馏/心跳拦截）。"
            "请把原文写得更完整后重试；系统也会自动补足上下文。"
            f" 原始信息：{raw[:160]}"
        )
    return raw[:300]


class PromptLLMService:
    def __init__(
        self,
        session: AsyncSession,
        user_id: int,
        secrets: SecretStore | None = None,
    ):
        self.session = session
        self.user_id = user_id
        self.secrets = secrets or SecretStore()

    async def resolve_adapter(self, provider_id: int | None = None) -> BaseLLMAdapter:
        item = await self._resolve_provider(provider_id)
        return self._build_adapter(item)

    async def run_completion(
        self,
        system: str,
        user: str,
        *,
        provider_id: int | None = None,
    ) -> str:
        adapter = await self.resolve_adapter(provider_id)
        try:
            return await adapter.complete(
                system,
                user,
                json_mode=False,
                reasoning=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"模型调用失败：{_llm_call_error_message(exc)}") from exc

    async def stream_completion(
        self,
        system: str,
        user: str,
        *,
        provider_id: int | None = None,
    ):
        adapter = await self.resolve_adapter(provider_id)
        try:
            async for delta in adapter.stream_complete(
                system,
                user,
                json_mode=False,
                reasoning=False,
            ):
                yield delta
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"模型调用失败：{_llm_call_error_message(exc)}") from exc

    async def _resolve_provider(self, provider_id: int | None) -> ModelProvider:
        if provider_id is not None:
            item = await self.session.get(ModelProvider, provider_id)
            if item is None or item.user_id != self.user_id:
                raise HTTPException(404, "模型配置不存在")
            if not item.enabled:
                raise HTTPException(400, "所选模型未启用")
            return item

        result = await self.session.execute(
            select(ModelProvider).where(
                ModelProvider.user_id == self.user_id,
                ModelProvider.enabled.is_(True),
                ModelProvider.is_default.is_(True),
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            result = await self.session.execute(
                select(ModelProvider)
                .where(
                    ModelProvider.user_id == self.user_id,
                    ModelProvider.enabled.is_(True),
                )
                .order_by(ModelProvider.id)
                .limit(1)
            )
            item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(400, "请先在模型设置中配置可用模型")
        return item

    def _build_adapter(self, item: ModelProvider) -> BaseLLMAdapter:
        try:
            api_key = self.secrets.decrypt(item.api_key_encrypted)
            raw_headers = self.secrets.decrypt(item.custom_headers_encrypted)
        except ValueError as exc:
            raise HTTPException(
                409,
                str(exc) or "模型凭据无法解密，请重新保存配置",
            ) from exc
        import json

        custom_headers = json.loads(raw_headers) if raw_headers else {}
        return build_llm_adapter(
            protocol=item.protocol,
            base_url=item.base_url,
            api_key=api_key,
            model=item.model,
            custom_headers=custom_headers,
            timeout_seconds=item.timeout_seconds,
            temperature=float(item.temperature),
            max_tokens=item.max_tokens,
        )
