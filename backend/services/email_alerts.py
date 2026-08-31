from __future__ import annotations

"""Email alert helper for the RansomForge demo.

Every email is built from the *actual* real-time event data so that each
message the analyst receives reflects what genuinely happened:
  - subject   encodes severity tier, score, and what was hit
  - body      shows event type, file/process context, reasons list,
              entropy value, honeypot flag, and a tier-appropriate
              recommended-action block
  - dedup     buckets by event_type + severity tier (not exact score) so
              a burst of similar events only fires one email per cooldown
              window; meaningfully different events (honeypot, process, etc.)
              always get their own email
"""

from datetime import datetime, timezone
import html
import json
import os
from threading import Lock
from time import monotonic
from typing import Any

try:
    import resend
except ImportError:  # pragma: no cover
    resend = None


# ── Cooldown windows per severity tier ────────────────────────────────────────
_COOLDOWN_BY_TIER: dict[str, float] = {
    "critical": 45.0,   # critical fires at most once per 45 s per bucket
    "high":     90.0,   # high fires at most once per 90 s per bucket
}
_DEFAULT_COOLDOWN = 120.0

_RECENT_BUCKETS: dict[str, float] = {}
_BUCKET_LOCK = Lock()


# ── Normalisation helpers ──────────────────────────────────────────────────────

def _norm(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, default=str, sort_keys=True)
        except Exception:
            return str(value)
    return str(value)


def _normalize_severity(event_data: dict[str, Any]) -> tuple[str, int]:
    sev = event_data.get("severity", "")
    raw_score = event_data.get("score", event_data.get("threat_score", 0))

    if isinstance(sev, str) and sev.strip().lower() in {"low", "medium", "high", "critical"}:
        severity = sev.strip().lower()
    else:
        try:
            s = int(raw_score)
        except Exception:
            s = 0
        if s >= 85:
            severity = "critical"
        elif s >= 65:
            severity = "high"
        elif s >= 35:
            severity = "medium"
        else:
            severity = "low"

    try:
        score = int(raw_score)
    except Exception:
        score = 0

    return severity, score


# ── Deduplication ─────────────────────────────────────────────────────────────

def _make_bucket(event_data: dict[str, Any], severity: str) -> str:
    """Bucket key: event_type + severity tier + whether it's a honeypot/process/file alert.

    Using exact score is intentionally avoided — score changes every loop tick
    which would let near-identical emails through on every tick.
    """
    event_type = _norm(event_data.get("event_type") or "unknown").lower()
    honeypot   = "honeypot" if event_data.get("honeypot_triggered") else "normal"
    has_proc   = "proc" if event_data.get("process_name") else "file"
    # For demo loop events the source distinguishes them from real file-system events
    source     = _norm(event_data.get("source") or event_data.get("trigger_source") or "").lower()[:20]
    return f"{event_type}:{severity}:{honeypot}:{has_proc}:{source}"


def _should_suppress(bucket: str, severity: str) -> bool:
    cooldown = _COOLDOWN_BY_TIER.get(severity, _DEFAULT_COOLDOWN)
    now = monotonic()
    with _BUCKET_LOCK:
        last = _RECENT_BUCKETS.get(bucket)
        # Evict old entries so the dict doesn't grow forever
        stale = [k for k, t in _RECENT_BUCKETS.items() if (now - t) > 300]
        for k in stale:
            _RECENT_BUCKETS.pop(k, None)
        if last is not None and (now - last) < cooldown:
            return True
        _RECENT_BUCKETS[bucket] = now
        return False


# ── Dynamic content builders ──────────────────────────────────────────────────

_EVENT_TYPE_LABELS: dict[str, str] = {
    "demo_ransomware_alert":   "Ransomware Simulation",
    "honeypot_accessed":       "Honeypot File Accessed",
    "file_encrypted":          "File Encryption Detected",
    "file_renamed_suspicious": "Suspicious File Rename",
    "mass_rename":             "Mass File Rename",
    "process_anomaly":         "Suspicious Process",
    "quarantine_triggered":    "System Quarantined",
    "network_isolated":        "Network Isolation Activated",
    "modified":                "File Modified",
    "created":                 "File Created",
    "deleted":                 "File Deleted",
    "moved":                   "File Moved",
}


