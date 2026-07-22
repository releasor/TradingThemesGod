"""大模型协议适配器的统一接口。"""

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class LLMRequest:
    url: str
    headers: dict[str, str]
    json: dict[str, Any]


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
        request = self.completion_request(
            system, user, json_mode=json_mode, reasoning=reasoning
        )
        async with httpx.AsyncClient(
            timeout=timeout_seconds or self.timeout_seconds
        ) as client:
            response = await client.post(
                request.url, headers=request.headers, json=request.json
            )
            response.raise_for_status()
            return self.parse_completion(response.json())

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
