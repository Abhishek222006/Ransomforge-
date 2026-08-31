from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DB_NAME = "ransomforge.db"


def _resolve_db_path(db_path: Optional[str] = None) -> Path:
    """Resolve the database path. Defaults to `backend/ransomforge.db`.

    The default location keeps the DB inside the `backend` folder so it's
    easy to find during local demos. Pass `db_path` to override for tests.
    """
    if db_path:
        return Path(db_path)
    # place the DB file next to this module's parent (backend/services -> backend)
    base = Path(__file__).resolve().parent.parent
    return base / DEFAULT_DB_NAME


def _dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> Dict[str, Any]:
    """Convert sqlite3.Row to a normal dict for easier consumption."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def init_db(db_path: Optional[str] = None) -> None:
    """Create the database file and required tables if they don't exist.

    Tables created:
    - events: stores live monitoring events
    - alerts: stores high-level alert messages
    """
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        # nicer row access for read helpers
        conn.row_factory = sqlite3.Row
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    file_path TEXT,
                    process_name TEXT,
                    threat_score INTEGER DEFAULT 0,
                    severity INTEGER DEFAULT 0,
                    entropy REAL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity INTEGER DEFAULT 0
                )
                """
            )
        _ensure_entropy_column(conn)
        conn.commit()


def _ensure_entropy_column(conn: sqlite3.Connection) -> None:
    """Add the optional entropy column to older demo databases."""
    with closing(conn.cursor()) as cur:
        cur.execute("PRAGMA table_info(events)")
        columns = {row[1] for row in cur.fetchall()}
        if "entropy" not in columns:
            cur.execute("ALTER TABLE events ADD COLUMN entropy REAL")


def insert_event(
    event_type: str,
    file_path: Optional[str] = None,
    process_name: Optional[str] = None,
    threat_score: int = 0,
    severity: int = 0,
    timestamp: Optional[str] = None,
    entropy: Optional[float] = None,
    db_path: Optional[str] = None,
) -> Optional[int]:
    """Insert a single monitoring event into the `events` table.

    Returns the inserted row id on success, or `None` on error.
    """
    path = _resolve_db_path(db_path)
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    try:
        with sqlite3.connect(path) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    INSERT INTO events (timestamp, event_type, file_path, process_name, threat_score, severity, entropy)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (timestamp, event_type, file_path, process_name, int(threat_score), int(severity), entropy),
                )
                conn.commit()
                return cur.lastrowid
    except Exception:
        # In a hackathon MVP it's preferable to fail gracefully and log.
        return None


def insert_alert(message: str, severity: int = 0, timestamp: Optional[str] = None, db_path: Optional[str] = None) -> Optional[int]:
    """Insert an alert into the `alerts` table.

    Returns the inserted alert id, or `None` on error.
    """
    path = _resolve_db_path(db_path)
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    try:
        with sqlite3.connect(path) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    INSERT INTO alerts (timestamp, message, severity)
                    VALUES (?, ?, ?)
                    """,
                    (timestamp, message, int(severity)),
                )
                conn.commit()
                return cur.lastrowid
    except Exception:
        return None


def get_recent_events(limit: int = 25, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return the most recent events as a list of dictionaries.

    This helper uses `sqlite3.Row` and converts rows to plain dicts so they are
    easy to JSON-serialize for FastAPI responses.
    """
    path = _resolve_db_path(db_path)
    try:
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    SELECT id, timestamp, event_type, file_path, process_name, threat_score, severity, entropy
                    FROM events
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (int(limit),),
                )
                rows = cur.fetchall()

        # convert sqlite3.Row -> dict
        return [dict(r) for r in rows]
    except Exception:
        return []


# Example usage and recommended integration points
if __name__ == "__main__":
    # Quick demo to initialize DB and insert a test event + alert
    init_db()
    eid = insert_event(
        event_type="demo",
        file_path="/tmp/suspicious.bin",
        process_name="evil.exe",
        threat_score=85,
        severity=2,
    )
    aid = insert_alert("Demo alert: suspicious activity detected", severity=2)

    print(f"Inserted event id: {eid}")
    print(f"Inserted alert id: {aid}")
    print("Recent events:", get_recent_events(10))

    # Recommended integration points:
    # - Call `init_db()` during FastAPI startup (lifespan) so the DB exists.
    # - Use `insert_event()` from the watchdog handler when an event is detected.
    # - Use `insert_alert()` when raising a high-severity alert to persist it.
    # - Use `get_recent_events()` inside a FastAPI route to return recent events to the frontend.
