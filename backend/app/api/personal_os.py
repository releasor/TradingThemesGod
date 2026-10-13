"""个人 AI OS API。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.personal_os import (
    OsChatMessageCreate,
    OsChatMessageResponse,
    OsChatSessionCreate,
    OsChatSessionResponse,
    OsChatSessionUpdate,
    OsDailyReportResponse,
    OsDecisionChooseRequest,
    OsDecisionCreate,
    OsDecisionOptionFeedback,
    OsDecisionOptionResponse,
    OsDecisionRunRequest,
    OsDecisionThreadResponse,
    OsJournalCreate,
    OsJournalResponse,
    OsJournalUpdate,
    OsNoteCreate,
    OsNoteResponse,
    OsNoteUpdate,
    OsProfileResponse,
    OsProfileUpdate,
    OsReportFeedbackRequest,
    OsReportGenerateRequest,
    OsDashboardOverview,
    OsDashboardPinCreate,
    OsDashboardPinResponse,
    OsDashboardPinUpdate,
    OsScoutTemplate,
)
from app.services.os_chat import OsChatService
from app.services.os_dashboard import OsDashboardService
from app.services.os_decisions import OsDecisionsService
from app.services.os_defaults import SCOUT_TEMPLATES
from app.services.os_export import OsExportService
from app.services.os_journal import OsJournalService
from app.services.os_notes import OsNotesService
from app.services.os_profile import OsProfileService
from app.services.os_reports import OsReportsService

router = APIRouter(prefix="/os", tags=["personal-os"])


def _profile(db: AsyncSession, user: User) -> OsProfileService:
    return OsProfileService(db, user.id)


def _notes(db: AsyncSession, user: User) -> OsNotesService:
    return OsNotesService(db, user.id)


def _chat(db: AsyncSession, user: User) -> OsChatService:
    return OsChatService(db, user.id)


def _journal(db: AsyncSession, user: User) -> OsJournalService:
    return OsJournalService(db, user.id)


def _reports(db: AsyncSession, user: User) -> OsReportsService:
    return OsReportsService(db, user.id)


def _decisions(db: AsyncSession, user: User) -> OsDecisionsService:
    return OsDecisionsService(db, user.id)


def _dashboard(db: AsyncSession, user: User) -> OsDashboardService:
    return OsDashboardService(db, user.id)


def _sse_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


async def _sse_event_gen(events: AsyncIterator[dict]) -> AsyncIterator[str]:
    yield f":{' ' * 2048}\n\n"
    await asyncio.sleep(0)
    try:
        async for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
    except Exception as exc:  # noqa: BLE001
        detail = getattr(exc, "detail", None) or str(exc)
        yield f"data: {json.dumps({'type': 'error', 'message': str(detail)[:300]}, ensure_ascii=False)}\n\n"


# —— Profile ——


@router.get("/profile", response_model=OsProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _profile(db, current_user).get()


@router.patch("/profile", response_model=OsProfileResponse)
async def update_profile(
    payload: OsProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _profile(db, current_user).update(payload)


@router.get("/export")
async def export_os_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出档案/笔记/日志/日报/决策为 Markdown ZIP（可迁移数据资产）。"""
    data = await OsExportService(db, current_user.id).build_zip()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"personal-ai-os-{stamp}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/decision-templates", response_model=list[OsScoutTemplate])
