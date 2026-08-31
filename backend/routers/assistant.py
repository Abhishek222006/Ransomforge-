from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:
    from ..services import db as db_service
    from ..services.backup_manager import get_all_backups, get_db
    from ..services.llm_service import (
        append_session_turn,
        build_messages,
        get_or_create_session_id,
        get_session_history,
        request_openrouter_chat,
    )
except ImportError:
    from services import db as db_service
    from services.backup_manager import get_all_backups, get_db
    from services.llm_service import (
        append_session_turn,
        build_messages,
        get_or_create_session_id,
        get_session_history,
        request_openrouter_chat,
    )


router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantChatRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=128)
    message: str = Field(..., min_length=1, max_length=2000)
    threat_score: int = Field(default=0, ge=0, le=100)
    severity: str = Field(default="low", max_length=32)
    recent_events: list[str] = Field(default_factory=list)


def _safe_recent_event_text(event: dict[str, Any]) -> str:
    details = event.get("details", {}) or {}
    if isinstance(details, str):
        return f"{event.get('event_type', 'event')}: {details}"

    parts = [event.get("event_type", "event")]
    if event.get("path"):
        parts.append(str(event["path"]))
    if details.get("message"):
        parts.append(str(details["message"]))
    if details.get("reason"):
        parts.append(str(details["reason"]))
    if details.get("entropy") is not None:
        parts.append(f"entropy={details['entropy']}")
    return " | ".join(parts)


def _build_context(request: Request, payload: AssistantChatRequest) -> dict[str, Any]:
    quarantine_manager = getattr(request.app.state, "quarantine_manager", None)
    event_store = getattr(request.app.state, "event_store", None)

    quarantine_status = {}
    if quarantine_manager is not None:
        try:
            quarantine_status = quarantine_manager.get_quarantine_status()
        except Exception:
            quarantine_status = {}

    local_events: list[str] = []
    if event_store is not None:
        try:
            for event in event_store.recent_events(limit=5):
                local_events.append(_safe_recent_event_text(event))
        except Exception:
            pass

    if not local_events:
        try:
            for event in db_service.get_recent_events(limit=5):
                local_events.append(_safe_recent_event_text(event))
        except Exception:
            pass

    recent_alerts: list[str] = []
    try:
        with get_db() as connection:
            rows = connection.execute(
                """
                SELECT timestamp, message, severity
                FROM alerts
                ORDER BY id DESC
                LIMIT 5
                """
            ).fetchall()
        for row in rows:
            recent_alerts.append(
                f"{row['timestamp']} | severity={row['severity']} | {row['message']}"
            )
    except Exception:
        pass

    recovery_state = {
        "total_backups": 0,
        "clean_backups": 0,
        "latest_backup": None,
        "recovery_ready": False,
    }
    try:
        backups = get_all_backups()
        clean_backups = [backup for backup in backups if backup.get("status") == "clean"]
        latest_backup = backups[0] if backups else None
        recovery_state = {
            "total_backups": len(backups),
            "clean_backups": len(clean_backups),
            "latest_backup": {
                "id": latest_backup.get("id"),
                "timestamp": latest_backup.get("timestamp"),
                "status": latest_backup.get("status"),
                "restore_status": latest_backup.get("restore_status"),
            }
            if latest_backup
            else None,
            "recovery_ready": bool(clean_backups),
        }
    except Exception:
        pass

    combined_recent_events = [*payload.recent_events, *local_events]

    return {
        "threat_score": payload.threat_score,
        "severity": payload.severity,
        "quarantine_status": quarantine_status,
        "recent_events": combined_recent_events[:8],
        "recent_alerts": recent_alerts,
        "recovery_state": recovery_state,
    }


@router.post("/chat")
async def assistant_chat(request: Request, payload: AssistantChatRequest) -> Any:
    """Return a beginner-friendly incident response explanation using OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return JSONResponse(status_code=503, content={"error": "OPENROUTER_API_KEY is not configured"})

    session_id = get_or_create_session_id(payload.session_id)
    context = _build_context(request, payload)
    history = get_session_history(session_id)
    messages = build_messages(payload.message, context, history)

    try:
        reply = await request_openrouter_chat(api_key=api_key, messages=messages)
    except TimeoutError:
        return JSONResponse(status_code=504, content={"error": "OpenRouter request timed out"})
    except (ValueError, KeyError, IndexError, TypeError):
        return JSONResponse(status_code=502, content={"error": "Invalid response from OpenRouter"})
    except RuntimeError:
        return JSONResponse(status_code=502, content={"error": "OpenRouter request failed"})

    if not isinstance(reply, str) or not reply.strip():
        return JSONResponse(status_code=502, content={"error": "OpenRouter returned an empty response"})

    append_session_turn(session_id, payload.message, reply.strip())
    return {"reply": reply.strip(), "session_id": session_id}