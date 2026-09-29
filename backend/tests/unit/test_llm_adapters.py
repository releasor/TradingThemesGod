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
async def test_connection_prefers_list_models_to_avoid_probe_filters():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="model-test",
        custom_headers={},
        timeout_seconds=120,
    )
    adapter.list_models = AsyncMock(return_value=["alpha", "beta", "gamma", "delta"])
    adapter.complete = AsyncMock()

    result = await adapter.test_connection()

    assert "连通成功" in result
    assert "alpha" in result
    adapter.list_models.assert_awaited_once()
    adapter.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_connection_falls_back_to_normal_completion_without_magic_token():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="model-test",
        custom_headers={},
        timeout_seconds=120,
        max_tokens=32,
    )
    adapter.list_models = AsyncMock(side_effect=RuntimeError("models disabled"))
    adapter.complete = AsyncMock(return_value="可以帮助梳理题材主线。注意区分事实与推断。投资有风险。")

    result = await adapter.test_connection()

    assert "题材" in result or "风险" in result
    args, kwargs = adapter.complete.await_args
    system, user = args
    assert "OK" not in system and "CONN_OK" not in system
    assert "OK" not in user and "CONN_OK" not in user
    assert len(system) >= 40
    assert len(user) >= 60
    assert kwargs["json_mode"] is False
    assert kwargs["reasoning"] is False
    assert kwargs["timeout_seconds"] == 60
    assert adapter.max_tokens == 32  # restored



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



def test_new_api_proxy_with_deepseek_model_does_not_send_thinking_extension():
    """中转站 + deepseek 模型名：勿注入官方 thinking 字段，避免 upstream 500。"""
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://gateway.example.com/v1",
        api_key="secret",
        model="deepseek-chat",
        custom_headers={},
        timeout_seconds=30,
    )

    request = adapter.completion_request(
        "你是助手", "请优化这段 Prompt：写周报", json_mode=False, reasoning=False
    )

    assert "thinking" not in request.json



def test_short_input_is_padded_to_avoid_gateway_probe_filter():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://gateway.example.com/v1",
        api_key="secret",
        model="deepseek-chat",
        custom_headers={},
        timeout_seconds=30,
        max_tokens=32,
    )

    request = adapter.completion_request(
        "你是助手",
        "写周报",
        json_mode=False,
        reasoning=False,
    )

    system = request.json["messages"][0]["content"]
    user = request.json["messages"][1]["content"]
    assert len(system) + len(user) >= 320
    assert "TradingThemesGod" in system
    assert user == "写周报"
    assert request.json["max_tokens"] >= 256


def test_long_input_is_not_padded():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://gateway.example.com/v1",
        api_key="secret",
        model="gpt-test",
        custom_headers={},
        timeout_seconds=30,
        max_tokens=512,
    )
    long_user = "请优化以下 Prompt：" + ("详细说明角色、约束与输出格式。" * 20)
    request = adapter.completion_request(
        "你是 Prompt 优化助手，只输出优化后的正文。",
        long_user,
        json_mode=False,
        reasoning=False,
    )
    system = request.json["messages"][0]["content"]
    assert "TradingThemesGod" not in system
    assert request.json["max_tokens"] == 512


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


def test_reasoner_models_force_temperature_one():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.deepseek.com",
        api_key="secret",
        model="deepseek-reasoner",
        custom_headers={},
        timeout_seconds=30,
        temperature=0.1,
    )
    request = adapter.completion_request("sys", "user", json_mode=False)
    assert request.json["temperature"] == 1.0


def test_chat_models_keep_configured_temperature():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.deepseek.com",
        api_key="secret",
        model="deepseek-chat",
        custom_headers={},
        timeout_seconds=30,
        temperature=0.1,
    )
    request = adapter.completion_request("sys", "user", json_mode=False)
    assert request.json["temperature"] == 0.1


def test_deepseek_v4_forces_temperature_one():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.deepseek.com",
        api_key="secret",
        model="deepseek-v4-pro",
        custom_headers={},
        timeout_seconds=30,
        temperature=0.2,
    )
    request = adapter.completion_request("sys", "user", json_mode=False)
    assert request.json["temperature"] == 1.0

@pytest.mark.asyncio
async def test_connection_without_model_uses_list_only():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="",
        custom_headers={},
        timeout_seconds=120,
    )
    adapter.list_models = AsyncMock(return_value=["alpha", "beta"])
    adapter.complete = AsyncMock()

    result = await adapter.test_connection()

    assert "连通成功" in result
    assert "alpha" in result
    adapter.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_connection_without_model_succeeds_on_empty_list():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="",
        custom_headers={},
        timeout_seconds=120,
    )
    adapter.list_models = AsyncMock(return_value=[])
    adapter.complete = AsyncMock()

    result = await adapter.test_connection()

    assert "连通成功" in result
    adapter.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_connection_without_model_errors_when_list_fails():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="",
        custom_headers={},
        timeout_seconds=120,
    )
    adapter.list_models = AsyncMock(side_effect=RuntimeError("models down"))
    adapter.complete = AsyncMock()

    with pytest.raises(ValueError, match="未配置模型名称"):
        await adapter.test_connection()
    adapter.complete.assert_not_awaited()

def test_official_moonshot_skips_gateway_padding():
    adapter = build_llm_adapter(
        protocol="openai_compatible",
        base_url="https://api.moonshot.cn/v1",
        api_key="secret",
        model="moonshot-v1-8k",
        custom_headers={},
        timeout_seconds=30,
    )
    request = adapter.completion_request(
        "你是助手", "清理缓存", json_mode=False, reasoning=False
    )
    system = request.json["messages"][0]["content"]
    user = request.json["messages"][1]["content"]
    assert "【工作台上下文】" not in system
    assert len(system) + len(user) < 320

