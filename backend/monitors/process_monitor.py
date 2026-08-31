from __future__ import annotations

"""Lightweight process anomaly monitor for the RansomForge hackathon demo.

This module is intentionally simple and low-impact. It uses psutil to sample
running processes every few seconds and emits believable ransomware-style
anomalies without any kernel-level or enterprise EDR complexity.

Sample console output:
    [process-monitor] suspicious process detected: encryptor.exe pid=4124 score=92 severity=critical
    [process-monitor] reasons: suspicious name, high cpu, memory burst, io burst

How to test with a fake suspicious process name on Windows:
1. Copy a harmless executable to a temp folder and rename it to something like
   `encryptor.exe` or `locker.exe`.
2. Launch it normally.
3. The monitor will score the name as suspicious even if the process is harmless.

Expected backend integration:
- `main.py` starts this monitor during FastAPI lifespan
- anomaly callbacks insert into SQLite via `db.py`
- anomaly callbacks broadcast `NEW_EVENT`, `THREAT_UPDATE`, and `ALERT`
"""

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from time import monotonic

import psutil


SUSPICIOUS_NAME_KEYWORDS = ("encryptor", "locker", "ransomware", "wannacry", "crypt")


def severity_label(score: int) -> str:
    """Convert a numeric score into a dashboard-friendly severity label."""
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


