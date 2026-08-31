from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Set

from fastapi import WebSocket


ALLOWED_EVENT_TYPES = {
    "NEW_EVENT",
    "ALERT",
    "THREAT_UPDATE",
    "SCAN_STARTED",
    "SCAN_PROGRESS",
    "SCAN_COMPLETED",
    "NETWORK_ISOLATED",
    "QUARANTINE_TRIGGERED",
    "ISOLATION_TRIGGERED",
    "ISOLATION_RELEASED",
    "RECOVERY_CREATED",
    "RECOVERY_RESTORED",
    "RECOVERY_FAILED",
}


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._recent_event_signatures: dict[str, float] = {}
        self._recent_signature_window_seconds = 0.75

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections.add(websocket)
        print(f"[ws] client connected: {id(websocket)}")

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            self._connections.discard(websocket)
        print(f"[ws] client disconnected: {id(websocket)}")

    def broadcast(self, message: dict) -> None:
        if self._loop is None:
            print("[ws] broadcast failed: event loop is unavailable")
            return

        future = asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)

        def _log_result(result_future: asyncio.Future) -> None:
            try:
                result_future.result()
            except Exception as error:
                print(f"[ws] broadcast failed: {error}")

        future.add_done_callback(_log_result)

    async def broadcast_async(self, message: dict) -> None:
        """Broadcast from inside the running event loop.

        This is used by the realtime demo broadcaster in `main.py`.
        """
        await self._broadcast(message)

    async def _broadcast(self, message: dict) -> None:
        if not self._validate_message(message):
            return

        signature = self._message_signature(message)
        if self._should_suppress(signature):
            return

        with self._lock:
            connections = list(self._connections)

        if not connections:
            return

        delivered_count = 0
        for connection in connections:
            try:
                await connection.send_json(message)
                delivered_count += 1
            except Exception:
                self.disconnect(connection)

        if delivered_count > 0:
            print(f"[ws] broadcast sent: {message.get('type', 'unknown')} recipients={delivered_count}")
        else:
            print(f"[ws] broadcast failed: {message.get('type', 'unknown')} delivered_to=0")

    def _validate_message(self, message: dict[str, Any]) -> bool:
        if not isinstance(message, dict):
            print("[ws] broadcast failed: invalid payload type")
            return False

        event_type = message.get("type")
        if event_type not in ALLOWED_EVENT_TYPES:
            print(f"[ws] broadcast failed: unsupported event type {event_type!r}")
            return False

        payload = message.get("data") or message.get("payload") or {}
        if not isinstance(payload, dict):
            print(f"[ws] broadcast failed: invalid payload shape for {event_type}")
            return False

        return True

    def _message_signature(self, message: dict[str, Any]) -> str:
        payload = message.get("payload") or message.get("data") or {}
        try:
            payload_text = json.dumps(payload, sort_keys=True, default=str)
        except Exception:
            payload_text = str(payload)
        return f"{message.get('type')}::{payload_text}"

    def _should_suppress(self, signature: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        with self._lock:
            last_seen = self._recent_event_signatures.get(signature)
            self._recent_event_signatures[signature] = now
            stale_signatures = [
                key for key, timestamp in self._recent_event_signatures.items()
                if (now - timestamp) > 10.0
            ]
            for key in stale_signatures:
                self._recent_event_signatures.pop(key, None)

        if last_seen is None:
            return False

        return (now - last_seen) < self._recent_signature_window_seconds

    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(self._connections)
