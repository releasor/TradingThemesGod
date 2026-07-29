"""Tushare 配置服务单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.tushare_settings import TushareSettingsUpdate
from app.services.tushare_settings import (
    TushareRuntime,
    TushareSettingsService,
    clear_tushare_runtime_cache,
    get_cached_tushare_runtime,
    set_cached_tushare_runtime,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_tushare_runtime_cache()
    yield
    clear_tushare_runtime_cache()


def test_cached_runtime_falls_back_to_env():
    with patch("app.services.tushare_settings.get_settings") as settings:
        settings.return_value = MagicMock(TUSHARE_ENABLED=True, TUSHARE_TOKEN="env-token")
        runtime = get_cached_tushare_runtime()
    assert runtime.enabled is True
    assert runtime.token == "env-token"
    assert runtime.from_db is False
    assert runtime.ready is True


def test_set_cache_overrides_env():
    set_cached_tushare_runtime(
        TushareRuntime(enabled=True, token="db-token", from_db=True)
    )
    runtime = get_cached_tushare_runtime()
    assert runtime.token == "db-token"
    assert runtime.from_db is True


@pytest.mark.asyncio
async def test_save_keeps_token_when_empty_payload():
    secrets = MagicMock()
    secrets.encrypt.side_effect = lambda v: f"enc:{v}"
    secrets.decrypt.side_effect = lambda v: v.replace("enc:", "", 1)

    row = MagicMock()
    row.id = 1
    row.enabled = False
    row.token_encrypted = "enc:old-token"
    row.updated_at = None

    db = AsyncMock()
    service = TushareSettingsService(db, secrets=secrets)
    service.ensure_row = AsyncMock(return_value=row)
    service.resolve_runtime = AsyncMock(
        return_value=TushareRuntime(enabled=True, token="old-token", from_db=True)
    )

    result = await service.save(
        TushareSettingsUpdate(enabled=True, token=""),
        user_id=9,
    )

    assert row.enabled is True
    assert row.token_encrypted == "enc:old-token"
    assert result.has_token is True
    secrets.encrypt.assert_not_called()


@pytest.mark.asyncio
async def test_save_encrypts_new_token():
    secrets = MagicMock()
    secrets.encrypt.side_effect = lambda v: f"enc:{v}"

    row = MagicMock()
    row.id = 1
    row.enabled = False
    row.token_encrypted = None
    row.updated_at = None

    db = AsyncMock()
    service = TushareSettingsService(db, secrets=secrets)
    service.ensure_row = AsyncMock(return_value=row)
    service.resolve_runtime = AsyncMock(
        return_value=TushareRuntime(enabled=True, token="new", from_db=True)
    )

    result = await service.save(
        TushareSettingsUpdate(enabled=True, token=" new "),
        user_id=1,
    )

    assert row.token_encrypted == "enc:new"
    assert result.has_token is True
    secrets.encrypt.assert_called_once_with("new")


@pytest.mark.asyncio
async def test_connection_succeeds_on_first_available_api():
    db = AsyncMock()
    service = TushareSettingsService(db)
    service.resolve_runtime = AsyncMock(
        return_value=TushareRuntime(enabled=True, token="tok", from_db=True)
    )

    pro = MagicMock()
    pro.concept.side_effect = RuntimeError("抱歉，您没有接口(concept)访问权限")
    pro.ths_index.return_value = MagicMock(empty=False, __len__=lambda self: 12)
    pro.dc_index.side_effect = AssertionError("should not reach")
    pro.trade_cal.side_effect = AssertionError("should not reach")
    pro.stock_basic.side_effect = AssertionError("should not reach")

    fake_ts = MagicMock()
    fake_ts.pro_api.return_value = pro

    with (
        patch("app.services.tushare_settings.get_settings") as settings,
        patch.dict("sys.modules", {"tushare": fake_ts}),
    ):
        settings.return_value = MagicMock(
            TUSHARE_API_URL="",
            TUSHARE_CONCEPT_SRC="ts",
            TUSHARE_THS_INDEX_TYPE="N",
            TUSHARE_THS_INDEX_EXCHANGE="A",
        )
        result = await service.test_connection()

    assert result.success is True
    assert "ths_index" in result.message


@pytest.mark.asyncio
async def test_connection_reports_permission_gap_clearly():
    db = AsyncMock()
    service = TushareSettingsService(db)
    service.resolve_runtime = AsyncMock(
        return_value=TushareRuntime(enabled=True, token="tok", from_db=True)
    )

    pro = MagicMock()
    deny = RuntimeError("抱歉，您没有接口访问权限，权限的具体详情访问：doc")
    pro.concept.side_effect = deny
    pro.ths_index.side_effect = deny
    pro.dc_index.side_effect = deny
    pro.trade_cal.side_effect = deny
    pro.stock_basic.side_effect = deny

    fake_ts = MagicMock()
    fake_ts.pro_api.return_value = pro

    with (
        patch("app.services.tushare_settings.get_settings") as settings,
        patch.dict("sys.modules", {"tushare": fake_ts}),
    ):
        settings.return_value = MagicMock(
            TUSHARE_API_URL="",
            TUSHARE_CONCEPT_SRC="ts",
            TUSHARE_THS_INDEX_TYPE="N",
            TUSHARE_THS_INDEX_EXCHANGE="A",
        )
        result = await service.test_connection()

    assert result.success is False
    assert "积分" in result.message or "权限" in result.message
