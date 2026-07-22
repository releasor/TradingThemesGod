"""Google Gemini API 适配器。"""

from typing import Any

from app.integrations.llm.base import BaseLLMAdapter, LLMRequest


class GeminiAdapter(BaseLLMAdapter):
    def completion_request(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
    ) -> LLMRequest:
        generation_config = {
            "temperature": self.temperature,
            "maxOutputTokens": self.max_tokens,
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        return LLMRequest(
            url=(
                f"{self.base_url}/models/{self.model}:generateContent"
                f"?key={self.api_key}"
            ),
            headers={"Content-Type": "application/json", **self.custom_headers},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": generation_config,
            },
        )

    def parse_completion(self, payload: dict[str, Any]) -> str:
        parts = payload["candidates"][0]["content"]["parts"]
        return "".join(str(item.get("text", "")) for item in parts)

    def models_request(self) -> tuple[str, dict[str, str]]:
        return f"{self.base_url}/models?key={self.api_key}", self.custom_headers

    def parse_models(self, payload: dict[str, Any]) -> list[str]:
        return sorted(
            str(item["name"]).removeprefix("models/")
            for item in payload.get("models", [])
        )
