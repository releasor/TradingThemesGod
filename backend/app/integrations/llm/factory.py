"""根据配置创建模型协议适配器。"""

from app.integrations.llm.anthropic import AnthropicAdapter
from app.integrations.llm.base import BaseLLMAdapter
from app.integrations.llm.gemini import GeminiAdapter
from app.integrations.llm.ollama import OllamaAdapter
from app.integrations.llm.openai_compatible import OpenAICompatibleAdapter

ADAPTERS = {
    "openai_compatible": OpenAICompatibleAdapter,
    "anthropic": AnthropicAdapter,
    "gemini": GeminiAdapter,
    "ollama": OllamaAdapter,
}


def build_llm_adapter(protocol: str, **kwargs) -> BaseLLMAdapter:
    adapter_class = ADAPTERS.get(protocol)
    if adapter_class is None:
        raise ValueError(f"不支持的模型协议：{protocol}")
    return adapter_class(**kwargs)
