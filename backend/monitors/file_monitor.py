from __future__ import annotations

from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

try:
    from ..detection.rules import HoneypotDetector, should_analyze_entropy
    from ..detection.threat_scoring import analyze_file_entropy, score_file_event_details
except ImportError:
    from detection.rules import HoneypotDetector, should_analyze_entropy
    from detection.threat_scoring import analyze_file_entropy, score_file_event_details


IGNORED_PARTS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


class FileMonitorService:
    def __init__(self, watch_path: Path, on_event: Callable[[dict], None]) -> None:
        self.watch_path = Path(watch_path)
        self.on_event = on_event
        self.honeypot_detector = HoneypotDetector()
        self.observer = Observer()

    def start(self) -> None:
        if not self.watch_path.exists():
            return

        handler = _SecurityEventHandler(self.on_event, self.honeypot_detector)
        self.observer.schedule(handler, str(self.watch_path), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=3)


class _SecurityEventHandler(FileSystemEventHandler):
    def __init__(self, on_event: Callable[[dict], None], honeypot_detector: HoneypotDetector) -> None:
        self.on_event = on_event
        self.honeypot_detector = honeypot_detector

    def on_created(self, event):
        self._handle_event("created", event.src_path)

    def on_modified(self, event):
        self._handle_event("modified", event.src_path)

    def on_deleted(self, event):
        self._handle_event("deleted", event.src_path)

    def on_moved(self, event):
        self._handle_event("moved", event.src_path, getattr(event, "dest_path", None))

    def _handle_event(self, event_type: str, src_path: str, dest_path: str | None = None) -> None:
        honeypot_event = self.honeypot_detector.inspect_event(event_type, src_path, dest_path)
        if honeypot_event is not None:
            self.on_event(honeypot_event)
            return

        file_path = Path(dest_path or src_path)
        if self._should_ignore(file_path):
            return

        entropy_analysis = self._analyze_entropy(event_type, file_path)
        score_details = score_file_event_details(str(file_path), event_type, entropy=entropy_analysis.get("entropy"))

        event = {
            "event_type": event_type,
            "path": str(file_path),
            "severity": score_details["score"],
            "details": {
                "source": "watchdog",
                "filename": file_path.name,
                "reasons": score_details["reasons"],
                "entropy": score_details["entropy"],
                "entropy_level": score_details["entropy_level"],
                "entropy_bonus": score_details["entropy_bonus"],
            },
        }
        self.on_event(event)

    @staticmethod
    def _should_ignore(file_path: Path) -> bool:
        return any(part in IGNORED_PARTS for part in file_path.parts)

    @staticmethod
    def _analyze_entropy(event_type: str, file_path: Path) -> dict:
        # Entropy is a useful ransomware signal because encrypted files often
        # look random. We keep this best-effort and local-only so the realtime
        # detector stays fast and beginner-friendly.
        if not should_analyze_entropy(event_type, str(file_path)):
            return {"entropy": None, "entropy_level": "unknown", "entropy_bonus": 0, "entropy_reasons": []}

        return analyze_file_entropy(str(file_path))