def _event_label(event_type: str) -> str:
    return _EVENT_TYPE_LABELS.get(event_type.lower(), event_type.replace("_", " ").title())


def _score_band_label(score: int) -> str:
    if score >= 95:
        return "Extreme"
    if score >= 85:
        return "Critical"
    if score >= 75:
        return "Very High"
    if score >= 65:
        return "High"
    return "Elevated"


def _build_description(event_data: dict[str, Any], severity: str, score: int) -> str:
    """Compose a human-readable one-line summary that varies with the event."""
    event_type  = _norm(event_data.get("event_type") or "unknown")
    label       = _event_label(event_type)
    band        = _score_band_label(score)
    file_path   = _norm(event_data.get("file_path") or "")
    proc        = _norm(event_data.get("process_name") or "")
    honeypot    = event_data.get("honeypot_triggered", False)
    reasons     = event_data.get("reasons") or []

    if honeypot:
        target = f"honeypot file {file_path or '(unknown)'}"
        return f"{band}-risk honeypot access: {target}. Immediate investigation required."

    if proc:
        return (
            f"{band}-risk process anomaly detected — {proc} triggered a {label.lower()} "
            f"event with threat score {score}."
        )

    if reasons and isinstance(reasons, list):
        top = "; ".join(str(r) for r in reasons[:3])
        return f"{band}-risk {label.lower()} (score {score}). Reasons: {top}."

    if file_path:
        fname = file_path.split("/")[-1].split("\\")[-1]
        return f"{band}-risk {label.lower()} on '{fname}' — threat score {score}."

    return f"{band}-risk ransomware indicator detected — {label} (score {score})."


def _build_recommendations(severity: str, event_data: dict[str, Any]) -> str:
    """Return a tier-appropriate recommended action block."""
    honeypot = event_data.get("honeypot_triggered", False)
    event_type = _norm(event_data.get("event_type") or "")
    is_process = bool(event_data.get("process_name"))
    is_quarantine = "quarantine" in event_type or "isolated" in event_type

    if is_quarantine:
        return (
            "System has been quarantined. Verify quarantine state in the RansomForge dashboard, "
            "review the isolation timeline, and restore from the most recent clean snapshot once "
            "the threat vector is confirmed."
        )
    if honeypot:
        return (
            "A honeypot file was accessed — this is a strong indicator of active ransomware. "
            "Immediately isolate the affected host, terminate the offending process, and restore "
            "system state from a verified clean backup."
        )
    if severity == "critical":
        return (
            "CRITICAL: Isolate the affected host NOW. Terminate the suspicious process if identified. "
            "Do NOT reboot — preserve memory artefacts for forensics. Restore from the latest "
            "clean snapshot via the Recovery Center."
        )
    if severity == "high" and is_process:
        return (
            "Suspicious process detected at high risk. Verify the process legitimacy, check its "
            "parent tree, and terminate if unauthorised. Consider network isolation while "
            "investigation is in progress."
        )
    if severity == "high":
        return (
            "High-risk file activity detected. Review the affected path immediately, check for "
            "extension changes or entropy spikes, and run a full system scan. If activity is "
            "ongoing, activate network isolation from the dashboard."
        )
    return (
        "Elevated threat activity detected. Review the event in the RansomForge Live Feed, "
        "verify system integrity, and create a fresh snapshot if the system appears clean."
    )


