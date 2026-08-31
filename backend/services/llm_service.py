from __future__ import annotations

from collections import deque
import os
from threading import Lock
from typing import Any
from uuid import uuid4

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
_MAX_HISTORY_MESSAGES = 12

_SESSION_HISTORY: dict[str, deque[dict[str, str]]] = {}
_SESSION_LOCK = Lock()


def get_or_create_session_id(session_id: str | None) -> str:
    if session_id:
        return session_id
    return uuid4().hex


def get_session_history(session_id: str) -> list[dict[str, str]]:
    with _SESSION_LOCK:
        history = _SESSION_HISTORY.get(session_id)
        if history is None:
            return []
        return list(history)


def append_session_turn(session_id: str, user_message: str, assistant_reply: str) -> None:
    with _SESSION_LOCK:
        history = _SESSION_HISTORY.get(session_id)
        if history is None:
            history = deque(maxlen=_MAX_HISTORY_MESSAGES)
            _SESSION_HISTORY[session_id] = history

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_reply})


def build_system_prompt() -> str:
    return (
        "You are a defensive-only cybersecurity incident response assistant for a hackathon demo. "
        "Explain ransomware alerts in beginner-friendly language. "
        "Be concise, practical, and calm. "
        "Describe what happened, why the alert triggered, what quarantine means, what to do next, "
        "how to recover safely, and containment recommendations. "
        "Never provide offensive hacking steps, destructive commands, or instructions to disable security tools."
    )


def build_context_message(context: dict[str, Any]) -> str:
    return (
        f"Current threat score: {context.get('threat_score', 0)}\n"
        f"Current severity: {context.get('severity', 'low')}\n"
        f"Quarantine status: {context.get('quarantine_status', {})}\n"
        f"Recovery state: {context.get('recovery_state', {})}\n"
        f"Recent alerts: {context.get('recent_alerts', [])}\n"
        f"Recent events: {context.get('recent_events', [])}"
    )


def build_messages(user_message: str, context: dict[str, Any], history: list[dict[str, str]]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "system", "content": f"Use this local incident context when helpful:\n{build_context_message(context)}"},
    ]
    messages.extend(history[-_MAX_HISTORY_MESSAGES:])
    messages.append({"role": "user", "content": user_message})
    return messages


def get_openrouter_model() -> str:
    return os.getenv("OPENROUTER_MODEL", OPENROUTER_MODEL).strip() or OPENROUTER_MODEL


async def request_openrouter_chat(
    *,
    api_key: str,
    messages: list[dict[str, str]],
    timeout_seconds: float = 20.0,
    model: str | None = None,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "RansomForge Incident Response Assistant",
    }
    body = {
        "model": model or get_openrouter_model(),
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 350,
    }

    timeout = httpx.Timeout(timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=body)
    except httpx.TimeoutException as exc:
        raise TimeoutError("OpenRouter request timed out") from exc
    except httpx.RequestError as exc:
        raise RuntimeError("OpenRouter request failed") from exc

    if response.status_code >= 400:
        raise RuntimeError(f"OpenRouter returned {response.status_code}")

    data = response.json()
    reply = data["choices"][0]["message"]["content"]
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError("OpenRouter returned an empty response")
    return reply.strip()
