from fastapi import APIRouter, Query

try:
    from ..services import db as db_service
except ImportError:
    from services import db as db_service

router = APIRouter(tags=["events"])


@router.get("/events/recent")
async def recent_events(limit: int = Query(25, ge=1, le=100)) -> dict:
    """Return the latest live monitoring events for the frontend dashboard.

    This is intentionally lightweight and uses the small sqlite helper so the
    dashboard can poll recent activity without any extra dependencies.
    """
    return {"events": db_service.get_recent_events(limit=limit)}
