"""Ollama 原生协议适配器。"""

from typing import Any

from app.integrations.llm.base import BaseLLMAdapter, LLMRequest


class OllamaAdapter(BaseLLMAdapter):
    def completion_request(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
    ) -> LLMRequest:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        if json_mode:
            payload["format"] = "json"
        return LLMRequest(
            url=f"{self.base_url}/api/chat",
            headers={"Content-Type": "application/json", **self.custom_headers},
            json=payload,
        )

    def parse_completion(self, payload: dict[str, Any]) -> str:
        return str(payload["message"]["content"])

    def models_request(self) -> tuple[str, dict[str, str]]:
        return f"{self.base_url}/api/tags", self.custom_headers

    def parse_models(self, payload: dict[str, Any]) -> list[str]:
        return sorted(str(item["name"]) for item in payload.get("models", []))
