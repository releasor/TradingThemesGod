"""Prompt 工作台 API。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.prompt_workbench import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
    DesignRequest,
    DualTestRequest,
    DualTestResult,
    IterateRequest,
    OptimizeRequest,
    OptimizeRunResponse,
    PromptItemCreate,
    PromptItemResponse,
    PromptItemUpdate,
    TextResult,
)
from app.services.prompt_chat import PromptChatService
from app.services.prompt_library import PromptLibraryService
from app.services.prompt_optimize import PromptOptimizeService

router = APIRouter(prefix="/prompt", tags=["prompt"])


def _library(db: AsyncSession, user: User) -> PromptLibraryService:
    return PromptLibraryService(db, user.id)


def _optimize(db: AsyncSession, user: User) -> PromptOptimizeService:
    return PromptOptimizeService(db, user.id)


def _chat(db: AsyncSession, user: User) -> PromptChatService:
    return PromptChatService(db, user.id)


@router.get("/items", response_model=list[PromptItemResponse])
async def list_items(
    q: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    enabled: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _library(db, current_user).list(
        q=q, category=category, tag=tag, enabled=enabled
    )


@router.post("/items", response_model=PromptItemResponse, status_code=201)
async def create_item(
    payload: PromptItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _library(db, current_user).create(payload)


@router.get("/items/{item_id}", response_model=PromptItemResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _library(db, current_user).get(item_id)


@router.put("/items/{item_id}", response_model=PromptItemResponse)
async def update_item(
    item_id: int,
    payload: PromptItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _library(db, current_user).update(item_id, payload)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _library(db, current_user).delete(item_id)


@router.post("/design", response_model=TextResult)
async def design_prompt(
    payload: DesignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _optimize(db, current_user).design(payload)


@router.post("/optimize", response_model=TextResult)
async def optimize_prompt(
    payload: OptimizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _optimize(db, current_user).optimize(payload)


def _sse_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


async def _sse_event_gen(events: AsyncIterator[dict]) -> AsyncIterator[str]:
    # 注释帧 + 填充，促使代理/浏览器立刻冲刷首包
    yield f":{' ' * 2048}\n\n"
    await asyncio.sleep(0)
    try:
        async for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
    except Exception as exc:  # noqa: BLE001
        detail = getattr(exc, "detail", None) or str(exc)
        yield f"data: {json.dumps({'type': 'error', 'message': str(detail)[:300]}, ensure_ascii=False)}\n\n"


@router.post("/optimize/stream")
async def optimize_prompt_stream(
    payload: OptimizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _optimize(db, current_user)
    return StreamingResponse(
        _sse_event_gen(service.optimize_stream(payload)),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.post("/optimize/iterate", response_model=TextResult)
async def iterate_prompt(
    payload: IterateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _optimize(db, current_user).iterate(payload)


@router.post("/optimize/iterate/stream")
async def iterate_prompt_stream(
    payload: IterateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _optimize(db, current_user)
    return StreamingResponse(
        _sse_event_gen(service.iterate_stream(payload)),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.post("/test", response_model=DualTestResult)
async def test_prompts(
    payload: DualTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _optimize(db, current_user).dual_test(payload)


@router.get("/optimize/runs/{run_id}", response_model=OptimizeRunResponse)
async def get_optimize_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _optimize(db, current_user).get_run(run_id)


@router.get("/chat/sessions", response_model=list[ChatSessionResponse])
async def list_chat_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).list_sessions()


@router.post("/chat/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_chat_session(
    payload: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).create_session(payload)


@router.patch("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: int,
    payload: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).update_session(session_id, payload)


@router.delete("/chat/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _chat(db, current_user).delete_session(session_id)


@router.get(
    "/chat/sessions/{session_id}/messages",
    response_model=list[ChatMessageResponse],
)
async def list_chat_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).list_messages(session_id)


@router.post(
    "/chat/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
)
async def send_chat_message(
    session_id: int,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).send_message(session_id, payload)