def _build_subject(event_data: dict[str, Any], severity: str, score: int) -> str:
    event_type = _norm(event_data.get("event_type") or "unknown")
    label      = _event_label(event_type)
    band       = _score_band_label(score)
    honeypot   = event_data.get("honeypot_triggered", False)

    target = (
        _norm(event_data.get("file_path") or "")
        or _norm(event_data.get("process_name") or "")
        or _norm(event_data.get("title") or "")
        or "incident"
    )
    # Keep subject concise: use just the filename
    short_target = target.split("/")[-1].split("\\")[-1][:40]
    honeypot_tag = " 🍯 HONEYPOT" if honeypot else ""

    return (
        f"[RansomForge] {severity.upper()} | {band} threat{honeypot_tag} "
        f"— {label} | score {score} | {short_target}"
    )


def _render_reasons(reasons: Any) -> str:
    if not reasons:
        return "—"
    if isinstance(reasons, list):
        return "; ".join(str(r) for r in reasons) or "—"
    return _norm(reasons) or "—"


def _build_html(event_data: dict[str, Any], severity: str, score: int) -> str:
    ts          = html.escape(_norm(event_data.get("timestamp") or datetime.now(timezone.utc).isoformat()))
    event_type  = html.escape(_event_label(_norm(event_data.get("event_type") or "unknown")))
    description = html.escape(_build_description(event_data, severity, score))
    file_path   = html.escape(_norm(event_data.get("file_path") or "—"))
    proc        = html.escape(_norm(event_data.get("process_name") or "—"))
    source      = html.escape(_norm(event_data.get("source") or event_data.get("trigger_source") or "—"))
    band        = html.escape(_score_band_label(score))
    entropy_val = event_data.get("entropy")
    entropy     = html.escape(f"{entropy_val:.3f}" if isinstance(entropy_val, float) else _norm(entropy_val) or "—")
    honeypot    = event_data.get("honeypot_triggered", False)
    honeypot_txt= html.escape("YES ⚠️" if honeypot else "No")
    pid_val     = event_data.get("pid")
    pid         = html.escape(_norm(pid_val) if pid_val is not None else "—")
    cpu         = event_data.get("cpu_percent")
    mem         = event_data.get("memory_percent")
    cpu_txt     = html.escape(f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else "—")
    mem_txt     = html.escape(f"{mem:.1f}%" if isinstance(mem, (int, float)) else "—")
    reasons_txt = html.escape(_render_reasons(event_data.get("reasons")))
    recommendation = html.escape(_build_recommendations(severity, event_data))

    # Severity badge colours
    badge_bg = {"critical": "#dc2626", "high": "#d97706"}.get(severity, "#3b82f6")

    process_rows = ""
    if event_data.get("process_name"):
        process_rows = f"""
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;width:160px;">PID</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{pid}</td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">CPU Usage</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{cpu_txt}</td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">Memory Usage</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{mem_txt}</td></tr>"""

    entropy_row = ""
    if entropy != "—":
        entropy_row = f"""<tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;width:160px;">Entropy</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{entropy}</td></tr>"""

    return f"""
<html>
  <body style="font-family:Arial,sans-serif;color:#0f172a;line-height:1.5;">
    <div style="max-width:720px;margin:0 auto;padding:24px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;">

      <!-- Header -->
      <div style="background:#0f172a;color:white;padding:18px 20px;border-radius:10px;margin-bottom:18px;">
        <div style="font-size:20px;font-weight:700;">RansomForge SOC — Incident Alert</div>
        <div style="margin-top:6px;">
          <span style="background:{badge_bg};color:white;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700;letter-spacing:1px;">{severity.upper()}</span>
          &nbsp;<span style="font-size:13px;opacity:0.85;">{band} threat — score {score}/100</span>
        </div>
      </div>

      <!-- Description -->
      <p style="font-size:15px;margin-top:0;margin-bottom:18px;">{description}</p>

      <!-- Event table -->
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;width:160px;">Event Type</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{event_type}</td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">Severity</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;"><b style="color:{badge_bg};">{severity.upper()}</b></td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">Threat Score</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;"><b>{score} / 100</b></td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">File Path</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-family:monospace;font-size:12px;">{file_path}</td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">Process Name</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{proc}</td></tr>
        {process_rows}
        {entropy_row}
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">Honeypot Hit</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{honeypot_txt}</td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">Source</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{source}</td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">Detection Reasons</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;">{reasons_txt}</td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-weight:700;">Timestamp (UTC)</td><td style="padding:8px 0;border-top:1px solid #cbd5e1;font-family:monospace;font-size:12px;">{ts}</td></tr>
      </table>

      <!-- Recommended action -->
      <div style="margin-top:20px;padding:14px 16px;background:#fefce8;border:1px solid #fde047;border-radius:8px;">
        <div style="font-weight:700;font-size:13px;margin-bottom:4px;">&#9888; Recommended Action</div>
        <div style="font-size:13px;color:#334155;">{recommendation}</div>
      </div>

      <p style="margin-top:16px;font-size:11px;color:#94a3b8;">
        RansomForge · Hackathon SOC Demo · Alert generated at {ts}
      </p>
    </div>
  </body>
</html>"""


