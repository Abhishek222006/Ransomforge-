from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SQLiteEventStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout = 30000")
        except sqlite3.Error:
            pass
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    severity INTEGER NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    directory TEXT,
                    snapshot_path TEXT,
                    file_count INTEGER,
                    size_bytes INTEGER,
                    status TEXT,
                    snapshot_status TEXT,
                    restore_status TEXT,
                    restore_timestamp TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    snapshot_id INTEGER,
                    status TEXT,
                    message TEXT,
                    details TEXT
                )
                """
            )
            connection.commit()

    def record_event(self, event: dict[str, Any]) -> None:
        created_at = event.get("created_at") or datetime.now(timezone.utc).isoformat()
        details = json.dumps(event.get("details", {}), default=str)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO security_events (event_type, path, severity, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.get("event_type", "unknown"),
                    event.get("path", ""),
                    int(event.get("severity", 0)),
                    details,
                    created_at,
                ),
            )
            connection.commit()

    def recent_events(self, limit: int = 25) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_type, path, severity, details, created_at
                FROM security_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        events: list[dict[str, Any]] = []
        for event_type, path, severity, details, created_at in rows:
            events.append(
                {
                    "event_type": event_type,
                    "path": path,
                    "severity": severity,
                    "details": json.loads(details),
                    "created_at": created_at,
                }
            )
        return events

    def recent_process_events(self, limit: int = 25) -> list[dict[str, Any]]:
        """Return the most recent process anomaly events.

        This keeps the dashboard refresh-friendly by loading suspicious process
        history directly from the existing SQLite event log.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT details, created_at, severity
                FROM security_events
                WHERE event_type = 'process_anomaly'
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

        process_events: list[dict[str, Any]] = []
        for details, created_at, severity in rows:
            try:
                parsed_details = json.loads(details) if details else {}
            except json.JSONDecodeError:
                parsed_details = {}

            process_events.append(
                {
                    "timestamp": created_at,
                    "process_name": parsed_details.get("process_name"),
                    "pid": parsed_details.get("pid"),
                    "cpu_percent": parsed_details.get("cpu_percent", 0),
                    "memory_percent": parsed_details.get("memory_percent", 0),
                    "io_read_bytes": parsed_details.get("io_read_bytes", 0),
                    "io_write_bytes": parsed_details.get("io_write_bytes", 0),
                    "child_process_count": parsed_details.get("child_process_count", 0),
                    "threat_score": parsed_details.get("score", severity),
                    "severity": parsed_details.get("severity"),
                    "reasons": parsed_details.get("reasons", []),
                }
            )

        return process_events