class ProcessMonitorService:
    """Periodically sample running processes and flag suspicious behavior."""

    def __init__(
        self,
        on_anomaly: Callable[[dict[str, Any]], None],
        interval_seconds: float = 4.0,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 30.0,
        io_delta_threshold: int = 5 * 1024 * 1024,
        child_threshold: int = 4,
        min_score_to_report: int = 35,
    ) -> None:
        self.on_anomaly = on_anomaly
        self.interval_seconds = max(1.0, float(interval_seconds))
        self.cpu_threshold = float(cpu_threshold)
        self.memory_threshold = float(memory_threshold)
        self.io_delta_threshold = int(io_delta_threshold)
        self.child_threshold = int(child_threshold)
        self.min_score_to_report = int(min_score_to_report)
        self._previous_io_totals: dict[int, int] = {}
        self._previous_child_counts: dict[int, int] = {}
        self._last_reported_at: dict[int, float] = {}
        self._last_reported_score: dict[int, int] = {}
        self._last_fallback_reported_at: float = 0.0
        self._last_start_logged: bool = False

    async def run(self, stop_event: asyncio.Event) -> None:
        """Run until the stop event is set."""
        if not self._last_start_logged:
            print("[process-monitor] started")
            self._last_start_logged = True

        while not stop_event.is_set():
            anomalies = await asyncio.to_thread(self.scan_once)
            for anomaly in anomalies:
                print(
                    f"[process-monitor] anomaly detected: {anomaly.get('process_name')} pid={anomaly.get('pid')} score={anomaly.get('score')} severity={anomaly.get('severity')}"
                )
                self.on_anomaly(anomaly)

            if not anomalies:
                fallback_anomaly = self._build_fallback_anomaly()
                if fallback_anomaly is not None:
                    print(
                        f"[process-monitor] anomaly detected: {fallback_anomaly.get('process_name')} pid={fallback_anomaly.get('pid')} score={fallback_anomaly.get('score')} severity={fallback_anomaly.get('severity')}"
                    )
                    self.on_anomaly(fallback_anomaly)

            await asyncio.sleep(self.interval_seconds)

    def scan_once(self) -> list[dict[str, Any]]:
        """Inspect running processes once and return any anomalies found."""
        anomalies: list[dict[str, Any]] = []

        for proc in psutil.process_iter(attrs=["pid", "name", "exe", "username", "status"]):
            try:
                anomaly = self._inspect_process(proc)
                if anomaly is not None:
                    anomalies.append(anomaly)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        return anomalies

    def _inspect_process(self, proc: psutil.Process) -> dict[str, Any] | None:
        info = proc.info
        pid = int(info.get("pid") or proc.pid)
        process_name = (info.get("name") or proc.name() or f"pid_{pid}").strip()
        lower_name = process_name.lower()

        # Lightweight sampling. We intentionally avoid expensive or intrusive calls.
        cpu_percent = float(proc.cpu_percent(interval=None))
        memory_percent = float(proc.memory_percent())
        io_counters = self._safe_io_counters(proc)
        child_count = self._safe_child_count(proc)

        score = 0
        reasons: list[str] = []

        if any(keyword in lower_name for keyword in SUSPICIOUS_NAME_KEYWORDS):
            score += 35
            reasons.append("suspicious name")

        if cpu_percent >= self.cpu_threshold:
            score += 25
            reasons.append("high cpu")
        elif cpu_percent >= self.cpu_threshold * 0.7:
            score += 12
            reasons.append("elevated cpu")

        if memory_percent >= self.memory_threshold:
            score += 18
            reasons.append("memory burst")
        elif memory_percent >= self.memory_threshold * 0.7:
            score += 8
            reasons.append("elevated memory")

        current_io_total = None
        if io_counters is not None:
            current_io_total = int(getattr(io_counters, "read_bytes", 0)) + int(getattr(io_counters, "write_bytes", 0))
            previous_total = self._previous_io_totals.get(pid)
            if previous_total is not None:
                io_delta = current_io_total - previous_total
                if io_delta >= self.io_delta_threshold:
                    score += 20
                    reasons.append("io burst")
                elif io_delta >= self.io_delta_threshold // 2:
                    score += 10
                    reasons.append("elevated io")

        previous_child_count = self._previous_child_counts.get(pid)
        if child_count >= self.child_threshold:
            score += 12
            reasons.append("child process burst")
        elif previous_child_count is not None and child_count - previous_child_count >= 2:
            score += 10
            reasons.append("rapid child spawning")

        self._previous_child_counts[pid] = child_count
        if current_io_total is not None:
            self._previous_io_totals[pid] = current_io_total

        score = min(score, 100)
        severity = severity_label(score)

        if score < self.min_score_to_report:
            return None

        now = datetime.now(timezone.utc).timestamp()
        last_reported_at = self._last_reported_at.get(pid)
        if last_reported_at is not None and (now - last_reported_at) < 3.0:
            return None

        self._last_reported_at[pid] = now

        timestamp = datetime.now(timezone.utc).isoformat()
        anomaly = {
            "event_type": "process_anomaly",
            "process_name": process_name,
            "pid": pid,
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory_percent, 2),
            "io_read_bytes": int(getattr(io_counters, "read_bytes", 0)) if io_counters else 0,
            "io_write_bytes": int(getattr(io_counters, "write_bytes", 0)) if io_counters else 0,
            "child_process_count": child_count,
            "score": score,
            "severity": severity,
            "reasons": reasons,
            "timestamp": timestamp,
            "description": "Suspicious process behavior detected",
        }
        return anomaly

    def _build_fallback_anomaly(self) -> dict[str, Any] | None:
        """Generate a safe synthetic anomaly when the host is too quiet for a demo.

        This keeps the dashboard visibly active without scanning or modifying any
        extra processes. The payload matches the real process anomaly shape.
        """
        now = monotonic()
        if (now - self._last_fallback_reported_at) < max(self.interval_seconds * 3, 18.0):
            return None

        self._last_fallback_reported_at = now
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "event_type": "process_anomaly",
            "process_name": "synthetic-demo-process.exe",
            "pid": 0,
            "cpu_percent": 78.5,
            "memory_percent": 34.2,
            "io_read_bytes": 1_024_000,
            "io_write_bytes": 6_291_456,
            "child_process_count": 5,
            "score": 72,
            "severity": severity_label(72),
            "reasons": [
                "synthetic demo visibility fallback",
                "elevated cpu",
                "memory burst",
                "io burst",
                "child process burst",
            ],
            "timestamp": timestamp,
            "description": "Synthetic process anomaly emitted for demo visibility",
        }

    @staticmethod
    def _safe_io_counters(proc: psutil.Process):
        try:
            return proc.io_counters()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, AttributeError):
            return None

    @staticmethod
    def _safe_child_count(proc: psutil.Process) -> int:
        try:
            return len(proc.children(recursive=False))
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            return 0