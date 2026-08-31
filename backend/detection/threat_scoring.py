from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
from typing import Any


SUSPICIOUS_EXTENSIONS = {".locked", ".encrypted", ".crypto", ".ransom"}
HIGH_RISK_NAMES = {"shadowcopy", "vssadmin", "bcdedit", "wmic"}
ENTROPY_LOW_THRESHOLD = 4.5
ENTROPY_HIGH_THRESHOLD = 6.5
ENTROPY_SAMPLE_BYTES = 512 * 1024


def calculate_shannon_entropy(data: bytes) -> float:
    """Calculate Shannon entropy for text or binary data.

    Ransomware-encrypted files often look close to random data, which pushes
    their entropy higher than normal user documents. That makes entropy a fast,
    lightweight signal that supports future AI/ML feature engineering without
    replacing the existing heuristic detector.
    """
    if not data:
        return 0.0

    counts = Counter(data)
    length = len(data)
    entropy = 0.0
    for count in counts.values():
        probability = count / length
        entropy -= probability * math.log2(probability)
    return round(entropy, 4)


def analyze_file_entropy(path: str, sample_bytes: int = ENTROPY_SAMPLE_BYTES) -> dict[str, Any]:
    """Read a local file and return a lightweight entropy analysis payload.

    This is intentionally best-effort and local-only. If a file cannot be read,
    the function returns an "unknown" result instead of blocking the realtime
    pipeline.
    """
    file_path = Path(path)
    result: dict[str, Any] = {
        "entropy": None,
        "entropy_level": "unknown",
        "entropy_bonus": 0,
        "entropy_reasons": [],
    }

    try:
        if not file_path.exists() or not file_path.is_file():
            return result

        with file_path.open("rb") as handle:
            data = handle.read(max(0, int(sample_bytes)))

        entropy = calculate_shannon_entropy(data)
        result["entropy"] = entropy

        if entropy < ENTROPY_LOW_THRESHOLD:
            result["entropy_level"] = "low"
        elif entropy <= ENTROPY_HIGH_THRESHOLD:
            result["entropy_level"] = "moderate"
            result["entropy_bonus"] = 6
        else:
            result["entropy_level"] = "high"
            result["entropy_bonus"] = 18
            result["entropy_reasons"] = ["high entropy detected"]
    except Exception:
        return result

    return result


def score_file_event_details(path: str, event_type: str, entropy: float | None = None) -> dict[str, Any]:
    """Return the file score plus the feature flags used to justify it."""
    file_path = Path(path)
    score = 10
    reasons: list[str] = [f"{event_type} file activity"]
    entropy_level = "unknown"
    entropy_bonus = 0

    if event_type == "created":
        score += 10
    elif event_type == "modified":
        score += 20
    elif event_type == "deleted":
        score += 35
    elif event_type == "moved":
        score += 25

    if file_path.suffix.lower() in SUSPICIOUS_EXTENSIONS:
        score += 40
        reasons.append("suspicious extension")

    if any(token in file_path.name.lower() for token in HIGH_RISK_NAMES):
        score += 25
        reasons.append("high risk filename")

    if file_path.suffix.lower() in {".txt", ".doc", ".docx", ".pdf", ".csv", ".xlsx", ".json"}:
        score += 10

    if entropy is not None:
        entropy_level = _entropy_level(entropy)
        if entropy_level == "moderate":
            entropy_bonus = 6
        elif entropy_level == "high":
            entropy_bonus = 18
            reasons.append("high entropy detected")
        score += entropy_bonus

    return {
        "score": min(score, 100),
        "reasons": reasons,
        "entropy": entropy,
        "entropy_level": entropy_level,
        "entropy_bonus": entropy_bonus,
    }


def score_file_event(path: str, event_type: str, entropy: float | None = None) -> int:
    """Return a compact threat score for legacy callers."""
    return int(score_file_event_details(path, event_type, entropy=entropy)["score"])


def _entropy_level(entropy: float) -> str:
    if entropy < ENTROPY_LOW_THRESHOLD:
        return "low"
    if entropy <= ENTROPY_HIGH_THRESHOLD:
        return "moderate"
    return "high"
