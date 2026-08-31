from fastapi import APIRouter, Request


router = APIRouter(prefix="/operations", tags=["operations"])


@router.post("/isolate-network")
async def isolate_network(request: Request) -> dict:
    """Trigger the safe, simulated network isolation workflow for demos."""
    manager = getattr(request.app.state, "quarantine_manager", None)
    if manager is None:
        return {"ok": False, "message": "Quarantine manager unavailable"}

    event = manager.trigger_isolation(
        reason="Manual network isolation activated",
        threat_score=100,
        severity="critical",
        trigger_source="manual",
        auto_recover_seconds=30,
    )
    if event is None:
        return {"ok": True, "message": "Network already isolated", "event": None}

    return {"ok": True, "message": "Network isolation triggered", "event": event}


@router.post("/full-scan")
async def full_scan(request: Request) -> dict:
    """Start a lightweight simulated full system scan over runtime_watch only."""
    scan_service = getattr(request.app.state, "scan_service", None)
    if scan_service is None:
        return {"ok": False, "message": "Scan service unavailable"}

    result = await scan_service.start_scan()
    return result