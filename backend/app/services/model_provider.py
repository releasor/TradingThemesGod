"""模型服务配置管理与连接测试。"""

from __future__ import annotations

import json
import time

import httpx
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm.factory import build_llm_adapter
from app.models.model_provider import ModelProvider
from app.schemas.model_provider import ModelProviderResponse, ModelProviderUpsert
from app.services.secret_store import SecretStore


def model_http_error_message(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "模型响应超时，请缩短超时时间或更换可用模型"
    if not isinstance(exc, httpx.HTTPStatusError):
        return str(exc)[:300]

    response = exc.response
    detail = ""
    try:
        payload = response.json()
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        if isinstance(error, dict):
            detail = str(error.get("message", ""))
        if not detail and isinstance(payload, dict):
            detail = str(payload.get("message") or payload.get("detail") or "")
    except (ValueError, TypeError):
        detail = response.text.strip()

    message = f"模型服务返回 {response.status_code}"
    return f"{message}：{detail[:240]}" if detail else message


class ModelProviderService:
    def __init__(self, session: AsyncSession, secrets: SecretStore | None = None):
        self.session = session
        self.secrets = secrets or SecretStore()

    def _response(self, item: ModelProvider) -> ModelProviderResponse:
        headers = self._decrypt_headers(item, required=False)
        return ModelProviderResponse(
            id=item.id,
            name=item.name,
            protocol=item.protocol,
            base_url=item.base_url,
            model=item.model,
            has_api_key=bool(item.api_key_encrypted),
            custom_header_names=sorted(headers),
            timeout_seconds=item.timeout_seconds,
            temperature=float(item.temperature),
            max_tokens=item.max_tokens,
            enabled=item.enabled,
            is_default=item.is_default,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _decrypt_headers(
        self, item: ModelProvider, *, required: bool = True
    ) -> dict[str, str]:
        try:
            raw = self.secrets.decrypt(item.custom_headers_encrypted)
        except ValueError:
            if required:
                raise
            return {}
        return json.loads(raw) if raw else {}

    async def list(self) -> list[ModelProviderResponse]:
        result = await self.session.execute(
            select(ModelProvider).order_by(
                ModelProvider.is_default.desc(), ModelProvider.id
            )
        )
        return [self._response(item) for item in result.scalars()]

    async def save(
        self, payload: ModelProviderUpsert, provider_id: int | None = None
    ) -> ModelProviderResponse:
        item = (
            await self.session.get(ModelProvider, provider_id) if provider_id else None
        )
        if provider_id and item is None:
            raise HTTPException(404, "模型配置不存在")
        item = item or ModelProvider()
        if payload.is_default:
            await self.session.execute(update(ModelProvider).values(is_default=False))
        for field in (
            "name",
            "protocol",
            "model",
            "timeout_seconds",
            "temperature",
            "max_tokens",
            "enabled",
            "is_default",
        ):
            setattr(item, field, getattr(payload, field))
        item.base_url = str(payload.base_url).rstrip("/")
        if payload.api_key:
            item.api_key_encrypted = self.secrets.encrypt(payload.api_key)
        if payload.custom_headers or not provider_id:
            item.custom_headers_encrypted = self.secrets.encrypt(
                json.dumps(payload.custom_headers, ensure_ascii=False)
            )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return self._response(item)

    async def delete(self, provider_id: int) -> None:
        item = await self.session.get(ModelProvider, provider_id)
        if item is None:
            raise HTTPException(404, "模型配置不存在")
        await self.session.delete(item)
        await self.session.commit()

    async def get_default(self) -> ModelProvider:
        item = await self.session.scalar(
            select(ModelProvider).where(
                ModelProvider.enabled.is_(True), ModelProvider.is_default.is_(True)
            )
        )
        if item is None:
            raise HTTPException(409, "请先在模型设置中配置并启用默认模型")
        return item

    def adapter(self, item: ModelProvider):
        return build_llm_adapter(
            protocol=item.protocol,
            base_url=item.base_url,
            api_key=self.secrets.decrypt(item.api_key_encrypted),
            model=item.model,
            custom_headers=self._decrypt_headers(item),
            timeout_seconds=item.timeout_seconds,
            temperature=float(item.temperature),
            max_tokens=item.max_tokens,
        )

    async def test(self, provider_id: int) -> tuple[str, int]:
        item = await self.session.get(ModelProvider, provider_id)
        if item is None:
            raise HTTPException(404, "模型配置不存在")
        started = time.monotonic()
        try:
            text = await self.adapter(item).test_connection()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            detail = (
                model_http_error_message(exc)
                if isinstance(exc, httpx.HTTPError)
                else str(exc)[:300]
            )
            raise HTTPException(502, f"模型连接失败：{detail}") from exc
        return text, int((time.monotonic() - started) * 1000)

    async def list_available_models(self, provider_id: int) -> list[str]:
        item = await self.session.get(ModelProvider, provider_id)
        if item is None:
            raise HTTPException(404, "模型配置不存在")
        try:
            return await self.adapter(item).list_models()
        except httpx.HTTPError as exc:
            raise HTTPException(
                502, f"读取模型列表失败：{model_http_error_message(exc)}"
            ) from exc
