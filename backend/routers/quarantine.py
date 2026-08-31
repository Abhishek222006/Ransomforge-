from fastapi import APIRouter, Request


router = APIRouter(prefix="/quarantine", tags=["quarantine"])


@router.get("/status")
async def quarantine_status(request: Request) -> dict:
    """Return the current quarantine state for the dashboard."""
    manager = getattr(request.app.state, "quarantine_manager", None)
    status = manager.get_quarantine_status() if manager is not None else {"status": "NORMAL"}
    return {"quarantine": status}