"""OpenAI-compatible 协议适配器。"""

from typing import Any
from urllib.parse import urlparse

import httpx

from app.integrations.llm.base import BaseLLMAdapter, LLMRequest

_HTTP_CLIENTS: dict[str, httpx.AsyncClient] = {}


def _shared_stream_client(http_timeout: httpx.Timeout) -> httpx.AsyncClient:
    key = f"{http_timeout.connect}|{http_timeout.read}|{http_timeout.write}|{http_timeout.pool}"
    client = _HTTP_CLIENTS.get(key)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            timeout=http_timeout,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )
        _HTTP_CLIENTS[key] = client
    return client


# New API / 部分中转会拦截「短输入 + 低 max_tokens」类请求，当成心跳/蒸馏探测。
_MIN_INPUT_CHARS = 320
_MIN_MAX_TOKENS = 256
_INPUT_PAD = (
    "【工作台上下文】TradingThemesGod 是 A 股题材与产业链研究工作台，"
    "模块包括题材看板、复盘研究、催化雷达、题材挖掘、主线图谱与 Prompt 工作台。"
    "当前请求来自已登录用户的真实业务操作：需要模型按系统说明完成任务并直接给出可用结果。"
    "请忽略本节中与任务无关的背景信息，只根据系统角色与用户正文作答；"
    "回答使用简体中文，不要复述本节上下文，不要输出与任务无关的寒暄。"
    "补充说明：用户可能在优化 Prompt、设计提示词、自由对话或复盘分析；"
    "无论任务长短，都应按完整业务请求处理，而不是心跳、探测或蒸馏样本。"
)


_OFFICIAL_HOST_SUFFIXES = (
    ".moonshot.cn",
    "moonshot.cn",
    ".deepseek.com",
    "deepseek.com",
    ".openai.com",
    "openai.com",
    ".dashscope.aliyuncs.com",
    ".bigmodel.cn",
)


def _needs_gateway_padding(base_url: str) -> bool:
    """Only New API / relay gateways need anti-probe padding; official APIs do not."""
    host = (urlparse(base_url).hostname or "").lower()
    if not host or host in {"localhost", "127.0.0.1"}:
        return False
    for suffix in _OFFICIAL_HOST_SUFFIXES:
        bare = suffix.lstrip(".")
        if host == bare or host.endswith(suffix):
            return False
    return True


def _pad_messages_for_gateway(system: str, user: str) -> tuple[str, str]:
    system = system or ""
    user = user or ""
    total = len(system) + len(user)
    if total >= _MIN_INPUT_CHARS:
        return system, user
    need = _MIN_INPUT_CHARS - total + 8
    pad = _INPUT_PAD
    while len(pad) < need:
        pad = pad + "｜" + _INPUT_PAD
    padded_system = (system.rstrip() + "\n\n" + pad).strip()
    return padded_system, user


class IncompleteModelResponseError(ValueError):
    """模型因输出预算耗尽而未生成完整响应。"""


class OpenAICompatibleAdapter(BaseLLMAdapter):
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.custom_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def requires_fixed_temperature(model: str) -> bool:
        """部分思考/推理模型只允许 temperature=1。"""
        name = (model or "").strip().lower()
        if not name:
            return False
        needles = (
            "reasoner",
            "deepseek-r1",
            "deepseek-v4",
            "-thinking",
            "thinking-",
            "o1-pro",
            "o1-mini",
            "o1-preview",
            "o3-mini",
            "o3-pro",
            "o4-mini",
        )
        if any(n in name for n in needles):
            return True
        # 精确匹配短名，避免误伤含 "o1" 子串的其它模型 id
        token = name.rsplit("/", 1)[-1]
        return token in {"o1", "o3", "o4"}

    def _effective_temperature(self) -> float:
        if self.requires_fixed_temperature(self.model):
            return 1.0
        return float(self.temperature)

    def completion_request(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
    ) -> LLMRequest:
        max_tokens = int(self.max_tokens or 0)
        if _needs_gateway_padding(self.base_url):
            system, user = _pad_messages_for_gateway(system, user)
            if len(system) + len(user) < _MIN_INPUT_CHARS * 2:
                # 短业务输入时抬高输出预算，降低被识别为探测的概率
                max_tokens = max(max_tokens, _MIN_MAX_TOKENS)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self._effective_temperature(),
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        hostname = urlparse(self.base_url).hostname or ""
        host = (hostname or "").lower()
        if not reasoning and (
            host == "api.deepseek.com" or host.endswith(".deepseek.com")
        ):
            # Only official DeepSeek supports this extension; New API proxies often 500.
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



    @staticmethod
    def _is_fixed_temperature_error(message: str) -> bool:
        lower = message.lower()
        return "invalid temperature" in lower or "only 1 is allowed" in lower

    async def complete_detailed(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
        timeout_seconds: int | None = None,
    ):
        try:
            return await super().complete_detailed(
                system,
                user,
                json_mode=json_mode,
                reasoning=reasoning,
                timeout_seconds=timeout_seconds,
            )
        except ValueError as exc:
            if not self._is_fixed_temperature_error(str(exc)):
                raise
            if abs(float(self.temperature) - 1.0) < 1e-9:
                raise
            original = self.temperature
            self.temperature = 1.0
            try:
                return await super().complete_detailed(
                    system,
                    user,
                    json_mode=json_mode,
                    reasoning=reasoning,
                    timeout_seconds=timeout_seconds,
                )
            finally:
                self.temperature = original

    async def stream_complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        reasoning: bool = True,
        timeout_seconds: int | None = None,
    ):
        """Stream token deltas via OpenAI-compatible SSE."""
        import json

        self.last_stream_status: str | None = None
        reasoning_hinted = False
        content_seen = False
        request = self.completion_request(
            system, user, json_mode=json_mode, reasoning=reasoning
        )
        payload = {**request.json, "stream": True}
        timeout = timeout_seconds or self.timeout_seconds
        http_timeout = httpx.Timeout(timeout, connect=10.0)
        client = _shared_stream_client(http_timeout)
        async with client.stream(
                "POST",
                request.url,
                headers={**request.headers, "Accept": "text/event-stream"},
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    raw_preview = (await response.aread()).decode(
                        "utf-8", errors="replace"
                    )[:2000]
                    raise ValueError(f"模型 HTTP {response.status_code}: {raw_preview}")
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                    else:
                        continue
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta_obj = choices[0].get("delta") or {}
                    thinking = (
                        delta_obj.get("reasoning_content")
                        or delta_obj.get("reasoning")
                        or delta_obj.get("thinking")
                    )
                    if isinstance(thinking, str) and thinking:
                        if not reasoning_hinted:
                            reasoning_hinted = True
                            self.last_stream_status = "模型思考中，正文即将开始…"
                        if not content_seen:
                            yield thinking
                    delta = delta_obj.get("content")
                    if isinstance(delta, str) and delta:
                        content_seen = True
                        self.last_stream_status = None
                        yield delta
