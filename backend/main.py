import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
import random

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

try:
    from .routers.health import router as health_router
    from .routers.events import router as events_router
    from .routers.processes import router as processes_router
    from .routers.quarantine import router as quarantine_router
    from .routers.operations import router as operations_router
    from .routers.assistant import router as assistant_router
    from .routers.recovery import router as recovery_router
    from .services.database import SQLiteEventStore
    from .services.websocket_manager import WebSocketManager
    from .services.isolation import QuarantineManager, set_quarantine_manager
    from .services.scan import FullSystemScanService
    from .services.email_alerts import send_alert_email
    from .monitors.file_monitor import FileMonitorService
    from .monitors.process_monitor import ProcessMonitorService, severity_label as process_severity_label
    from .detection.rules import create_honeypot_files
    from .services import db as db_service
except ImportError:
    from routers.health import router as health_router
    from routers.events import router as events_router
    from routers.processes import router as processes_router
    from routers.quarantine import router as quarantine_router
    from routers.operations import router as operations_router
    from routers.assistant import router as assistant_router
    from routers.recovery import router as recovery_router
    from services.database import SQLiteEventStore
    from services.websocket_manager import WebSocketManager
    from services.isolation import QuarantineManager, set_quarantine_manager
    from services.scan import FullSystemScanService
    from services.email_alerts import send_alert_email
    from monitors.file_monitor import FileMonitorService
    from monitors.process_monitor import ProcessMonitorService, severity_label as process_severity_label
    from detection.rules import create_honeypot_files
    from services import db as db_service


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DATABASE_PATH = BASE_DIR / "ransomforge_events.db"
MONITOR_PATH = REPO_ROOT / "runtime_watch"
DUMMY_BROADCAST_INTERVAL = 4

load_dotenv(REPO_ROOT / ".env")


def _severity_label(score: int) -> str:
    """Map a numeric threat score to a simple dashboard severity label."""
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _build_new_event_message(
    event_type: str,
    file_path: str | None,
    score: int,
    timestamp: str,
    description: str,
    extra_data: dict | None = None,
) -> dict:
    """Build the structured NEW_EVENT message expected by the frontend."""
    severity = _severity_label(score)
    data = {
        "event_type": event_type,
        "file_path": file_path,
        "threat_score": score,
        "severity": severity,
        "timestamp": timestamp,
        "time": timestamp,
        "title": event_type.replace("_", " ").title(),
        "description": description,
    }
    if extra_data:
        data.update(extra_data)
    return {"type": "NEW_EVENT", "data": data, "payload": data}


def _build_threat_update_message(score: int) -> dict:
    """Build the structured THREAT_UPDATE message expected by the frontend."""
    severity = _severity_label(score)
    data = {"score": score, "severity": severity}
    return {"type": "THREAT_UPDATE", "score": score, "severity": severity, "data": data, "payload": data}


def _build_alert_message(
    title: str,
    description: str,
    score: int,
    file_path: str | None,
    timestamp: str,
    extra_data: dict | None = None,
) -> dict:
    """Build the structured ALERT message for banner-style UI updates."""
    severity = _severity_label(score)
    data = {
        "title": title,
        "description": description,
        "severity": severity,
        "score": score,
        "file_path": file_path,
        "timestamp": timestamp,
        "time": timestamp,
    }
    if extra_data:
        data.update(extra_data)
    return {"type": "ALERT", "data": data, "payload": data}


def _send_email_alert_if_needed(event_data: dict) -> None:
    try:
        severity = str(event_data.get("severity", "")).lower()
        score_value = event_data.get("score", event_data.get("threat_score", 0))
        score = int(score_value)
    except Exception:
        severity = ""
        score = 0

    if severity not in {"high", "critical"} and score < 65:
        return

    try:
        send_alert_email(event_data)
    except Exception as error:
        print(f"[email] failed: {error}")


