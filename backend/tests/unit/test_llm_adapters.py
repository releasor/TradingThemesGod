from unittest.mock import AsyncMock

import pytest

from app.integrations.llm.factory import build_llm_adapter
from app.integrations.llm.openai_compatible import IncompleteModelResponseError


def test_openai_compatible_builds_expected_request():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="http://localhost:15721/v1",
        api_key="secret",
        model="gpt-test",
        custom_headers={"X-Route": "local"},
        timeout_seconds=30,
    )

    request = adapter.completion_request("system", "user")

    assert request.url == "http://localhost:15721/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret"
    assert request.headers["X-Route"] == "local"
    assert request.json["model"] == "gpt-test"
    assert request.json["response_format"] == {"type": "json_object"}


def test_openai_compatible_can_build_plain_text_request_for_connection_test():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.deepseek.com",
        api_key="secret",
        model="deepseek-chat",
        custom_headers={},
        timeout_seconds=30,
    )

    request = adapter.completion_request("只返回 OK", "测试连接", json_mode=False)

    assert request.url == "https://api.deepseek.com/chat/completions"
    assert "response_format" not in request.json


@pytest.mark.asyncio
async def test_connection_uses_short_timeout_and_disables_reasoning():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="model-test",
        custom_headers={},
        timeout_seconds=120,
    )
    adapter.complete = AsyncMock(return_value="OK")

    result = await adapter.test_connection()

    assert result == "OK"
    adapter.complete.assert_awaited_once_with(
        "只返回 OK，不要输出其他内容。",
        "测试模型服务连接。",
        json_mode=False,
        reasoning=False,
        timeout_seconds=30,
    )


def test_openai_compatible_reports_token_limit_instead_of_empty_json():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.deepseek.com",
        api_key="secret",
        model="deepseek-v4-pro",
        custom_headers={},
        timeout_seconds=30,
    )

    with pytest.raises(IncompleteModelResponseError, match="输出 token 上限"):
        adapter.parse_completion(
            {
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": "", "reasoning_content": "分析过程"},
                    }
                ]
            }
        )


def test_deepseek_can_disable_reasoning_for_structured_output():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.deepseek.com",
        api_key="secret",
        model="deepseek-v4-pro",
        custom_headers={},
        timeout_seconds=30,
    )

    request = adapter.completion_request("Return JSON", "Build graph", reasoning=False)

    assert request.json["thinking"] == {"type": "disabled"}


def test_non_deepseek_openai_request_does_not_send_thinking_extension():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="secret",
        model="gpt-test",
        custom_headers={},
        timeout_seconds=30,
    )

    request = adapter.completion_request("Return JSON", "Build graph", reasoning=False)

    assert "thinking" not in request.json


def test_ollama_uses_native_generate_endpoint():
    adapter = build_llm_adapter(
        protocol="ollama",
        base_url="http://localhost:11434",
        api_key="",
        model="qwen3",
        custom_headers={},
        timeout_seconds=30,
    )

    request = adapter.completion_request("system", "user")

    assert request.url == "http://localhost:11434/api/chat"
    assert request.json["stream"] is False
