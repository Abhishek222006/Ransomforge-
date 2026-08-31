from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["processes"])


@router.get("/processes/recent")
async def recent_processes(request: Request, limit: int = Query(25, ge=1, le=100)) -> list[dict]:
    """Return recent suspicious process anomalies for dashboard refresh recovery.

    This is intentionally lightweight: it reads directly from the existing
    SQLite event store and returns the newest process anomalies first.
    """
    event_store = request.app.state.event_store
    try:
        return event_store.recent_process_events(limit=limit)
    except Exception:
        return []
