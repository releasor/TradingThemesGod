"""OpenAI-compatible 协议适配器。"""

from typing import Any
from urllib.parse import urlparse

from app.integrations.llm.base import BaseLLMAdapter, LLMRequest


class IncompleteModelResponseError(ValueError):
    """模型因输出预算耗尽而未生成完整响应。"""


class OpenAICompatibleAdapter(BaseLLMAdapter):
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.custom_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

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
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        hostname = urlparse(self.base_url).hostname or ""
        if not reasoning and (
            hostname == "api.deepseek.com" or hostname.endswith(".deepseek.com")
        ):
            payload["thinking"] = {"type": "disabled"}
        return LLMRequest(
            url=f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
        )

    def parse_completion(self, payload: dict[str, Any]) -> str:
        choice = payload["choices"][0]
        content = choice["message"].get("content")
        if choice.get("finish_reason") == "length":
            raise IncompleteModelResponseError(
                "模型达到输出 token 上限，未能生成完整 JSON；请调高最大输出"
            )
        if not isinstance(content, str) or not content.strip():
            raise ValueError("模型返回了空内容")
        return content

    def extract_reasoning(self, payload: dict[str, Any]) -> str | None:
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        for key in ("reasoning_content", "reasoning", "thinking", "reasoning_text"):
            value = message.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        # 部分兼容层把思考放在单独字段
        for key in ("reasoning", "thinking"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def models_request(self) -> tuple[str, dict[str, str]]:
        return f"{self.base_url}/models", self._headers()

    def parse_models(self, payload: dict[str, Any]) -> list[str]:
        return sorted(str(item["id"]) for item in payload.get("data", []))
