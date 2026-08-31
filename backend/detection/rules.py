from __future__ import annotations

"""Lightweight honeypot detection helpers for the RansomForge demo.

This module stays intentionally simple: it creates a small set of decoy files in
`runtime_watch/` and flags events when those files are modified, renamed,
deleted, or accessed in quick bursts. The goal is a believable critical alert
for hackathon storytelling, not enterprise endpoint protection.

Sample console output:
    [honeypot] created decoy files in runtime_watch
    [honeypot] triggered: bank_passwords.txt.locked score=100 severity=critical
"""

from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Deque, Iterable


HONEYPOT_FILENAMES = (
    "bank_passwords.txt",
    "wallet_keys.txt",
    "salary_data.xlsx",
    "employee_records.csv",
    "confidential_backup.zip",
)
SUSPICIOUS_EXTENSIONS = (".locked", ".encrypted")
HONEYPOT_SCORE = 100
HONEYPOT_SEVERITY = "critical"


def should_analyze_entropy(event_type: str, file_name: str) -> bool:
    """Return True when a file event is worth Shannon entropy inspection.

    Ransomware often modifies, renames, or appends extensions to files after
    encryption. Those patterns are cheap, high-signal triggers for a fast
    entropy pass that can enrich the existing heuristic detector and feed future
    AI/ML feature engineering.
    """
    name = Path(file_name).name.lower()
    if event_type in {"modified", "moved"}:
        return True
    return any(name.endswith(extension) for extension in SUSPICIOUS_EXTENSIONS)


def create_honeypot_files(watch_path: Path) -> list[Path]:
    """Create decoy files inside `runtime_watch/` if they do not already exist."""
    watch_path = Path(watch_path)
    watch_path.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    templates = {
        "bank_passwords.txt": "BANK ACCOUNT PASSWORDS\nDemo-only decoy content.\n",
        "wallet_keys.txt": "WALLET KEYS\nDemo-only decoy content.\n",
        "salary_data.xlsx": "Demo spreadsheet placeholder for the hackathon.\n",
        "employee_records.csv": "name,department,salary\nDemo User,Security,99999\n",
        "confidential_backup.zip": "DEMO ZIP PLACEHOLDER - NOT A REAL ARCHIVE\n",
    }

    for name in HONEYPOT_FILENAMES:
        file_path = watch_path / name
        if not file_path.exists():
            file_path.write_text(templates.get(name, "Demo honeypot file\n"), encoding="utf-8")
            created.append(file_path)

    return created


def is_honeypot_name(file_name: str) -> bool:
    """Return True when a file name matches one of the decoy files or an obvious variant."""
    name = Path(file_name).name.lower()
    for base_name in HONEYPOT_FILENAMES:
        base = base_name.lower()
        if name == base:
            return True
        if name.startswith(base + "."):
            return True
    return False


def is_suspicious_honeypot_extension(file_name: str) -> bool:
    """Detect suspicious ransomware-style extensions appended to honeypot files."""
    name = Path(file_name).name.lower()
    return any(name.endswith(extension) and is_honeypot_name(name[: -len(extension)]) for extension in SUSPICIOUS_EXTENSIONS)


class HoneypotDetector:
    """Track honeypot activity and flag rapid-access bursts."""

    def __init__(self, burst_window_seconds: float = 3.0, burst_threshold: int = 3, cooldown_seconds: float = 5.0) -> None:
        self.burst_window_seconds = float(burst_window_seconds)
        self.burst_threshold = int(burst_threshold)
        self.cooldown_seconds = float(cooldown_seconds)
        self._recent_access: dict[str, Deque[float]] = defaultdict(deque)
        self._last_triggered: dict[str, float] = {}

    def inspect_event(self, event_type: str, src_path: str, dest_path: str | None = None) -> dict | None:
        """Return a honeypot trigger event when a decoy file is touched."""
        candidate_paths = [p for p in (dest_path, src_path) if p]
        matched_path = next((p for p in candidate_paths if is_honeypot_name(p) or is_suspicious_honeypot_extension(p)), None)
        if not matched_path:
            return None

        file_path = Path(matched_path)
        key = str(file_path).lower()
        now = monotonic()

        access_window = self._recent_access[key]
        access_window.append(now)
        while access_window and (now - access_window[0]) > self.burst_window_seconds:
            access_window.popleft()

        if key in self._last_triggered and (now - self._last_triggered[key]) < self.cooldown_seconds:
            return None

        reasons = self._build_reasons(event_type, file_path.name, len(access_window) >= self.burst_threshold)
        self._last_triggered[key] = now

        timestamp = datetime.now(timezone.utc).isoformat()
        description = "; ".join(reasons) if reasons else "Critical sensitive file activity detected"
        details = {
            "honeypot_triggered": True,
            "honeypot_name": file_path.name,
            "event_type": event_type,
            "reasons": reasons,
            "alert_title": "Honeypot File Triggered",
            "alert_description": "Critical sensitive file activity detected",
            "message": description,
            "source": "honeypot_monitor",
        }

        return {
            "event_type": "honeypot_triggered",
            "path": str(file_path),
            "severity": HONEYPOT_SCORE,
            "details": details,
            "created_at": timestamp,
        }

    @staticmethod
    def _build_reasons(event_type: str, file_name: str, rapid_access: bool) -> list[str]:
        reasons = ["honeypot file matched"]
        if is_suspicious_honeypot_extension(file_name):
            reasons.append("suspicious extension appended")
        if event_type == "modified":
            reasons.append("honeypot modified")
        elif event_type == "deleted":
            reasons.append("honeypot deleted")
        elif event_type == "moved":
            reasons.append("honeypot renamed")
        elif event_type == "created":
            reasons.append("honeypot created")
        if rapid_access:
            reasons.append("rapid access pattern")
        return reasons