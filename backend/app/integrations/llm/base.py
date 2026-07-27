"""大模型协议适配器的统一接口。"""

from dataclasses import dataclass
from typing import Any
import json

import httpx


@dataclass(slots=True)
class LLMRequest:
    url: str
    headers: dict[str, str]
    json: dict[str, Any]


@dataclass(slots=True)
class LLMCompletionResult:
    """模型完成结果，附带思考过程与原始响应预览，便于排障。"""

    content: str
    reasoning: str | None = None
    raw_preview: str | None = None


class BaseLLMAdapter:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        custom_headers: dict[str, str],
        timeout_seconds: int,
        temperature: float = 0.1,
        max_tokens: int = 8192,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.custom_headers = custom_headers
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens

    def completion_request(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
    ) -> LLMRequest:
        raise NotImplementedError

    def parse_completion(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError

    def extract_reasoning(self, payload: dict[str, Any]) -> str | None:
        """从厂商响应中尽量提取思考/推理文本。"""
        return None

    def models_request(self) -> tuple[str, dict[str, str]]:
        raise NotImplementedError

    def parse_models(self, payload: dict[str, Any]) -> list[str]:
        raise NotImplementedError

    async def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
        timeout_seconds: int | None = None,
    ) -> str:
        result = await self.complete_detailed(
            system,
            user,
            json_mode=json_mode,
            reasoning=reasoning,
            timeout_seconds=timeout_seconds,
        )
        return result.content

    async def complete_detailed(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
        timeout_seconds: int | None = None,
    ) -> LLMCompletionResult:
        request = self.completion_request(
            system, user, json_mode=json_mode, reasoning=reasoning
        )
        async with httpx.AsyncClient(
            timeout=timeout_seconds or self.timeout_seconds
        ) as client:
            response = await client.post(
                request.url, headers=request.headers, json=request.json
            )
            raw_preview = response.text[:12000]
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(
                    f"模型 HTTP {exc.response.status_code}: {raw_preview[:2000]}"
                ) from exc
            payload = response.json()
            return LLMCompletionResult(
                content=self.parse_completion(payload),
                reasoning=self.extract_reasoning(payload),
                raw_preview=json.dumps(payload, ensure_ascii=False)[:12000],
            )

    async def list_models(self) -> list[str]:
        url, headers = self.models_request()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return self.parse_models(response.json())

    async def test_connection(self) -> str:
        return await self.complete(
            "只返回 OK，不要输出其他内容。",
            "测试模型服务连接。",
            json_mode=False,
            reasoning=False,
            timeout_seconds=min(self.timeout_seconds, 30),
        )
