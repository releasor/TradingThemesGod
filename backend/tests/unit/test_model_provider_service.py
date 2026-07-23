import httpx

from app.services.model_provider import model_http_error_message
from app.services.secret_store import SecretStore


def test_secret_store_encrypts_and_round_trips(tmp_path):
    store = SecretStore(key_file=tmp_path / "model.key")
    encrypted = store.encrypt("sk-secret")

    assert encrypted != "sk-secret"
    assert store.decrypt(encrypted) == "sk-secret"
    assert "sk-secret" not in encrypted


def test_secret_store_keeps_same_key_between_instances(tmp_path):
    key_file = tmp_path / "model.key"
    first = SecretStore(key_file=key_file)
    encrypted = first.encrypt("token")

    assert SecretStore(key_file=key_file).decrypt(encrypted) == "token"


def test_secret_store_default_key_lives_under_backend_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("MODEL_SECRET_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.secret_store._DEFAULT_KEY_FILE",
        tmp_path / "backend-model.key",
    )

    store = SecretStore()
    encrypted = store.encrypt("stable")

    assert (tmp_path / "backend-model.key").exists()
    assert SecretStore().decrypt(encrypted) == "stable"


def test_list_tolerates_undecryptable_custom_headers(tmp_path):
    from types import SimpleNamespace
    from datetime import datetime, timezone

    from app.services.model_provider import ModelProviderService

    other = SecretStore(key_file=tmp_path / "other.key")
    current = SecretStore(key_file=tmp_path / "current.key")
    item = SimpleNamespace(
        id=1,
        user_id=1,
        name="broken-headers",
        protocol="openai_compatible",
        base_url="https://example.com",
        model="demo",
        api_key_encrypted="",
        custom_headers_encrypted=other.encrypt('{"X-Demo":"1"}'),
        timeout_seconds=60,
        temperature=0.1,
        max_tokens=1024,
        enabled=True,
        is_default=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    response = ModelProviderService(session=None, user_id=1, secrets=current)._response(item)

    assert response.custom_header_names == []
    assert response.has_api_key is False


def test_model_http_error_message_includes_provider_detail():
    request = httpx.Request(
        "POST",
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": "Bearer sk-secret"},
    )
    response = httpx.Response(
        400,
        request=request,
        json={
            "error": {
                "message": "response_format requires the word json in the prompt",
                "type": "invalid_request_error",
            }
        },
    )
    error = httpx.HTTPStatusError("400 Bad Request", request=request, response=response)

    message = model_http_error_message(error)

    assert message == (
        "模型服务返回 400：response_format requires the word json in the prompt"
    )
    assert "sk-secret" not in message


def test_model_http_error_message_explains_timeout():
    error = httpx.ReadTimeout(
        "", request=httpx.Request("POST", "https://api.example.com/chat/completions")
    )

    assert model_http_error_message(error) == (
        "模型响应超时，请缩短超时时间或更换可用模型"
    )