# ── Varied demo-event scenarios used by the realtime loop and _build_dummy_event ──
_DEMO_SCENARIOS = [
    {
        "event_type":  "mass_rename",
        "extension":   ".locked",
        "title":       "Mass file rename to .locked detected",
        "description": "Multiple files renamed to .locked in rapid succession — classic ransomware staging.",
        "reasons":     ["mass rename burst", "extension changed to .locked", "high modify rate"],
        "entropy_range": (7.2, 7.98),
    },
    {
        "event_type":  "file_encrypted",
        "extension":   ".encrypted",
        "title":       "File encryption burst detected",
        "description": "High-entropy writes detected across multiple files — encryption in progress.",
        "reasons":     ["entropy spike > 7.5", "write burst", "known ransomware extension"],
        "entropy_range": (7.5, 7.99),
    },
    {
        "event_type":  "file_renamed_suspicious",
        "extension":   ".crypt",
        "title":       "Suspicious file rename pattern",
        "description": "Files renamed with suspicious crypt extension — possible ransomware activity.",
        "reasons":     ["suspicious rename pattern", "crypt extension detected"],
        "entropy_range": (6.8, 7.6),
    },
    {
        "event_type":  "modified",
        "extension":   ".docx",
        "title":       "Rapid document modification burst",
        "description": "Batch of office documents modified at abnormal rate — possible encryption pass.",
        "reasons":     ["high write frequency", "office file targeted"],
        "entropy_range": (5.5, 7.2),
    },
    {
        "event_type":  "deleted",
        "extension":   ".bak",
        "title":       "Shadow copy / backup deletion attempt",
        "description": "Backup files deleted in bulk — common ransomware tactic to prevent recovery.",
        "reasons":     ["backup deletion", "shadow copy removal pattern"],
        "entropy_range": (4.0, 6.5),
    },
]


def _build_dummy_event(score: int) -> dict:
    """Create a frontend-friendly dummy event payload with varied context."""
    scenario = random.choice(_DEMO_SCENARIOS)
    fname = f"demo_{random.randint(1000, 9999)}{scenario['extension']}"
    return _build_new_event_message(
        event_type=scenario["event_type"],
        file_path=str(REPO_ROOT / "runtime_watch" / fname),
        score=score,
        timestamp=datetime.now(timezone.utc).isoformat(),
        description=scenario["description"],
    )


def _build_threat_update(score: int) -> dict:
    """Create a frontend-friendly threat score payload."""
    return _build_threat_update_message(score)


async def _realtime_demo_loop(websocket_manager: WebSocketManager, stop_event: asyncio.Event) -> None:
    """Broadcast demo events every few seconds while the backend is running."""
    score = 52
    while not stop_event.is_set():
        await asyncio.sleep(DUMMY_BROADCAST_INTERVAL)

        # keep the score lively for the dashboard
        score = max(10, min(98, score + random.randint(-4, 11)))
        if websocket_manager.connection_count <= 0:
            continue

        # Pick a random scenario so every broadcast (and email) carries distinct context
        scenario = random.choice(_DEMO_SCENARIOS)
        timestamp = datetime.now(timezone.utc).isoformat()
        fname = f"demo_live_{random.randint(1000, 9999)}{scenario['extension']}"
        file_path = str(REPO_ROOT / "runtime_watch" / fname)
        entropy = round(random.uniform(*scenario["entropy_range"]), 3)
        severity_str = _severity_label(score)

        new_event = _build_new_event_message(
            event_type=scenario["event_type"],
            file_path=file_path,
            score=score,
            timestamp=timestamp,
            description=scenario["description"],
        )
        await websocket_manager.broadcast_async(new_event)
        await websocket_manager.broadcast_async(_build_threat_update_message(score))

        _send_email_alert_if_needed(
            {
                "event_type":        scenario["event_type"],
                "title":             scenario["title"],
                "severity":          severity_str,
                "score":             score,
                "description":       scenario["description"],
                "file_path":         file_path,
                "timestamp":         timestamp,
                "source":            "realtime_demo_loop",
                "reasons":           scenario["reasons"],
                "entropy":           entropy,
                "honeypot_triggered": False,
            }
        )

        try:
            app.state.quarantine_manager.register_signal(
                event_type=scenario["event_type"],
                threat_score=score,
                severity=severity_str,
                reason=scenario["description"],
                timestamp=timestamp,
                file_path=file_path,
                honeypot_triggered=False,
                auto_recover_seconds=30,
            )
        except Exception:
            pass

        if score >= 80:
            await websocket_manager.broadcast_async(
                _build_alert_message(
                    title=scenario["title"],
                    description=scenario["description"],
                    score=score,
                    file_path=file_path,
                    timestamp=timestamp,
                )
            )


