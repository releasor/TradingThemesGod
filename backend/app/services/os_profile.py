"""个人 AI OS 档案服务。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_os import OsProfile
from app.schemas.personal_os import OsProfileResponse, OsProfileUpdate
from app.services.os_defaults import (
    DEFAULT_HEALTH_BASELINE,
    DEFAULT_MEMORY_POLICY,
    DEFAULT_MODEL_PREFS,
    DEFAULT_MODULE_FLAGS,
    DEFAULT_SYSTEM_PROMPT,
)


class OsProfileService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def ensure_profile(self) -> OsProfile:
        result = await self.session.execute(
            select(OsProfile).where(OsProfile.user_id == self.user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is not None:
            return profile
        profile = OsProfile(
            user_id=self.user_id,
            display_name=None,
            goals=None,
            health_baseline=dict(DEFAULT_HEALTH_BASELINE),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            memory_policy=dict(DEFAULT_MEMORY_POLICY),
            module_flags=dict(DEFAULT_MODULE_FLAGS),
            model_prefs=dict(DEFAULT_MODEL_PREFS),
            report_prompt_appendix=None,
            decision_prompt_appendix=None,
        )
        self.session.add(profile)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            result = await self.session.execute(
                select(OsProfile).where(OsProfile.user_id == self.user_id)
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                raise
            return existing
        await self.session.refresh(profile)
        return profile

    async def get(self) -> OsProfileResponse:
        profile = await self.ensure_profile()
        return OsProfileResponse.model_validate(profile)

    async def update(self, payload: OsProfileUpdate) -> OsProfileResponse:
        profile = await self.ensure_profile()
        data = payload.model_dump(exclude_unset=True)
        for key in ("memory_policy", "module_flags", "model_prefs"):
            if key in data and data[key] is not None and hasattr(data[key], "model_dump"):
                data[key] = data[key].model_dump()
        if "system_prompt" in data and data["system_prompt"] is not None:
            data["system_prompt"] = data["system_prompt"].strip()
        for key, value in data.items():
            setattr(profile, key, value)
        await self.session.commit()
        await self.session.refresh(profile)
        return OsProfileResponse.model_validate(profile)

    async def require_module(self, name: str) -> OsProfile:
        profile = await self.ensure_profile()
        flags = profile.module_flags or {}
        if not flags.get(name, True):
            raise HTTPException(403, f"模块「{name}」已关闭，请在 OS 设置中开启")
        return profile

    async def append_tuning_note(
        self,
        *,
        field: str,
        line: str,
        max_chars: int = 4000,
    ) -> OsProfile:
        """把用户反馈追加到调参附录，供后续生成注入。"""
        if field not in ("report_prompt_appendix", "decision_prompt_appendix"):
            raise ValueError(f"unsupported tuning field: {field}")
        profile = await self.ensure_profile()
        addition = (line or "").strip()
        if not addition:
            return profile
        previous = (getattr(profile, field) or "").strip()
        merged = f"{previous}\n{addition}".strip() if previous else addition
        setattr(profile, field, merged[-max_chars:])
        await self.session.commit()
        await self.session.refresh(profile)
        return profile
