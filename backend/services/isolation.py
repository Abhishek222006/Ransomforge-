from __future__ import annotations

"""Lightweight quarantine / isolation manager for the RansomForge demo.

This module intentionally avoids dangerous system changes. It only maintains a
local application state, emits structured isolation events, and optionally
auto-recovers after a timeout. That keeps the hackathon demo visually strong
without doing anything risky to the host machine.

Sample console output:
    [isolation] network quarantined
    [isolation] reason: Honeypot file triggered
    [isolation] auto-recovery scheduled in 30s
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock, Timer
from time import monotonic
from typing import Any, Callable, Deque, Optional


IsolationCallback = Callable[[dict[str, Any]], None]


@dataclass
class QuarantineState:
    status: str = "NORMAL"
    reason: str = ""
    threat_score: int = 0
    severity: str = "low"
    timestamp: str = ""
    trigger_source: str = ""
    auto_recover_seconds: int = 0
    honeypot_triggered: bool = False
    critical_reason_count: int = 0
    network_status: str = "NORMAL"


class QuarantineManager:
    """Maintain quarantine state and emit structured isolation events."""

    def __init__(
        self,
        on_change: Optional[IsolationCallback] = None,
        auto_recover_seconds: int = 30,
        critical_window_seconds: int = 15,
        critical_threshold: int = 3,
    ) -> None:
        self._lock = Lock()
        self._state = QuarantineState()
        self._on_change = on_change
        self._auto_recover_seconds = max(0, int(auto_recover_seconds))
        self._critical_window_seconds = max(5, int(critical_window_seconds))
        self._critical_threshold = max(2, int(critical_threshold))
        self._critical_events: Deque[float] = deque()
        self._auto_recover_timer: Timer | None = None

    def set_callback(self, callback: Optional[IsolationCallback]) -> None:
        """Update the state-change callback used by the FastAPI app."""
        with self._lock:
            self._on_change = callback

    def get_quarantine_status(self) -> dict[str, Any]:
        """Return a JSON-friendly snapshot of the current isolation state."""
        with self._lock:
            return {
                "status": self._state.status,
                "network_status": self._state.network_status,
                "reason": self._state.reason,
                "threat_score": self._state.threat_score,
                "severity": self._state.severity,
                "timestamp": self._state.timestamp,
                "trigger_source": self._state.trigger_source,
                "auto_recover_seconds": self._state.auto_recover_seconds,
                "honeypot_triggered": self._state.honeypot_triggered,
                "critical_reason_count": self._state.critical_reason_count,
            }

    def enable_quarantine(
        self,
        reason: str,
        threat_score: int = 100,
        severity: str = "critical",
        timestamp: str | None = None,
        trigger_source: str = "manual",
        file_path: str | None = None,
        honeypot_triggered: bool = False,
        auto_recover_seconds: int | None = None,
    ) -> dict[str, Any] | None:
        """Switch the app into quarantined mode and emit a structured event."""
        with self._lock:
            already_quarantined = self._state.status == "QUARANTINED"
            self._state = QuarantineState(
                status="QUARANTINED",
                reason=reason,
                threat_score=int(threat_score),
                severity=severity,
                timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
                trigger_source=trigger_source,
                auto_recover_seconds=int(self._auto_recover_seconds if auto_recover_seconds is None else max(0, auto_recover_seconds)),
                honeypot_triggered=honeypot_triggered,
                critical_reason_count=self._state.critical_reason_count,
            )

            self._cancel_timer_locked()
            recovery_seconds = self._state.auto_recover_seconds
            if recovery_seconds > 0:
                self._auto_recover_timer = Timer(recovery_seconds, self._auto_recover)
                self._auto_recover_timer.daemon = True
                self._auto_recover_timer.start()

            event = self._build_event(
                event_type="ISOLATION_TRIGGERED",
                status="QUARANTINED",
                reason=reason,
                threat_score=threat_score,
                severity=severity,
                timestamp=self._state.timestamp,
                file_path=file_path,
                trigger_source=trigger_source,
                honeypot_triggered=honeypot_triggered,
                auto_recover_seconds=recovery_seconds,
            )

        print("[isolation] network quarantined")
        print(f"[isolation] reason: {reason}")
        if recovery_seconds > 0:
            print(f"[isolation] auto-recovery scheduled in {recovery_seconds}s")

        if already_quarantined:
            return None
        self._emit(event)
        return event

    def disable_quarantine(self, reason: str = "Auto recovery", timestamp: str | None = None) -> dict[str, Any] | None:
        """Return the app to NORMAL mode and emit a release event."""
        with self._lock:
            if self._state.status != "QUARANTINED":
                return None

            self._cancel_timer_locked()
            self._state.status = "NORMAL"
            self._state.reason = reason
            self._state.threat_score = 0
            self._state.severity = "low"
            self._state.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
            self._state.trigger_source = "recovery"
            self._state.honeypot_triggered = False
            self._state.network_status = "NORMAL"

            event = self._build_event(
                event_type="ISOLATION_RELEASED",
                status="NORMAL",
                reason=reason,
                threat_score=0,
                severity="low",
                timestamp=self._state.timestamp,
                trigger_source="recovery",
                honeypot_triggered=False,
                auto_recover_seconds=0,
            )

        print("[isolation] network quarantine cleared")
        print(f"[isolation] reason: {reason}")
        self._emit(event)
        return event

    def isolate_network(
        self,
        reason: str = "Critical ransomware activity detected",
        severity: str = "critical",
        timestamp: str | None = None,
        auto_recover_seconds: int | None = None,
        demo_only: bool = True,
        preserve_quarantine: bool = False,
    ) -> dict[str, Any] | None:
        """Simulate outbound network containment for hackathon demos.

        This does not change any real firewall or adapter settings. It only flips
        the internal state, emits a websocket event, and records a log entry so
        judges can see a convincing containment workflow.

        Optional Windows-only command (kept disabled by default):
            # subprocess.run(["netsh", "interface", "set", "interface", "name=Ethernet", "admin=DISABLED"])
        """
        with self._lock:
            if self._state.network_status == "ISOLATED" and (preserve_quarantine or self._state.status != "NORMAL"):
                return None

            self._state.network_status = "ISOLATED"
            if not preserve_quarantine or self._state.status != "QUARANTINED":
                self._state.status = "ISOLATED"
            self._state.reason = reason
            self._state.severity = severity
            self._state.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
            self._state.trigger_source = "network_isolation"
            self._state.auto_recover_seconds = int(self._auto_recover_seconds if auto_recover_seconds is None else max(0, auto_recover_seconds))

            event_status = "QUARANTINED" if preserve_quarantine and self._state.status == "QUARANTINED" else "ISOLATED"

            event = self._build_event(
                event_type="NETWORK_ISOLATED",
                status=event_status,
                reason=reason,
                threat_score=self._state.threat_score or 100,
                severity=severity,
                timestamp=self._state.timestamp,
                trigger_source="network_isolation",
                honeypot_triggered=self._state.honeypot_triggered,
                auto_recover_seconds=self._state.auto_recover_seconds,
            )

        print("[isolation] outbound network quarantined")
        print(f"[isolation] reason: {reason}")
        if demo_only:
            print("[isolation] demo-only mode active; no real adapter or firewall changes applied")

        self._emit(event)
        return event

    def trigger_isolation(
        self,
        *,
        reason: str,
        threat_score: int = 100,
        severity: str = "critical",
        timestamp: str | None = None,
        trigger_source: str = "automatic",
        file_path: str | None = None,
        honeypot_triggered: bool = False,
        auto_recover_seconds: int | None = None,
    ) -> dict[str, Any] | None:
        """Trigger quarantine plus network containment once for a critical incident."""
        with self._lock:
            already_active = self._state.network_status == "ISOLATED" and self._state.status in {"QUARANTINED", "ISOLATED"}
            if already_active:
                return None

        quarantine_event = None
        with self._lock:
            needs_quarantine = self._state.status != "QUARANTINED"

        if needs_quarantine:
            quarantine_event = self.enable_quarantine(
                reason=reason,
                threat_score=threat_score,
                severity=severity,
                timestamp=timestamp,
                trigger_source=trigger_source,
                file_path=file_path,
                honeypot_triggered=honeypot_triggered,
                auto_recover_seconds=auto_recover_seconds,
            )

        network_event = self.isolate_network(
            reason=reason,
            severity=severity,
            timestamp=timestamp,
            auto_recover_seconds=auto_recover_seconds,
            demo_only=True,
            preserve_quarantine=True,
        )

        if quarantine_event is None and network_event is None:
            return None

        return {"quarantine": quarantine_event, "network": network_event}

    def register_signal(
        self,
        *,
        event_type: str,
        threat_score: int,
        severity: str,
        reason: str,
        timestamp: str | None = None,
        file_path: str | None = None,
        honeypot_triggered: bool = False,
        auto_recover_seconds: int | None = None,
    ) -> dict[str, Any] | None:
        """Evaluate whether an incoming signal should trigger quarantine."""
        score = int(threat_score)
        now = monotonic()
        is_critical = score >= 90 or severity == "critical" or honeypot_triggered
        trigger_args: dict[str, Any] | None = None

        with self._lock:
            self._purge_old_critical_events_locked(now)
            if is_critical:
                self._critical_events.append(now)

            rapid_critical = len(self._critical_events) >= self._critical_threshold
            trigger_needed = honeypot_triggered or score >= 90 or rapid_critical
            if not trigger_needed:
                return None

            if honeypot_triggered:
                trigger_reason = "Honeypot file triggered"
            elif score >= 90:
                trigger_reason = f"Threat score reached {score}"
            else:
                trigger_reason = "Multiple critical anomalies detected rapidly"

            if self._state.status == "QUARANTINED":
                self._state.critical_reason_count = len(self._critical_events)
                return None

            trigger_args = {
                "reason": trigger_reason,
                "threat_score": max(score, 100 if honeypot_triggered else score),
                "severity": "critical",
                "timestamp": timestamp,
                "trigger_source": event_type,
                "file_path": file_path,
                "honeypot_triggered": honeypot_triggered,
                "auto_recover_seconds": auto_recover_seconds,
            }

        if trigger_args is None:
            return None
        return self.trigger_isolation(**trigger_args)

    def _auto_recover(self) -> None:
        """Timer callback that returns the system to NORMAL in a safe demo-only way."""
        self.disable_quarantine(reason="Auto recovery timeout reached")

    def _emit(self, event: dict[str, Any]) -> None:
        callback = None
        with self._lock:
            callback = self._on_change
        if callback is not None:
            callback(event)

    def _purge_old_critical_events_locked(self, now: float) -> None:
        while self._critical_events and (now - self._critical_events[0]) > self._critical_window_seconds:
            self._critical_events.popleft()
        self._state.critical_reason_count = len(self._critical_events)

    def _cancel_timer_locked(self) -> None:
        if self._auto_recover_timer is not None:
            self._auto_recover_timer.cancel()
            self._auto_recover_timer = None

    @staticmethod
    def _build_event(
        *,
        event_type: str,
        status: str,
        reason: str,
        threat_score: int,
        severity: str,
        timestamp: str,
        trigger_source: str,
        honeypot_triggered: bool,
        auto_recover_seconds: int,
        file_path: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "status": status,
            "reason": reason,
            "threat_score": int(threat_score),
            "severity": severity,
            "timestamp": timestamp,
            "file_path": file_path,
            "trigger_source": trigger_source,
            "honeypot_triggered": honeypot_triggered,
            "auto_recover_seconds": auto_recover_seconds,
            "demo_only": True,
        }
        return {"type": event_type, "data": data, "payload": data}


_GLOBAL_QUARANTINE_MANAGER: QuarantineManager | None = None


def set_quarantine_manager(manager: QuarantineManager) -> None:
    """Register the application-wide quarantine manager."""
    global _GLOBAL_QUARANTINE_MANAGER
    _GLOBAL_QUARANTINE_MANAGER = manager


def enable_quarantine(**kwargs: Any) -> dict[str, Any] | None:
    """Enable quarantine using the application-wide manager if available."""
    if _GLOBAL_QUARANTINE_MANAGER is None:
        return None
    return _GLOBAL_QUARANTINE_MANAGER.enable_quarantine(**kwargs)


def disable_quarantine(**kwargs: Any) -> dict[str, Any] | None:
    """Disable quarantine using the application-wide manager if available."""
    if _GLOBAL_QUARANTINE_MANAGER is None:
        return None
    return _GLOBAL_QUARANTINE_MANAGER.disable_quarantine(**kwargs)


def get_quarantine_status() -> dict[str, Any]:
    """Return the current quarantine status, or a default NORMAL state."""
    if _GLOBAL_QUARANTINE_MANAGER is None:
        return {
            "status": "NORMAL",
            "network_status": "NORMAL",
            "reason": "",
            "threat_score": 0,
            "severity": "low",
            "timestamp": "",
            "trigger_source": "",
            "auto_recover_seconds": 0,
            "honeypot_triggered": False,
            "critical_reason_count": 0,
        }
    return _GLOBAL_QUARANTINE_MANAGER.get_quarantine_status()