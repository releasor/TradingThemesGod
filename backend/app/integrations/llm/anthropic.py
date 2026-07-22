"""Anthropic Messages API 适配器。"""

from typing import Any

from app.integrations.llm.base import BaseLLMAdapter, LLMRequest


class AnthropicAdapter(BaseLLMAdapter):
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": self.api_key,
            **self.custom_headers,
        }

    def completion_request(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
    ) -> LLMRequest:
        return LLMRequest(
            url=f"{self.base_url}/messages",
            headers=self._headers(),
            json={
                "model": self.model,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
        )

    def parse_completion(self, payload: dict[str, Any]) -> str:
        return "".join(str(item.get("text", "")) for item in payload.get("content", []))

    def models_request(self) -> tuple[str, dict[str, str]]:
        return f"{self.base_url}/models", self._headers()

    def parse_models(self, payload: dict[str, Any]) -> list[str]:
        return sorted(str(item["id"]) for item in payload.get("data", []))
