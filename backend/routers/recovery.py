from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

try:
    from ..services.backup_manager import (
        create_snapshot,
        get_all_backups,
        get_last_clean_backup,
        get_recovery_logs,
        restore_from_backup,
        record_restore_failure,
    )
    from ..services.reporter import generate_incident_report
except ImportError:
    from services.backup_manager import (
        create_snapshot,
        get_all_backups,
        get_last_clean_backup,
        get_recovery_logs,
        restore_from_backup,
        record_restore_failure,
    )
    from services.reporter import generate_incident_report


router = APIRouter(prefix="/api/recovery", tags=["recovery"])


def _normalize_backup(backup: dict | None) -> dict | None:
    if not backup:
        return None

    normalized = dict(backup)
    normalized["id"] = int(normalized.get("id") or 0)
    normalized["timestamp"] = normalized.get("timestamp") or datetime.now(timezone.utc).isoformat()
    normalized["directory"] = str(normalized.get("directory") or "")
    normalized["snapshot_path"] = str(normalized.get("snapshot_path") or "")
    normalized["file_count"] = int(normalized.get("file_count") or 0)
    normalized["size_bytes"] = int(normalized.get("size_bytes") or 0)
    normalized["status"] = normalized.get("status") or "unknown"
    normalized["snapshot_status"] = normalized.get("snapshot_status") or normalized["status"]
    normalized["restore_status"] = normalized.get("restore_status") or None
    normalized["restore_timestamp"] = normalized.get("restore_timestamp") or None
    return normalized


def _normalize_restore_result(result: dict | None) -> dict:
    if not result:
        return {"success": False, "error": "Restore returned no result"}
    if result.get("success") is False:
        return {"success": False, "error": result.get("error") or "Restore failed"}
    return {
        "success": True,
        "message": result.get("message") or "Snapshot restored successfully",
    }


def _recovery_payload(event_type: str, message: str, **extra: object) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    data = {"message": message, "timestamp": timestamp, **extra}
    return {"type": event_type, "data": data, "payload": data}


async def _broadcast(request: Request, payload: dict) -> None:
    websocket_manager = getattr(request.app.state, "websocket_manager", None)
    if websocket_manager is None:
        return
    try:
        websocket_manager.broadcast(payload)
    except Exception:
        pass


async def _broadcast_async(request: Request, payload: dict) -> None:
    await _broadcast(request, payload)


def _count_runtime_assets() -> int:
    try:
        from ..services.backup_manager import MONITORED_DIR
    except ImportError:
        from services.backup_manager import MONITORED_DIR

    if not MONITORED_DIR.exists():
        return 0

    return sum(1 for path in MONITORED_DIR.rglob("*") if path.is_file())


def _count_snapshot_files() -> int:
    try:
        from ..services.backup_manager import BACKUP_ROOT
    except ImportError:
        from services.backup_manager import BACKUP_ROOT

    if not BACKUP_ROOT.exists():
        return 0

    return sum(1 for path in BACKUP_ROOT.rglob("*") if path.is_file())


def _get_status_counts(backups: list[dict]) -> tuple[int, int]:
    successful = 0
    failed = 0
    for backup in backups:
        if backup.get("restore_status") == "success":
            successful += 1
        elif backup.get("restore_status") == "failed":
            failed += 1
    return successful, failed


def _restore_error_status(message: str) -> int:
    text = (message or "").lower()
    if "not found" in text or "missing or invalid" in text:
        return 404
    if "invalid snapshot metadata" in text or "invalid backup" in text:
        return 400
    if "already running" in text or "operation already running" in text:
        return 409
    if "permission denied" in text or "locked" in text:
        return 423
    if "timed out" in text:
        return 504
    return 503


@router.get("/backups")
async def list_backups() -> dict:
    """Return all versioned backups for the recovery timeline."""
    backups = [_normalize_backup(backup) for backup in get_all_backups()]
    return {"backups": backups}


