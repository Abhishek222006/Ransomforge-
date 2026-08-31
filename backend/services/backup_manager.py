from __future__ import annotations

"""Lightweight backup snapshot helpers for the RansomForge demo.

This module keeps the implementation intentionally small and local-only:
- snapshots are stored under C:/RansomGuard/backups/
- only the monitored runtime_watch/ folder is copied
- restore renames the current runtime_watch folder before replacing it
- the scheduler runs in a daemon thread every few minutes

The goal is safe, one-click recovery for a hackathon dashboard, not a full
enterprise backup system.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any
import shutil
import sqlite3
import uuid


BASE_DIR = Path(__file__).resolve().parent.parent
MONITORED_DIR = BASE_DIR.parent / "runtime_watch"
BACKUP_ROOT = Path("C:/RansomGuard/backups")
DB_PATH = BASE_DIR / "ransomforge.db"
BACKUP_OPERATION_LOCK = Lock()


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection to the shared RansomForge database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout = 30000")
    except sqlite3.Error:
        pass
    _ensure_schema(connection)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    with connection:
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
        _ensure_columns(connection, "backups", {
            "snapshot_status": "TEXT",
            "restore_status": "TEXT",
            "restore_timestamp": "TEXT",
        })


def _ensure_columns(connection: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def _count_files_and_size(directory: Path) -> tuple[int, int]:
    file_count = 0
    size_bytes = 0
    if not directory.exists():
        return file_count, size_bytes

    for path in directory.rglob("*"):
        if path.is_file():
            file_count += 1
            try:
                size_bytes += path.stat().st_size
            except OSError:
                pass
    return file_count, size_bytes


def _snapshot_name(timestamp: str) -> str:
    safe_timestamp = timestamp.replace(":", "-")
    return f"snapshot_{safe_timestamp}_{uuid.uuid4().hex[:8]}"


def _normalize_timestamp(value: Any) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat()
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _record_recovery_event(
    event_type: str,
    snapshot_id: int | None,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> None:
    payload = details or {}
    with get_db() as connection:
        connection.execute(
            """
            INSERT INTO recovery_events (timestamp, event_type, snapshot_id, status, message, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _normalize_timestamp(timestamp),
                event_type,
                snapshot_id,
                status,
                message,
                json.dumps(payload, default=str),
            ),
        )
        connection.commit()


class _BackupOperationGuard:
    def __init__(self, operation: str) -> None:
        self.operation = operation
        self.acquired = False

    def __enter__(self) -> "_BackupOperationGuard":
        self.acquired = BACKUP_OPERATION_LOCK.acquire(blocking=False)
        if not self.acquired:
            raise RuntimeError(f"Backup operation already running: {self.operation}")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.acquired:
            BACKUP_OPERATION_LOCK.release()




def _cleanup_directory(directory: Path) -> None:
    if not directory.exists():
        return
    if directory.is_file() or directory.is_symlink():
        directory.unlink(missing_ok=True)
        return
    shutil.rmtree(directory, ignore_errors=False)


def _prepare_restore_destination() -> None:
    """Move the current monitored folder aside before restoring a clean copy."""
    MONITORED_DIR.parent.mkdir(parents=True, exist_ok=True)
    if not MONITORED_DIR.exists():
        return

    infected_name = MONITORED_DIR.parent / f"runtime_watch_infected_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    suffix_index = 1
    while infected_name.exists():
        infected_name = MONITORED_DIR.parent / f"runtime_watch_infected_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{suffix_index}"
        suffix_index += 1

    try:
        MONITORED_DIR.rename(infected_name)
        print(f"[restore] runtime_watch quarantined -> {infected_name}")
    except (PermissionError, FileExistsError, OSError):
        print("[restore] unable to quarantine runtime_watch cleanly; continuing with restore retry")


def _copy_snapshot_to_watch(snapshot_path: Path) -> None:
    """Copy a snapshot into the monitored folder with a Windows-safe retry."""
    try:
        shutil.copytree(snapshot_path, MONITORED_DIR, dirs_exist_ok=True)
        return
    except (FileExistsError, PermissionError, OSError) as primary_error:
        print(f"[restore] first restore attempt failed: {primary_error}")

    try:
        _cleanup_directory(MONITORED_DIR)
    except Exception as cleanup_error:
        raise RuntimeError(f"Unable to clear runtime_watch for restore: {cleanup_error}") from cleanup_error

    shutil.copytree(snapshot_path, MONITORED_DIR, dirs_exist_ok=True)


