from __future__ import annotations

"""PDF incident report generation for the RansomForge demo.

This module reads the existing SQLite event/alert data and produces a polished
incident report PDF in C:/RansomGuard/reports/ using reportlab.
"""

from datetime import datetime, timezone
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from . import db as db_service
except ImportError:
    from services import db as db_service

try:
    from .backup_manager import get_all_backups, get_last_clean_backup
except ImportError:
    from services.backup_manager import get_all_backups, get_last_clean_backup


REPORT_ROOT = Path("C:/RansomGuard/reports")


def _resolve_db_path(db_path: str | None = None) -> Path:
    if db_path:
        return Path(db_path)
    try:
        return Path(db_service._resolve_db_path())
    except Exception:
        return Path(__file__).resolve().parent.parent / "ransomforge.db"


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(_resolve_db_path(db_path), timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
    except sqlite3.Error:
        pass
    return connection


def _normalize_timestamp(value: Any) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _severity_label(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def _severity_rank(label: str) -> int:
    mapping = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    return mapping.get((label or "low").lower(), 1)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def _table_paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_safe_text(text).replace("\n", "<br/>") or "-", style)


def _load_alerts(limit: int = 25, db_path: str | None = None) -> list[dict[str, Any]]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, timestamp, message, severity
            FROM alerts
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    alerts: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["id"] = int(item["id"])
        item["timestamp"] = _normalize_timestamp(item.get("timestamp"))
        item["message"] = _safe_text(item.get("message"))
        item["severity"] = int(item.get("severity") or 0)
        alerts.append(item)
    return alerts


def _load_events(limit: int = 25, db_path: str | None = None) -> list[dict[str, Any]]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, timestamp, event_type, file_path, process_name, threat_score, severity, entropy
            FROM events
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    events: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["id"] = int(item["id"])
        item["timestamp"] = _normalize_timestamp(item.get("timestamp"))
        item["event_type"] = _safe_text(item.get("event_type"))
        item["file_path"] = _safe_text(item.get("file_path"))
        item["process_name"] = _safe_text(item.get("process_name"))
        item["threat_score"] = int(item.get("threat_score") or 0)
        item["severity"] = int(item.get("severity") or 0)
        events.append(item)
    return events


def _build_table(data: list[list[Any]], col_widths: list[float], style: ParagraphStyle) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _alert_rows(alerts: list[dict[str, Any]], text_style: ParagraphStyle) -> list[list[Any]]:
    rows: list[list[Any]] = [["Severity", "Threat Score", "Description", "Timestamp"]]
    if not alerts:
        rows.append([
            _table_paragraph("No alerts available", text_style),
            _table_paragraph("-", text_style),
            _table_paragraph("No alert records were found in SQLite.", text_style),
            _table_paragraph("-", text_style),
        ])
        return rows

    for alert in alerts:
        rows.append([
            _table_paragraph(_severity_label(int(alert.get("severity") or 0)), text_style),
            _table_paragraph(int(alert.get("severity") or 0), text_style),
            _table_paragraph(alert.get("message"), text_style),
            _table_paragraph(alert.get("timestamp"), text_style),
        ])
    return rows


def _event_rows(events: list[dict[str, Any]], text_style: ParagraphStyle) -> list[list[Any]]:
    rows: list[list[Any]] = [["Event Type", "File Path", "Severity", "Timestamp"]]
    if not events:
        rows.append([
            _table_paragraph("No events available", text_style),
            _table_paragraph("-", text_style),
            _table_paragraph("-", text_style),
            _table_paragraph("-", text_style),
        ])
        return rows

    for event in events:
        rows.append([
            _table_paragraph(event.get("event_type"), text_style),
            _table_paragraph(event.get("file_path") or event.get("process_name") or "-", text_style),
            _table_paragraph(_severity_label(int(event.get("severity") or 0)), text_style),
            _table_paragraph(event.get("timestamp"), text_style),
        ])
    return rows


def generate_incident_report(
    *,
    quarantine_status: dict[str, Any] | None = None,
    db_path: str | None = None,
) -> str:
    """Generate a PDF ransomware incident report and return the output path."""
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    timestamp_label = timestamp.strftime("%Y_%m_%d_%H%M%S")
    report_path = REPORT_ROOT / f"report_{timestamp_label}_{uuid.uuid4().hex[:8]}.pdf"

    alerts = _load_alerts(db_path=db_path)
    events = _load_events(db_path=db_path)
    severity_source = [int(alert.get("severity") or 0) for alert in alerts] + [int(event.get("severity") or 0) for event in events]
    max_severity = max(severity_source) if severity_source else 0
    severity_summary = _severity_label(max_severity)

    latest_backup = get_last_clean_backup()
    backup_count = len(get_all_backups())
    quarantine_status = quarantine_status or {}
    quarantine_label = str(quarantine_status.get("status") or quarantine_status.get("quarantine", {}).get("status") or "UNKNOWN")
    latest_backup_label = "Available" if latest_backup else "Not available"
    restore_recommendation = "Restore the latest clean backup and isolate affected systems." if latest_backup else "Create a clean backup before attempting recovery."

    print("[report] generating incident report")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=16,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=6,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
    )
    centered_style = ParagraphStyle(
        "CenteredBody",
        parent=body_style,
        alignment=TA_CENTER,
    )

    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=42,
        bottomMargin=36,
        title="RansomForge Incident Report",
        author="RansomForge",
        subject="Ransomware incident summary",
        pageCompression=0,
    )

    story: list[Any] = []
    story.append(Spacer(1, 1.9 * inch))
    story.append(Paragraph("RansomForge Incident Report", title_style))
    story.append(Paragraph(f"Generated {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}", subtitle_style))
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph(f"Severity Summary: <b>{severity_summary}</b>", centered_style))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("This report summarizes realtime ransomware-like activity detected in the monitored environment.", centered_style))
    story.append(PageBreak())

    story.append(Paragraph("Executive Summary", section_style))
    summary_text = (
        "Critical ransomware-like activity was detected inside the monitored environment. "
        "The platform triggered realtime alerts, quarantine workflows, and recovery operations."
        if max_severity >= 85
        else "Suspicious ransomware-like activity was detected inside the monitored environment. "
        "The platform generated alerts, tracked live events, and preserved recovery snapshots."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 0.18 * inch))

    story.append(Paragraph("Alert Summary", section_style))
    alert_table = _build_table(_alert_rows(alerts, body_style), [1.0 * inch, 1.0 * inch, 3.7 * inch, 1.35 * inch], body_style)
    story.append(alert_table)
    story.append(Spacer(1, 0.22 * inch))

    story.append(Paragraph("Event Timeline", section_style))
    event_table = _build_table(_event_rows(events, body_style), [1.3 * inch, 3.6 * inch, 0.9 * inch, 1.25 * inch], body_style)
    story.append(event_table)
    story.append(Spacer(1, 0.22 * inch))

    story.append(Paragraph("Recovery Status", section_style))
    recovery_table = _build_table(
        [
            ["Item", "Status"],
            ["Quarantine Status", _table_paragraph(quarantine_label, body_style)],
            ["Latest Backup", _table_paragraph(latest_backup_label, body_style)],
            ["Backup Count", _table_paragraph(str(backup_count), body_style)],
            ["Restore Recommendation", _table_paragraph(restore_recommendation, body_style)],
        ],
        [1.8 * inch, 5.2 * inch],
        body_style,
    )
    story.append(recovery_table)
    story.append(Spacer(1, 0.22 * inch))

    story.append(Paragraph("AI Response", section_style))
    story.append(
        Paragraph(
            "Recommended next steps include isolating affected systems, restoring clean backups, and reviewing suspicious process activity.",
            body_style,
        )
    )

    doc.build(story)
    print(f"[report] report generated: {report_path}")
    return str(report_path)