from __future__ import annotations

"""Lightweight simulated full system scan for the RansomForge demo.

The scan is intentionally constrained to the monitored runtime_watch folder so
it can create believable SOC-style telemetry without touching the rest of the
machine. It reuses the existing entropy, honeypot, and heuristic scoring logic
to enrich the dashboard and support future ML/AI feature engineering.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any, Callable

from . import db as db_service

try:
    from ..detection.rules import is_honeypot_name, is_suspicious_honeypot_extension
    from ..detection.threat_scoring import analyze_file_entropy, score_file_event_details
    from .email_alerts import send_alert_email
except ImportError:
    from detection.rules import is_honeypot_name, is_suspicious_honeypot_extension
    from detection.threat_scoring import analyze_file_entropy, score_file_event_details
    from services.email_alerts import send_alert_email


ScanCallback = Callable[[dict[str, Any]], None]


@dataclass
class ScanSummary:
    files_scanned: int = 0
    threats_detected: int = 0
    max_threat_score: int = 0
    duration_seconds: float = 0.0
    severity: str = "low"


class FullSystemScanService:
    """Simulated scan runner for the local runtime_watch folder."""

    def __init__(
        self,
        watch_path: Path,
        websocket_manager,
        event_store,
        quarantine_manager,
        on_progress: ScanCallback | None = None,
    ) -> None:
        self.watch_path = Path(watch_path)
        self.websocket_manager = websocket_manager
        self.event_store = event_store
        self.quarantine_manager = quarantine_manager
        self._on_progress = on_progress
        self._lock = Lock()
        self._scan_task: asyncio.Task | None = None
        self._scan_id = 0

    async def start_scan(self) -> dict[str, Any]:
        """Start the scan in the background and return immediately to the API."""
        with self._lock:
            if self._scan_task is not None and not self._scan_task.done():
                return {"ok": False, "message": "A scan is already running"}

            self._scan_id += 1
            scan_id = f"scan-{self._scan_id}"
            self._scan_task = asyncio.create_task(self._run_scan(scan_id))

        return {"ok": True, "message": "Full system scan started", "scan_id": scan_id, "watch_path": str(self.watch_path)}

    async def _run_scan(self, scan_id: str) -> None:
        start_time = monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        print(f"[scan] full system scan started: {self.watch_path}")
        self._broadcast(
            {
                "type": "SCAN_STARTED",
                "data": {"message": "Full system scan started", "timestamp": started_at, "scan_id": scan_id},
                "payload": {"message": "Full system scan started", "timestamp": started_at, "scan_id": scan_id},
            }
        )

        self._record_scan_event(
            event_type="full_scan_started",
            path=str(self.watch_path),
            severity=10,
            details={"scan_id": scan_id, "status": "started", "watch_path": str(self.watch_path)},
            created_at=started_at,
        )

        summary = ScanSummary()
        files = self._collect_files()

        if not files:
            await self._finalize_scan(scan_id, summary, start_time)
            return

        for index, file_path in enumerate(files, start=1):
            result = self._inspect_file(file_path)
            summary.files_scanned = index
            summary.max_threat_score = max(summary.max_threat_score, result["score"])

            if result["is_threat"]:
                summary.threats_detected += 1
                finding_at = datetime.now(timezone.utc).isoformat()
                self._record_scan_event(
                    event_type="full_scan_finding",
                    path=str(file_path),
                    severity=result["score"],
                    details={
                        "scan_id": scan_id,
                        "file_name": file_path.name,
                        "reason": result["reason"],
                        "reasons": result["reasons"],
                        "entropy": result["entropy"],
                        "entropy_level": result["entropy_level"],
                        "honeypot_triggered": result["honeypot_triggered"],
                        "suspicious_filename": result["suspicious_filename"],
                        "score": result["score"],
                    },
                    created_at=finding_at,
                )

                if result["score"] >= 90 or result["honeypot_triggered"]:
                    try:
                        self.quarantine_manager.register_signal(
                            event_type="full_scan",
                            threat_score=result["score"],
                            severity=result["severity"],
                            reason=result["reason"],
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            file_path=str(file_path),
                            honeypot_triggered=result["honeypot_triggered"],
                            auto_recover_seconds=30,
                        )
                    except Exception:
                        pass

            if index == 1 or index % 3 == 0 or index == len(files):
                progress_timestamp = datetime.now(timezone.utc).isoformat()
                progress_payload = {
                    "type": "SCAN_PROGRESS",
                    "data": {
                        "files_scanned": summary.files_scanned,
                        "threats_detected": summary.threats_detected,
                        "current_file": file_path.name,
                        "timestamp": progress_timestamp,
                        "scan_id": scan_id,
                    },
                    "payload": {
                        "files_scanned": summary.files_scanned,
                        "threats_detected": summary.threats_detected,
                        "current_file": file_path.name,
                        "timestamp": progress_timestamp,
                        "scan_id": scan_id,
                    },
                }
                self._broadcast(progress_payload)

            await asyncio.sleep(0.02)

        await self._finalize_scan(scan_id, summary, start_time)

    async def _finalize_scan(self, scan_id: str, summary: ScanSummary, start_time: float) -> None:
        summary.duration_seconds = round(monotonic() - start_time, 2)
        summary.severity = self._summarize_severity(summary)
        completed_at = datetime.now(timezone.utc).isoformat()

        print(
            f"[scan] completed files={summary.files_scanned} threats={summary.threats_detected} duration={summary.duration_seconds}s severity={summary.severity}"
        )

        payload = {
            "type": "SCAN_COMPLETED",
            "data": {
                "files_scanned": summary.files_scanned,
                "threats_detected": summary.threats_detected,
                "duration_seconds": summary.duration_seconds,
                "severity": summary.severity,
                "timestamp": completed_at,
                "scan_id": scan_id,
            },
            "payload": {
                "files_scanned": summary.files_scanned,
                "threats_detected": summary.threats_detected,
                "duration_seconds": summary.duration_seconds,
                "severity": summary.severity,
                "timestamp": completed_at,
                "scan_id": scan_id,
            },
        }
        self._broadcast(payload)

        details = {
            "scan_id": scan_id,
            "files_scanned": summary.files_scanned,
            "threats_detected": summary.threats_detected,
            "duration_seconds": summary.duration_seconds,
            "severity": summary.severity,
            "watch_path": str(self.watch_path),
        }
        self._record_scan_event(
            event_type="full_scan_completed",
            path=str(self.watch_path),
            severity=summary.max_threat_score or self._severity_to_score(summary.severity),
            details=details,
            created_at=completed_at,
        )

        if summary.max_threat_score >= 80 or summary.threats_detected >= 3:
            try:
                self.quarantine_manager.register_signal(
                    event_type="full_scan",
                    threat_score=max(summary.max_threat_score, 80),
                    severity=summary.severity,
                    reason="Full system scan detected suspicious ransomware activity",
                    timestamp=completed_at,
                    file_path=str(self.watch_path),
                    honeypot_triggered=False,
                    auto_recover_seconds=30,
                )
            except Exception:
                pass

    def _inspect_file(self, file_path: Path) -> dict[str, Any]:
        entropy = None
        entropy_level = "unknown"
        if file_path.exists() and file_path.is_file():
            entropy_result = analyze_file_entropy(str(file_path))
            entropy = entropy_result.get("entropy")
            entropy_level = entropy_result.get("entropy_level", "unknown")

        score_details = score_file_event_details(str(file_path), "modified", entropy=entropy)
        honeypot_triggered = is_honeypot_name(file_path.name) or is_suspicious_honeypot_extension(file_path.name)
        suspicious_filename = any(token in file_path.name.lower() for token in ("locked", "encrypted", "crypto", "ransom", "decrypt"))

        reasons = list(score_details["reasons"])
        if honeypot_triggered and "honeypot file matched" not in reasons:
            reasons.append("honeypot file matched")
        if suspicious_filename and "ransomware-like filename" not in reasons:
            reasons.append("ransomware-like filename")
        if entropy_level == "high" and "high entropy detected" not in reasons:
            reasons.append("high entropy detected")

        score = int(score_details["score"])
        if honeypot_triggered:
            score = max(score, 100)

        severity = self._score_to_severity(score)
        is_threat = score >= 65 or honeypot_triggered or entropy_level == "high" or suspicious_filename
        reason = ", ".join(reasons) if reasons else "Suspicious file observed during scan"

        return {
            "score": score,
            "severity": severity,
            "is_threat": is_threat,
            "reason": reason,
            "reasons": reasons,
            "entropy": entropy,
            "entropy_level": entropy_level,
            "honeypot_triggered": honeypot_triggered,
            "suspicious_filename": suspicious_filename,
        }

    def _collect_files(self) -> list[Path]:
        if not self.watch_path.exists():
            return []

        files = [path for path in self.watch_path.rglob("*") if path.is_file()]
        files.sort(key=lambda path: str(path).lower())
        return files

    def _broadcast(self, payload: dict[str, Any]) -> None:
        try:
            self.websocket_manager.broadcast(payload)
        except Exception:
            pass

        if self._on_progress is not None:
            try:
                self._on_progress(payload)
            except Exception:
                pass

    def _record_scan_event(self, *, event_type: str, path: str, severity: int, details: dict[str, Any], created_at: str) -> None:
        record = {
            "event_type": event_type,
            "path": path,
            "severity": int(severity),
            "details": details,
            "created_at": created_at,
        }

        try:
            self.event_store.record_event(record)
        except Exception:
            pass

        try:
            db_service.insert_event(
                event_type=event_type,
                file_path=path,
                process_name=None,
                threat_score=int(severity),
                severity=int(severity),
                timestamp=created_at,
                entropy=details.get("entropy"),
            )
        except Exception:
            pass

        if event_type == "full_scan_completed":
            try:
                db_service.insert_alert(
                    message=f"Full scan completed: {details.get('threats_detected', 0)} threats detected",
                    severity=int(severity),
                    timestamp=created_at,
                )
            except Exception:
                pass

        if event_type == "full_scan_finding":
            severity_label = self._score_to_severity(int(severity))
            if severity_label in {"high", "critical"}:
                try:
                    send_alert_email(
                        {
                            "event_type": event_type,
                            "severity": severity_label,
                            "score": int(severity),
                            "description": details.get("reason") or details.get("reasons") or "Suspicious file detected during full system scan",
                            "file_path": path,
                            "timestamp": created_at,
                            "source": "full_system_scan",
                            "scan_id": details.get("scan_id"),
                            "reasons": details.get("reasons", []),
                            "entropy": details.get("entropy"),
                            "entropy_level": details.get("entropy_level"),
                        }
                    )
                except Exception:
                    pass

    @staticmethod
    def _score_to_severity(score: int) -> str:
        if score >= 85:
            return "critical"
        if score >= 65:
            return "high"
        if score >= 35:
            return "medium"
        return "low"

    def _summarize_severity(self, summary: ScanSummary) -> str:
        """Summarize the overall scan severity for the completion payload."""
        if summary.max_threat_score >= 90 or summary.threats_detected >= 5:
            return "critical"
        if summary.max_threat_score >= 70 or summary.threats_detected >= 2:
            return "high"
        if summary.max_threat_score >= 35 or summary.threats_detected > 0:
            return "medium"
        return "low"

    @staticmethod
    def _severity_to_score(severity: str) -> int:
        mapping = {"critical": 90, "high": 70, "medium": 45, "low": 15}
        return mapping.get(severity, 15)