def _store_and_broadcast_process_anomaly(anomaly: dict) -> None:
    """Persist and broadcast a process anomaly using the same hackathon pipeline."""
    process_name = anomaly.get("process_name") or f"pid_{anomaly.get('pid')}"
    pid = anomaly.get("pid")
    score = int(anomaly.get("score", 0))
    severity = anomaly.get("severity") or process_severity_label(score)
    timestamp = anomaly.get("timestamp") or datetime.now(timezone.utc).isoformat()
    description = ", ".join(anomaly.get("reasons", [])) or anomaly.get("description") or "Suspicious process behavior detected"

    event_payload = {
        "event_type": anomaly.get("event_type", "process_anomaly"),
        "path": process_name,
        "severity": score,
        "details": {
            "process_name": process_name,
            "pid": pid,
            "cpu_percent": anomaly.get("cpu_percent", 0),
            "memory_percent": anomaly.get("memory_percent", 0),
            "io_read_bytes": anomaly.get("io_read_bytes", 0),
            "io_write_bytes": anomaly.get("io_write_bytes", 0),
            "child_process_count": anomaly.get("child_process_count", 0),
            "score": score,
            "severity": severity,
            "reasons": anomaly.get("reasons", []),
            "message": description,
            "source": "process_monitor",
        },
        "created_at": timestamp,
    }

    try:
        app.state.event_store.record_event(event_payload)
    except Exception:
        pass

    try:
        db_service.insert_event(
            event_type="process_anomaly",
            file_path=None,
            process_name=process_name,
            threat_score=score,
            severity=score,
            timestamp=timestamp,
        )
    except Exception:
        pass

    try:
        if score >= 80:
            db_service.insert_alert(message=f"{process_name}: {description}", severity=score, timestamp=timestamp)
    except Exception:
        pass

    _send_email_alert_if_needed(
        {
            "event_type":         "process_anomaly",
            "severity":           severity,
            "score":              score,
            "description":        description,
            "file_path":          None,
            "process_name":       process_name,
            "pid":                pid,
            "cpu_percent":        anomaly.get("cpu_percent", 0),
            "memory_percent":     anomaly.get("memory_percent", 0),
            "timestamp":          timestamp,
            "source":             "process_monitor",
            "reasons":            anomaly.get("reasons", []),
            "honeypot_triggered": False,
        }
    )

    try:
        app.state.quarantine_manager.register_signal(
            event_type="process_anomaly",
            threat_score=score,
            severity=severity,
            reason=description,
            timestamp=timestamp,
            file_path=process_name,
            honeypot_triggered=False,
            auto_recover_seconds=30,
        )
    except Exception:
        pass

    try:
        app.state.websocket_manager.broadcast(
            _build_new_event_message(
                event_type="process_anomaly",
                file_path=process_name,
                score=score,
                timestamp=timestamp,
                description=description,
                extra_data={
                    "process_name": process_name,
                    "pid": pid,
                    "cpu_percent": anomaly.get("cpu_percent", 0),
                    "memory_percent": anomaly.get("memory_percent", 0),
                    "io_read_bytes": anomaly.get("io_read_bytes", 0),
                    "io_write_bytes": anomaly.get("io_write_bytes", 0),
                    "child_process_count": anomaly.get("child_process_count", 0),
                },
            )
        )
        print(f"[process-monitor] websocket broadcast: {process_name} score={score}")
        app.state.websocket_manager.broadcast(_build_threat_update_message(score))
        app.state.websocket_manager.broadcast(
            _build_alert_message(
                title="Suspicious Process Detected",
                description=description,
                score=score,
                file_path=process_name,
                timestamp=timestamp,
                extra_data={
                    "process_name": process_name,
                    "pid": pid,
                    "cpu_percent": anomaly.get("cpu_percent", 0),
                    "memory_percent": anomaly.get("memory_percent", 0),
                    "io_read_bytes": anomaly.get("io_read_bytes", 0),
                    "io_write_bytes": anomaly.get("io_write_bytes", 0),
                    "child_process_count": anomaly.get("child_process_count", 0),
                    "reasons": anomaly.get("reasons", []),
                },
            )
        )
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    event_store = SQLiteEventStore(DATABASE_PATH)
    websocket_manager = WebSocketManager()
    websocket_manager.set_loop(asyncio.get_running_loop())
    quarantine_manager = QuarantineManager(auto_recover_seconds=30, critical_window_seconds=15, critical_threshold=3)
    scan_service = FullSystemScanService(
        watch_path=MONITOR_PATH,
        websocket_manager=websocket_manager,
        event_store=event_store,
        quarantine_manager=quarantine_manager,
    )
    MONITOR_PATH.mkdir(parents=True, exist_ok=True)
    create_honeypot_files(MONITOR_PATH)
    # Ensure the lightweight helper DB exists before any watcher event arrives.
    db_service.init_db()
    stop_event = asyncio.Event()
    process_stop_event = asyncio.Event()
    file_monitor = FileMonitorService(
        watch_path=MONITOR_PATH,
        on_event=app.state.handle_security_event,
    )
    process_monitor = ProcessMonitorService(on_anomaly=app.state.handle_process_anomaly, interval_seconds=4.0)

    app.state.event_store = event_store
    app.state.websocket_manager = websocket_manager
    app.state.quarantine_manager = quarantine_manager
    app.state.scan_service = scan_service
    app.state.file_monitor = file_monitor
    app.state.process_monitor = process_monitor
    app.state.realtime_stop_event = stop_event
    app.state.process_stop_event = process_stop_event
    quarantine_manager.set_callback(app.state.handle_quarantine_event)
    set_quarantine_manager(quarantine_manager)

    event_store.initialize()
    file_monitor.start()
    realtime_task = asyncio.create_task(_realtime_demo_loop(websocket_manager, stop_event))
    process_task = asyncio.create_task(process_monitor.run(process_stop_event))
    app.state.realtime_task = realtime_task
    app.state.process_task = process_task

    try:
        yield
    finally:
        stop_event.set()
        process_stop_event.set()
        realtime_task.cancel()
        process_task.cancel()
        try:
            await realtime_task
        except asyncio.CancelledError:
            pass
        try:
            await process_task
        except asyncio.CancelledError:
            pass
        file_monitor.stop()