def _build_text(event_data: dict[str, Any], severity: str, score: int) -> str:
    lines = [
        "=" * 60,
        "RansomForge SOC — Incident Alert",
        f"Severity  : {severity.upper()}  |  Score: {score}/100  ({_score_band_label(score)})",
        "=" * 60,
        "",
        _build_description(event_data, severity, score),
        "",
        f"Event Type    : {_event_label(_norm(event_data.get('event_type') or 'unknown'))}",
        f"File Path     : {_norm(event_data.get('file_path') or '—')}",
        f"Process Name  : {_norm(event_data.get('process_name') or '—')}",
        f"Honeypot Hit  : {'YES' if event_data.get('honeypot_triggered') else 'No'}",
        f"Source        : {_norm(event_data.get('source') or event_data.get('trigger_source') or '—')}",
        f"Reasons       : {_render_reasons(event_data.get('reasons'))}",
        f"Timestamp     : {_norm(event_data.get('timestamp') or datetime.now(timezone.utc).isoformat())}",
        "",
        "RECOMMENDED ACTION:",
        _build_recommendations(severity, event_data),
        "",
        "— RansomForge Hackathon SOC Demo",
    ]
    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def send_alert_email(event_data: dict[str, Any]) -> bool:
    """Send a ransomware alert email for high/critical events.

    Returns True when an email was sent; False when suppressed or failed.
    Each email body and subject are built from the live event_data so
    consecutive alerts look meaningfully different.
    """
    if not isinstance(event_data, dict):
        print("[email] failed: invalid event payload")
        return False

    severity, score = _normalize_severity(event_data)
    if severity not in {"high", "critical"}:
        return False

    bucket = _make_bucket(event_data, severity)
    if _should_suppress(bucket, severity):
        print(f"[email] suppressed (cooldown) bucket={bucket!r}")
        return False

    api_key   = os.getenv("RESEND_API_KEY", "").strip()
    recipient = os.getenv("ALERT_EMAIL", "").strip()
    sender    = os.getenv("ALERT_FROM_EMAIL", "RansomForge Alerts <onboarding@resend.dev>").strip()

    if not api_key:
        print("[email] failed: RESEND_API_KEY is not configured")
        return False
    if not recipient:
        print("[email] failed: ALERT_EMAIL is not configured")
        return False
    if resend is None:
        print("[email] failed: resend client is unavailable")
        return False

    subject   = _build_subject(event_data, severity, score)
    html_body = _build_html(event_data, severity, score)
    text_body = _build_text(event_data, severity, score)

    event_label = _event_label(_norm(event_data.get("event_type") or "unknown"))
    print(f"[email] sending — {severity.upper()} | score={score} | {event_label} | bucket={bucket!r}")

    try:
        resend.api_key = api_key
        resend.Emails.send({
            "from":    sender,
            "to":      recipient,
            "subject": subject,
            "html":    html_body,
            "text":    text_body,
        })
    except Exception as error:
        print(f"[email] failed: {error}")
        return False

    print("[email] alert sent successfully")
    return True