def create_snapshot(status: str = "clean") -> dict[str, Any]:
    """Create a versioned snapshot of runtime_watch/ and log it in SQLite."""
    print("[backup] snapshot started")
    with _BackupOperationGuard("snapshot"):
        try:
            BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
            MONITORED_DIR.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(timezone.utc).isoformat()
            snapshot_path = BACKUP_ROOT / _snapshot_name(timestamp)

            if snapshot_path.exists():
                shutil.rmtree(snapshot_path)

            shutil.copytree(MONITORED_DIR, snapshot_path)
            file_count, size_bytes = _count_files_and_size(snapshot_path)

            with get_db() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO backups (timestamp, directory, snapshot_path, file_count, size_bytes, status, snapshot_status, restore_status, restore_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (timestamp, str(MONITORED_DIR), str(snapshot_path), file_count, size_bytes, status, status, None, None),
                )
                backup_id = cursor.lastrowid
                connection.commit()

            print(f"[backup] snapshot completed: id={backup_id} path={snapshot_path}")
            _record_recovery_event(
                event_type="snapshot_created",
                snapshot_id=backup_id,
                status="success",
                message="Clean snapshot created",
                details={
                    "directory": str(MONITORED_DIR),
                    "snapshot_path": str(snapshot_path),
                    "file_count": file_count,
                    "size_bytes": size_bytes,
                    "snapshot_status": status,
                },
                timestamp=timestamp,
            )
            return {
                "id": backup_id,
                "timestamp": timestamp,
                "directory": str(MONITORED_DIR),
                "snapshot_path": str(snapshot_path),
                "file_count": file_count,
                "size_bytes": size_bytes,
                "status": status,
            }
        except Exception as error:
            print(f"[backup] snapshot failed: {error}")
            _record_recovery_event(
                event_type="snapshot_created",
                snapshot_id=None,
                status="failed",
                message=str(error),
                details={"directory": str(MONITORED_DIR), "snapshot_status": status},
            )
            raise


def get_all_backups() -> list[dict[str, Any]]:
    """Return all stored backup snapshots ordered by newest first."""
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT id, timestamp, directory, snapshot_path, file_count, size_bytes, status, snapshot_status, restore_status, restore_timestamp
            FROM backups
            ORDER BY id DESC
            """
        ).fetchall()

    backups: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["id"] = int(item["id"])
        item["timestamp"] = _normalize_timestamp(item.get("timestamp"))
        item["directory"] = str(item.get("directory") or MONITORED_DIR)
        item["snapshot_path"] = str(item.get("snapshot_path") or "")
        item["file_count"] = int(item.get("file_count") or 0)
        item["size_bytes"] = int(item.get("size_bytes") or 0)
        item["status"] = item.get("status") or "unknown"
        item["snapshot_status"] = item.get("snapshot_status") or item["status"]
        item["restore_status"] = item.get("restore_status") or None
        item["restore_timestamp"] = _normalize_timestamp(item.get("restore_timestamp")) if item.get("restore_timestamp") else None
        backups.append(item)
    return backups


def get_last_clean_backup() -> dict[str, Any] | None:
    """Return the newest clean backup snapshot, if any."""
    with get_db() as connection:
        row = connection.execute(
            """
            SELECT id, timestamp, directory, snapshot_path, file_count, size_bytes, status, snapshot_status, restore_status, restore_timestamp
            FROM backups
            WHERE status = 'clean'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if not row:
        return None

    backup = dict(row)
    backup["id"] = int(backup["id"])
    backup["timestamp"] = _normalize_timestamp(backup.get("timestamp"))
    backup["directory"] = str(backup.get("directory") or MONITORED_DIR)
    backup["snapshot_path"] = str(backup.get("snapshot_path") or "")
    backup["file_count"] = int(backup.get("file_count") or 0)
    backup["size_bytes"] = int(backup.get("size_bytes") or 0)
    backup["status"] = backup.get("status") or "clean"
    backup["snapshot_status"] = backup.get("snapshot_status") or backup["status"]
    backup["restore_status"] = backup.get("restore_status") or None
    backup["restore_timestamp"] = _normalize_timestamp(backup.get("restore_timestamp")) if backup.get("restore_timestamp") else None
    return backup