@router.get("/stats")
async def recovery_stats() -> dict:
    """Return live recovery statistics from SQLite and the snapshot folders."""
    backups = [_normalize_backup(backup) for backup in get_all_backups()]
    clean_backups = [backup for backup in backups if backup and backup.get("status") == "clean"]
    latest_backup = backups[0] if backups else None
    successful_restores, failed_restores = _get_status_counts([backup for backup in backups if backup])
    total_snapshots = len(backups)
    total_assets = _count_runtime_assets()
    snapshot_files = _count_snapshot_files()

    if total_snapshots == 0:
        backup_health = 0.0
    else:
        clean_ratio = (len(clean_backups) / total_snapshots) * 100
        restore_score = min(30.0, successful_restores * 10.0)
        failure_penalty = min(25.0, failed_restores * 12.5)
        filesystem_bonus = 10.0 if snapshot_files > 0 else 0.0
        backup_health = round(max(0.0, min(100.0, clean_ratio * 0.55 + restore_score + filesystem_bonus - failure_penalty)), 1)

    immunity_state = "ACTIVE" if clean_backups and latest_backup else "INACTIVE"

    return {
        "backup_health": backup_health,
        "last_snapshot": latest_backup["timestamp"] if latest_backup else None,
        "total_assets": total_assets,
        "total_snapshots": total_snapshots,
        "successful_restores": successful_restores,
        "failed_restores": failed_restores,
        "ransomware_immunity": immunity_state,
    }


@router.post("/backup/create")
async def backup_create(request: Request) -> dict:
    """Create a new clean snapshot of the monitored runtime folder."""
    try:
        backup = await asyncio.to_thread(create_snapshot, "clean")
        backup = _normalize_backup(backup)
        await _broadcast_async(request, _recovery_payload("RECOVERY_CREATED", "Snapshot created successfully", backup=backup))
        return {"success": True, "backup": backup}
    except Exception as exc:
        try:
            await _broadcast_async(request, _recovery_payload("RECOVERY_FAILED", "Snapshot creation failed", error=str(exc)))
        except Exception:
            pass
        return JSONResponse(
            status_code=_restore_error_status(str(exc)),
            content={"success": False, "error": str(exc)},
        )


@router.post("/restore/latest")
async def restore_latest(request: Request) -> dict:
    """Restore the newest clean snapshot."""
    backup = get_last_clean_backup()
    if not backup:
        raise HTTPException(status_code=404, detail="No clean backup available")

    try:
        result = await asyncio.to_thread(restore_from_backup, int(backup["id"]))
        normalized = _normalize_restore_result(result)
        if normalized["success"]:
            await _broadcast_async(request, _recovery_payload("RECOVERY_RESTORED", "Latest clean snapshot restored", backup_id=int(backup["id"]), result=result))
            return normalized

        await _broadcast_async(request, _recovery_payload("RECOVERY_FAILED", "Latest snapshot restore failed", backup_id=int(backup["id"]), error=normalized["error"]))
        return JSONResponse(status_code=_restore_error_status(normalized["error"]), content=normalized)
    except Exception as exc:
        record_restore_failure(int(backup["id"]), str(exc), {"backup_id": int(backup["id"]), "mode": "latest"})
        await _broadcast_async(request, _recovery_payload("RECOVERY_FAILED", "Latest snapshot restore failed", backup_id=int(backup["id"]), error=str(exc)))
        return JSONResponse(status_code=_restore_error_status(str(exc)), content={"success": False, "error": str(exc)})


@router.post("/restore/{backup_id}")
async def restore_backup(backup_id: int, request: Request) -> dict:
    """Restore the monitored folder from a selected backup snapshot."""
    try:
        result = await asyncio.to_thread(restore_from_backup, backup_id)
        normalized = _normalize_restore_result(result)
        if normalized["success"]:
            await _broadcast_async(request, _recovery_payload("RECOVERY_RESTORED", "Snapshot restored successfully", backup_id=backup_id, result=result))
            return normalized

        await _broadcast_async(request, _recovery_payload("RECOVERY_FAILED", "Snapshot restore failed", backup_id=backup_id, error=normalized["error"]))
        return JSONResponse(status_code=_restore_error_status(normalized["error"]), content=normalized)
    except HTTPException:
        raise
    except Exception as exc:
        record_restore_failure(backup_id, str(exc), {"backup_id": backup_id})
        await _broadcast_async(request, _recovery_payload("RECOVERY_FAILED", "Snapshot restore failed", backup_id=backup_id, error=str(exc)))
        return JSONResponse(status_code=_restore_error_status(str(exc)), content={"success": False, "error": str(exc)})


