"""Durable storage for user feedback so the agent can improve future suggestions."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import get_feedback_path


def _ensure_file(fpath: Path) -> list[dict]:
    """Ensure the feedback JSON file exists and return its contents as a list."""
    if not fpath.exists():
        return []
    try:
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def add_feedback(text: str) -> None:
    """Append a feedback entry. Text is stored and included in future LLM context."""
    text = text.strip()
    if not text:
        return
    fpath = get_feedback_path()
    entries = _ensure_file(fpath)
    entries.append({
        "text": text,
        "added_at": datetime.now(tz=timezone.utc).isoformat(),
    })
    fpath.parent.mkdir(parents=True, exist_ok=True)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def get_all_feedback() -> str:
    """
    Return all feedback as a single string for injection into the LLM system prompt.
    Returns empty string if no feedback.
    """
    fpath = get_feedback_path()
    entries = _ensure_file(fpath)
    if not entries:
        return ""
    lines = [e.get("text", "").strip() for e in entries if e.get("text", "").strip()]
    return "\n".join(lines) if lines else ""