async def list_decision_templates(
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return [OsScoutTemplate.model_validate(t) for t in SCOUT_TEMPLATES]


# —— Dashboard ——


@router.get("/dashboard", response_model=OsDashboardOverview)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _dashboard(db, current_user).overview()


@router.get("/dashboard/pins", response_model=list[OsDashboardPinResponse])
async def list_dashboard_pins(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _dashboard(db, current_user).list_pins()


@router.post("/dashboard/pins", response_model=OsDashboardPinResponse, status_code=201)
async def create_dashboard_pin(
    payload: OsDashboardPinCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _dashboard(db, current_user).pin(payload)


@router.patch("/dashboard/pins/{pin_id}", response_model=OsDashboardPinResponse)
async def update_dashboard_pin(
    pin_id: int,
    payload: OsDashboardPinUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _dashboard(db, current_user).update_pin(pin_id, payload)


@router.delete("/dashboard/pins/{pin_id}", status_code=204)
async def delete_dashboard_pin(
    pin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _dashboard(db, current_user).unpin(pin_id)


@router.delete(
    "/dashboard/pins/by-source/{source_type}/{source_id}",
    status_code=204,
)
async def delete_dashboard_pin_by_source(
    source_type: str,
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _dashboard(db, current_user).unpin_by_source(source_type, source_id)


# —— Notes ——


@router.get("/notes", response_model=list[OsNoteResponse])
async def list_notes(
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _notes(db, current_user).list(q=q, limit=limit)


@router.post("/notes", response_model=OsNoteResponse, status_code=201)
async def create_note(
    payload: OsNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _notes(db, current_user).create(payload)


@router.patch("/notes/{note_id}", response_model=OsNoteResponse)
async def update_note(
    note_id: int,
    payload: OsNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _notes(db, current_user).update(note_id, payload)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _notes(db, current_user).delete(note_id)


# —— Chat ——


@router.get("/chat/sessions", response_model=list[OsChatSessionResponse])
async def list_chat_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).list_sessions()


@router.post("/chat/sessions", response_model=OsChatSessionResponse, status_code=201)
async def create_chat_session(
    payload: OsChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).create_session(payload)


@router.patch("/chat/sessions/{session_id}", response_model=OsChatSessionResponse)
async def update_chat_session(
    session_id: int,
    payload: OsChatSessionUpdate,
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
    response_model=list[OsChatMessageResponse],
)
async def list_chat_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).list_messages(session_id)


@router.post(
    "/chat/sessions/{session_id}/messages",
    response_model=OsChatMessageResponse,
)
async def send_chat_message(
    session_id: int,
    payload: OsChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _chat(db, current_user).send_message(session_id, payload)


@router.post("/chat/sessions/{session_id}/messages/stream")
async def send_chat_message_stream(
    session_id: int,
    payload: OsChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _chat(db, current_user)
    return StreamingResponse(
        _sse_event_gen(service.send_message_stream(session_id, payload)),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


# —— Journal ——


@router.get("/journal", response_model=list[OsJournalResponse])
async def list_journal(
    kind: str | None = None,
    day: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _journal(db, current_user).list(kind=kind, day=day, limit=limit)


@router.post("/journal", response_model=OsJournalResponse, status_code=201)
async def create_journal(
    payload: OsJournalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _journal(db, current_user).create(payload)


@router.patch("/journal/{entry_id}", response_model=OsJournalResponse)
async def update_journal(
    entry_id: int,
    payload: OsJournalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _journal(db, current_user).update(entry_id, payload)


@router.delete("/journal/{entry_id}", status_code=204)
async def delete_journal(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _journal(db, current_user).delete(entry_id)


# —— Reports ——


@router.get("/reports", response_model=list[OsDailyReportResponse])
async def list_reports(
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _reports(db, current_user).list(limit=limit)


@router.get("/reports/{report_id}", response_model=OsDailyReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _reports(db, current_user).get(report_id)


@router.post("/reports/generate", response_model=OsDailyReportResponse)
async def generate_report(
    payload: OsReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _reports(db, current_user).generate(payload)


@router.post("/reports/generate/stream")
async def generate_report_stream(
    payload: OsReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _reports(db, current_user)
    return StreamingResponse(
        _sse_event_gen(service.generate_stream(payload)),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.post("/reports/{report_id}/feedback", response_model=OsDailyReportResponse)
async def report_feedback(
    report_id: int,
    payload: OsReportFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _reports(db, current_user).feedback(report_id, payload)


# —— Decisions ——


@router.get("/decisions", response_model=list[OsDecisionThreadResponse])
async def list_decisions(
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _decisions(db, current_user).list_threads(limit=limit)


@router.post("/decisions", response_model=OsDecisionThreadResponse, status_code=201)
async def create_decision(
    payload: OsDecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _decisions(db, current_user).create(payload)


@router.get("/decisions/{thread_id}", response_model=OsDecisionThreadResponse)
async def get_decision(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _decisions(db, current_user).get(thread_id)


@router.post(
    "/decisions/{thread_id}/run", response_model=OsDecisionThreadResponse
)
async def run_decision(
    thread_id: int,
    payload: OsDecisionRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _decisions(db, current_user).run(thread_id, payload)


@router.post(
    "/decisions/{thread_id}/choose", response_model=OsDecisionThreadResponse
)
async def choose_decision(
    thread_id: int,
    payload: OsDecisionChooseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _decisions(db, current_user).choose(thread_id, payload)


@router.post(
    "/decisions/options/{option_id}/feedback",
    response_model=OsDecisionOptionResponse,
)
async def decision_option_feedback(
    option_id: int,
    payload: OsDecisionOptionFeedback,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _decisions(db, current_user).option_feedback(option_id, payload)