def restore_from_backup(backup_id: int) -> dict[str, Any]:
    """Restore runtime_watch/ from a stored snapshot after quarantining the current folder."""
    print("[backup] restore started")
    with _BackupOperationGuard("restore"):
        try:
            print(f"[restore] backup selected: {backup_id}")
            with get_db() as connection:
                row = connection.execute(
                    """
                    SELECT id, timestamp, directory, snapshot_path, file_count, size_bytes, status, snapshot_status, restore_status, restore_timestamp
                    FROM backups
                    WHERE id = ?
                    """,
                    (int(backup_id),),
                ).fetchone()

            if row is None:
                raise ValueError(f"Backup {backup_id} not found")

            backup = dict(row)
            snapshot_path_value = str(backup.get("snapshot_path") or "").strip()
            if not snapshot_path_value:
                raise ValueError(f"Backup {backup_id} has invalid snapshot metadata")

            snapshot_path = Path(snapshot_path_value)
            if not snapshot_path.exists() or not snapshot_path.is_dir():
                raise FileNotFoundError(f"Snapshot path missing or invalid: {snapshot_path}")

            print(f"[restore] restoring snapshot: {snapshot_path}")
            _prepare_restore_destination()
            _copy_snapshot_to_watch(snapshot_path)

            restored_at = datetime.now(timezone.utc).isoformat()
            with get_db() as connection:
                connection.execute(
                    """
                    UPDATE backups
                    SET restore_status = ?, restore_timestamp = ?
                    WHERE id = ?
                    """,
                    ("success", restored_at, int(backup_id)),
                )
                connection.commit()

            print(f"[backup] restore completed: snapshot id={backup_id}")
            _record_recovery_event(
                event_type="snapshot_restored",
                snapshot_id=int(backup_id),
                status="success",
                message="Snapshot restored successfully",
                details={
                    "restored_path": str(MONITORED_DIR),
                    "source_snapshot": str(snapshot_path),
                },
                timestamp=restored_at,
            )
            return {
                "success": True,
                "message": "Snapshot restored successfully",
                "backup_id": int(backup_id),
                "restored_path": str(MONITORED_DIR),
                "source_snapshot": str(snapshot_path),
            }
        except Exception as error:
            print(f"[backup] restore failed: {error}")
            try:
                with get_db() as connection:
                    connection.execute(
                        """
                        UPDATE backups
                        SET restore_status = ?, restore_timestamp = ?
                        WHERE id = ?
                        """,
                        ("failed", datetime.now(timezone.utc).isoformat(), int(backup_id)),
                    )
                    connection.commit()
            except Exception:
                pass
            record_restore_failure(int(backup_id) if str(backup_id).isdigit() else None, str(error), {"backup_id": backup_id})
            return {
                "success": False,
                "error": str(error),
            }


def get_recovery_logs(limit: int = 100) -> list[dict[str, Any]]:
    """Return recovery event logs ordered by newest first."""
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT id, timestamp, event_type, snapshot_id, status, message, details
            FROM recovery_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    logs: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["id"] = int(item["id"])
        item["timestamp"] = _normalize_timestamp(item.get("timestamp"))
        item["snapshot_id"] = int(item["snapshot_id"]) if item.get("snapshot_id") is not None else None
        item["status"] = item.get("status") or "unknown"
        item["message"] = item.get("message") or ""
        try:
            item["details"] = json.loads(item.get("details") or "{}")
        except json.JSONDecodeError:
            item["details"] = {"raw": item.get("details")}
        logs.append(item)
    return logs


def record_restore_failure(snapshot_id: int | None, message: str, details: dict[str, Any] | None = None) -> None:
    """Persist a failed recovery attempt for the logs API."""
    _record_recovery_event(
        event_type="snapshot_restore_failed",
        snapshot_id=snapshot_id,
        status="failed",
        message=message,
        details=details or {},
    )


def auto_snapshot_scheduler(interval_minutes: int = 5) -> Thread:
    """Run snapshot creation in a daemon thread every few minutes."""
    stop_event = Event()
    interval_seconds = max(60, int(interval_minutes) * 60)

    def _runner() -> None:
        while not stop_event.is_set():
            # Wait for the interval BEFORE creating the first snapshot
            # This prevents the automatic snapshot on backend startup/reload
            if stop_event.wait(interval_seconds):
                break
            try:
                create_snapshot(status="clean")
            except Exception:
                pass

    thread = Thread(target=_runner, name="ransomforge-auto-snapshot", daemon=True)
    thread.start()
    setattr(thread, "stop_event", stop_event)
    return thread