app = FastAPI(
    title="RansomForge API",
    version="1.0.0",
    description="Hackathon-friendly backend for live ransomware monitoring and demo streaming.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(events_router)
app.include_router(processes_router)
app.include_router(quarantine_router)
app.include_router(operations_router)
app.include_router(assistant_router)
app.include_router(recovery_router)


def _handle_security_event(event: dict) -> None:
    # Keep existing store + broadcast behavior
    try:
        app.state.event_store.record_event(event)
    except Exception:
        # Don't let DB issues stop broadcasting in a hackathon demo
        pass

    try:
        # Also insert a lightweight, incremental record into the simple db helper.
        # Map fields from the event dict into insert_event signature.
        event_type = event.get("event_type", "unknown")
        file_path = event.get("path")
        details = event.get("details", {}) or {}
        process_name = details.get("process_name") or details.get("process")
        threat_score = int(event.get("severity", 0))
        severity = int(event.get("severity", 0))
        timestamp = event.get("created_at")

        # Non-blocking: ignore DB helper failures
        try:
            db_service.insert_event(
                event_type=event_type,
                file_path=file_path,
                process_name=process_name,
                threat_score=threat_score,
                severity=severity,
                timestamp=timestamp,
                entropy=details.get("entropy"),
            )
        except Exception:
            pass
    except Exception:
        # Defensive: if mapping fails, continue to broadcast
        pass

    # Broadcast structured messages for the frontend dashboard.
    try:
        event_type = event.get("event_type", "unknown")
        file_path = event.get("path")
        created_at = event.get("created_at") or datetime.now(timezone.utc).isoformat()
        score = int(event.get("severity", 0))
        details = event.get("details", {}) or {}
        description = details.get("message") or "Suspicious activity detected"
        alert_title = details.get("alert_title")
        alert_description = details.get("alert_description") or description
        severity_text = _severity_label(score)
        extra_data = {
            "honeypot_triggered": details.get("honeypot_triggered", False),
            "reasons": details.get("reasons", []),
            "source": details.get("source"),
            "process_name": details.get("process_name"),
            "pid": details.get("pid"),
            "entropy": details.get("entropy"),
            "entropy_level": details.get("entropy_level"),
            "entropy_bonus": details.get("entropy_bonus", 0),
        }

        try:
            app.state.quarantine_manager.register_signal(
                event_type=event_type,
                threat_score=score,
                severity=severity_text,
                reason=description,
                timestamp=created_at,
                file_path=file_path,
                honeypot_triggered=bool(details.get("honeypot_triggered", False)),
                auto_recover_seconds=30,
            )
        except Exception:
            pass

        app.state.websocket_manager.broadcast(
            _build_new_event_message(
                event_type=event_type,
                file_path=file_path,
                score=score,
                timestamp=created_at,
                description=description,
                extra_data=extra_data,
            )
        )
        app.state.websocket_manager.broadcast(_build_threat_update_message(score))

        if score >= 80:
            app.state.websocket_manager.broadcast(
                _build_alert_message(
                    title=alert_title or "High severity ransomware activity",
                    description=alert_description,
                    score=score,
                    file_path=file_path,
                    timestamp=created_at,
                    extra_data=extra_data,
                )
            )

        _send_email_alert_if_needed(
            {
                "event_type":         event_type,
                "severity":           severity_text,
                "score":              score,
                "description":        alert_description,
                "file_path":          file_path,
                "process_name":       process_name,
                "timestamp":          created_at,
                "source":             details.get("source"),
                "title":              alert_title or "Ransomware activity detected",
                "reasons":            details.get("reasons", []),
                "entropy":            details.get("entropy"),
                "honeypot_triggered": bool(details.get("honeypot_triggered", False)),
            }
        )
    except Exception:
        pass


app.state.handle_security_event = _handle_security_event
app.state.handle_process_anomaly = _store_and_broadcast_process_anomaly


def _handle_quarantine_event(event: dict) -> None:
    data = event.get("data", {}) or {}
    event_type = event.get("type", "ISOLATION_TRIGGERED")
    timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
    score = int(data.get("threat_score", 100))
    reason = data.get("reason") or "Isolation state changed"
    status = data.get("status", "QUARANTINED")

    event_record = {
        "event_type": (
            "quarantine_triggered"
            if event_type == "ISOLATION_TRIGGERED"
            else "quarantine_released"
            if event_type == "ISOLATION_RELEASED"
            else "network_isolated"
        ),
        "path": "system/quarantine",
        "severity": score,
        "details": {
            "status": status,
            "reason": reason,
            "trigger_source": data.get("trigger_source"),
            "honeypot_triggered": data.get("honeypot_triggered", False),
            "auto_recover_seconds": data.get("auto_recover_seconds", 0),
            "threat_score": score,
            "source": "isolation_manager",
        },
        "created_at": timestamp,
    }

    try:
        app.state.event_store.record_event(event_record)
    except Exception:
        pass

    try:
        db_service.insert_event(
            event_type=event_record["event_type"],
            file_path="system/quarantine",
            process_name=None,
            threat_score=score,
            severity=score,
            timestamp=timestamp,
        )
    except Exception:
        pass

    try:
        if event_type == "ISOLATION_TRIGGERED":
            db_service.insert_alert(message=f"Isolation activated: {reason}", severity=score, timestamp=timestamp)
        elif event_type == "NETWORK_ISOLATED":
            db_service.insert_alert(message=f"Network isolated: {reason}", severity=score, timestamp=timestamp)
    except Exception:
        pass

    try:
        app.state.websocket_manager.broadcast(event)
        if event_type == "ISOLATION_TRIGGERED":
            app.state.websocket_manager.broadcast(_build_threat_update_message(score))
            app.state.websocket_manager.broadcast(
                _build_alert_message(
                    title="Isolation Activated",
                    description=reason,
                    score=score,
                    file_path=data.get("file_path"),
                    timestamp=timestamp,
                    extra_data={
                        "status": status,
                        "trigger_source": data.get("trigger_source"),
                        "honeypot_triggered": data.get("honeypot_triggered", False),
                        "auto_recover_seconds": data.get("auto_recover_seconds", 0),
                    },
                )
            )
            if data.get("trigger_source") != "manual":
                _send_email_alert_if_needed(
                    {
                        "event_type": event_type,
                        "severity": data.get("severity") or _severity_label(score),
                        "score": score,
                        "description": reason,
                        "file_path": data.get("file_path"),
                        "process_name": data.get("process_name"),
                        "timestamp": timestamp,
                        "reason": reason,
                        "source": data.get("trigger_source") or "isolation_manager",
                    }
                )
        elif event_type == "NETWORK_ISOLATED":
            app.state.websocket_manager.broadcast(
                _build_alert_message(
                    title="NETWORK ISOLATED",
                    description=reason,
                    score=score,
                    file_path=data.get("file_path"),
                    timestamp=timestamp,
                    extra_data={
                        "status": status,
                        "trigger_source": data.get("trigger_source"),
                        "demo_only": data.get("demo_only", True),
                    },
                )
            )
        else:
            app.state.websocket_manager.broadcast(
                _build_alert_message(
                    title="Isolation Cleared",
                    description=reason,
                    score=0,
                    file_path=data.get("file_path"),
                    timestamp=timestamp,
                    extra_data={"status": status, "trigger_source": data.get("trigger_source")},
                )
            )
    except Exception:
        pass
app.state.handle_quarantine_event = _handle_quarantine_event


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "RansomForge backend running"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.post("/demo/event")
async def demo_event() -> dict[str, object]:
    event = {
        "event_type": "demo_ransomware_alert",
        "path": str(REPO_ROOT / "user_documents" / "suspicious_encryptor.exe"),
        "severity": 92,
        "details": {
            "source": "demo",
            "message": "Simulated ransomware activity detected",
            "action": "mass_file_encryption_pattern",
            "host": "hackathon-lab",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _handle_security_event(event)
    return {"status": "queued", "event": event}


# ── Operations endpoints ──────────────────────────────────────────────────────

_network_isolated = False
_scan_active      = False


@app.post("/operations/full-scan")
async def start_full_scan() -> dict[str, object]:
    """Trigger a simulated full system scan and stream progress via websocket."""
    global _scan_active
    if _scan_active:
        return {"status": "already_running", "message": "A scan is already in progress"}

    _scan_active = True
    asyncio.create_task(_run_scan_simulation())
    return {"status": "started", "message": "Full scan initiated"}


async def _run_scan_simulation() -> None:
    global _scan_active
    manager = app.state.websocket_manager
    total   = random.randint(3200, 6800)
    threats = 0

    await manager.broadcast_async({
        "type": "SCAN_STARTED",
        "payload": {"total_files": total, "timestamp": datetime.now(timezone.utc).isoformat()},
    })

    scanned = 0
    while scanned < total:
        await asyncio.sleep(0.25)
        step    = random.randint(80, 240)
        scanned = min(scanned + step, total)
        pct     = round((scanned / total) * 100, 1)

        if random.random() < 0.08:
            threats += 1

        await manager.broadcast_async({
            "type": "SCAN_PROGRESS",
            "payload": {
                "scanned": scanned,
                "total": total,
                "percent": pct,
                "threats_found": threats,
            },
        })

    final_score = min(30 + threats * 8, 98)
    await manager.broadcast_async({
        "type": "SCAN_COMPLETED",
        "payload": {
            "scanned": total,
            "threats_found": threats,
            "threat_score": final_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    })
    _scan_active = False


@app.post("/operations/isolate-network")
async def isolate_network() -> dict[str, object]:
    """Activate network isolation and broadcast NETWORK_ISOLATED."""
    global _network_isolated
    ts = datetime.now(timezone.utc).isoformat()
    manager = getattr(app.state, "quarantine_manager", None)
    event = None
    if manager is not None:
        event = manager.trigger_isolation(
            reason="Manual network isolation activated",
            threat_score=100,
            severity="critical",
            timestamp=ts,
            trigger_source="manual",
            auto_recover_seconds=30,
        )
    if event is None:
        _network_isolated = True
        await app.state.websocket_manager.broadcast_async({
            "type": "NETWORK_ISOLATED",
            "payload": {"timestamp": ts, "message": "Network isolation activated"},
        })
        return {"status": "isolated", "timestamp": ts}

    _network_isolated = True
    return {"status": "isolated", "timestamp": ts, "event": event}


@app.post("/operations/contain-host")
async def contain_host(host: str = "Endpoint-1") -> dict[str, object]:
    """Simulate host containment."""
    ts = datetime.now(timezone.utc).isoformat()
    await app.state.websocket_manager.broadcast_async({
        "type": "ALERT",
        "payload": {
            "title": f"Host Contained: {host}",
            "description": f"Host {host} has been isolated from the network.",
            "severity": "high",
            "timestamp": ts,
        },
    })
    return {"status": "contained", "host": host, "timestamp": ts}


@app.get("/quarantine/status")
async def quarantine_status() -> dict[str, object]:
    manager = getattr(app.state, "quarantine_manager", None)
    status = manager.get_quarantine_status() if manager is not None else {"status": "NORMAL", "network_status": "NORMAL"}
    return {
        "isolated": status.get("status") in {"QUARANTINED", "ISOLATED"} or status.get("network_status") == "ISOLATED",
        "scan_active": _scan_active,
        "quarantine": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/processes/recent")
async def recent_processes() -> dict[str, object]:
    """Return simulated suspicious process data for the dashboard panel."""
    procs = [
        {"id": 1, "name": "svchost.exe",    "cpu": random.randint(60, 95), "mem": random.randint(30, 70), "io": random.randint(70, 99), "risk": "critical", "pid": 4812},
        {"id": 2, "name": "powershell.exe", "cpu": random.randint(40, 80), "mem": random.randint(50, 85), "io": random.randint(20, 50), "risk": "high",     "pid": 2244},
        {"id": 3, "name": "conhost.exe",    "cpu": random.randint(10, 35), "mem": random.randint(30, 60), "io": random.randint(10, 30), "risk": "medium",   "pid": 5516},
        {"id": 4, "name": "explorer.exe",   "cpu": random.randint(5,  20), "mem": random.randint(20, 40), "io": random.randint(5,  15), "risk": "low",      "pid": 1120},
    ]
    return {"processes": procs, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/assets/honeypots")
async def honeypot_assets() -> dict[str, object]:
    assets = [
        {"id": 1, "name": "bank_passwords.txt",     "type": "honeypot",  "status": "triggered", "risk": "critical", "path": "/sensitive/bank_passwords.txt"},
        {"id": 2, "name": "wallet_keys.txt",         "type": "honeypot",  "status": "clean",     "risk": "high",     "path": "/sensitive/wallet_keys.txt"},
        {"id": 3, "name": "employee_records.csv",    "type": "protected", "status": "clean",     "risk": "medium",   "path": "/hr/employee_records.csv"},
        {"id": 4, "name": "confidential_backup.zip", "type": "protected", "status": "clean",     "risk": "medium",   "path": "/backups/confidential_backup.zip"},
        {"id": 5, "name": "system_config.bak",       "type": "protected", "status": "modified",  "risk": "high",     "path": "/system/system_config.bak"},
    ]
    return {"assets": assets, "timestamp": datetime.now(timezone.utc).isoformat()}


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await app.state.websocket_manager.connect(websocket)
    try:
        try:
            await websocket.send_json({"type": "connection", "message": "connected"})
        except Exception:
            pass
        while True:
            try:
                payload = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break

            try:
                if payload.strip().lower() == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await websocket.send_json({"type": "echo", "message": payload})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        app.state.websocket_manager.disconnect(websocket)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass 