@router.post("/emergency-boot")
async def emergency_boot(request: Request) -> dict:
    """Simulate an emergency recovery flow by restoring the latest snapshot and resetting risk."""
    backup = get_last_clean_backup()
    if not backup:
        raise HTTPException(status_code=404, detail="No clean backup available for emergency recovery")

    try:
        result = await asyncio.to_thread(restore_from_backup, int(backup["id"]))
        normalized = _normalize_restore_result(result)
        websocket_manager = getattr(request.app.state, "websocket_manager", None)
        if websocket_manager is not None:
            try:
                websocket_manager.broadcast({
                    "type": "THREAT_UPDATE",
                    "score": 0,
                    "severity": "low",
                    "data": {"score": 0, "severity": "low"},
                    "payload": {"score": 0, "severity": "low"},
                })
                websocket_manager.broadcast({
                    "type": "ALERT",
                    "data": {
                        "title": "Emergency Recovery Activated",
                        "description": "The latest clean snapshot was restored and containment state has been reset.",
                        "severity": "critical",
                        "score": 100,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "time": datetime.now(timezone.utc).isoformat(),
                    },
                    "payload": {
                        "title": "Emergency Recovery Activated",
                        "description": "The latest clean snapshot was restored and containment state has been reset.",
                        "severity": "critical",
                        "score": 100,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "time": datetime.now(timezone.utc).isoformat(),
                    },
                })
                if normalized["success"]:
                    websocket_manager.broadcast(_recovery_payload("RECOVERY_RESTORED", "Emergency recovery boot completed", backup_id=int(backup["id"]), result=result))
                else:
                    websocket_manager.broadcast(_recovery_payload("RECOVERY_FAILED", "Emergency recovery boot failed", backup_id=int(backup["id"]), error=normalized["error"]))
            except Exception:
                pass

        quarantine_manager = getattr(request.app.state, "quarantine_manager", None)
        if quarantine_manager is not None:
            try:
                quarantine_manager.disable_quarantine(reason="Emergency recovery boot completed")
            except Exception:
                pass

        if normalized["success"]:
            return {"success": True, "message": "Emergency recovery completed"}
        return JSONResponse(status_code=_restore_error_status(normalized["error"]), content=normalized)
    except Exception as exc:
        record_restore_failure(int(backup["id"]), str(exc), {"backup_id": int(backup["id"]), "mode": "emergency"})
        await _broadcast_async(request, _recovery_payload("RECOVERY_FAILED", "Emergency recovery boot failed", backup_id=int(backup["id"]), error=str(exc)))
        return JSONResponse(status_code=_restore_error_status(str(exc)), content={"success": False, "error": str(exc)})


@router.get("/logs")
async def recovery_logs() -> dict:
    """Return recovery event logs for the recovery center timeline."""
    return {"logs": get_recovery_logs()}


@router.get("/last-clean")
async def last_clean_backup() -> dict:
    """Return the latest clean backup snapshot for one-click recovery."""
    return {"backup": _normalize_backup(get_last_clean_backup())}


@router.post("/report/generate", response_model=None)
async def generate_report(request: Request, download: bool = False) -> object:
    """Generate a PDF incident report for the current ransomware workflow."""
    try:
        print("[report] generating incident report")
        quarantine_manager = getattr(request.app.state, "quarantine_manager", None)
        quarantine_status = {}
        if quarantine_manager is not None:
            try:
                quarantine_status = quarantine_manager.get_quarantine_status()
            except Exception:
                quarantine_status = {}

        report_path = generate_incident_report(quarantine_status=quarantine_status)
        report_name = Path(report_path).name
        print("[report] report generated")
        if download:
            return FileResponse(report_path, media_type="application/pdf", filename=report_name)

        return {"success": True, "report_path": report_path}
    except Exception as exc:
        print(f"[report] generation failed: {exc}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
