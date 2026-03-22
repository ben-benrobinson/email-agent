"""Calendar digest: scan inbox for proposed dates/times and email a summary to the user."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from .allowlist import normalize_email
from .config import Config, get_calendar_state_path
from .email_client import fetch_emails_since, send_email
from .llm_client import extract_calendar_proposals

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CalendarDigestRule:
    """A single digest schedule rule."""

    rule_id: str
    time_hhmm: str
    dows: set[int]  # Mon=0..Sun=6


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _rules_from_config() -> list[CalendarDigestRule]:
    rules: list[CalendarDigestRule] = []
    for r in Config.calendar_schedule:
        try:
            rules.append(
                CalendarDigestRule(
                    rule_id=str(r["rule_id"]),
                    time_hhmm=str(r["time_hhmm"]),
                    dows=set(r["dows"]),
                )
            )
        except Exception:
            continue
    return rules


def _parse_hhmm(hhmm: str) -> tuple[int, int] | None:
    try:
        hh, mm = hhmm.strip().split(":", 1)
        h = int(hh)
        m = int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except Exception:
        return None
    return None


def is_digest_due(*, now: datetime, rule: CalendarDigestRule, last_sent_at: datetime | None) -> bool:
    """
    Returns True if the digest should run for the given rule at the given time.

    Uses local machine time for naive datetimes. Fires **once per calendar day**
    after the scheduled time — not only at the exact minute (60s polling often
    skips the exact minute, which used to prevent digests from ever running).
    """
    hhmm = _parse_hhmm(rule.time_hhmm)
    if not hhmm:
        return False
    if now.weekday() not in rule.dows:
        return False
    h, m = hhmm
    schedule_today = datetime.combine(now.date(), time(hour=h, minute=m))
    if now < schedule_today:
        return False
    if last_sent_at is None:
        return True
    # Already sent today after this rule's scheduled time?
    if last_sent_at.date() == now.date() and last_sent_at >= schedule_today:
        return False
    return True


def run_calendar_digest_if_due(*, now: datetime | None = None, force: bool = False) -> bool:
    """
    If any schedule is due, generate and email a digest to self.
    Returns True if a digest was sent.

    If force is True, run all configured rules immediately (for testing), and
    still updates last_sent_at so a scheduled run the same day won't duplicate.
    """
    if not Config.calendar_allowlist or not Config.calendar_schedule:
        if force or logger.isEnabledFor(logging.DEBUG):
            logger.info(
                "Calendar digest skipped: calendar_allowlist (%d) or calendar_schedule (%d rules) empty",
                len(Config.calendar_allowlist),
                len(Config.calendar_schedule),
            )
        return False

    now = now or datetime.now()
    state_path = get_calendar_state_path()
    state = _load_state(state_path)
    rules = _rules_from_config()

    sent_any = False
    for rule in rules:
        last_iso = state.get("last_sent_at", {}).get(rule.rule_id)
        last_dt: datetime | None = None
        if isinstance(last_iso, str) and last_iso:
            try:
                last_dt = datetime.fromisoformat(last_iso)
            except Exception:
                last_dt = None

        if not force and not is_digest_due(now=now, rule=rule, last_sent_at=last_dt):
            continue

        # Pull emails since last digest (or a conservative fallback window)
        since = last_dt or (now - timedelta(days=7))
        # IMAP SINCE is date-granular; keep it in UTC if tz-aware, otherwise local
        emails = fetch_emails_since(since=since)

        allow = Config.calendar_allowlist
        candidates: list[dict] = []
        for em in emails:
            frm = normalize_email(em.get("from_addr", ""))
            if not frm or frm not in allow:
                continue
            candidates.append(em)

        logger.info(
            "Calendar digest: rule=%s candidates=%d (from %d fetched since %s)",
            rule.rule_id,
            len(candidates),
            len(emails),
            since.isoformat(),
        )

        proposals = extract_calendar_proposals(
            emails=[
                {
                    "from": normalize_email(e.get("from_addr", "")),
                    "subject": e.get("subject", ""),
                    "date": (e.get("date").isoformat() if e.get("date") else ""),
                    "body": e.get("body_text", "")[:5000],
                }
                for e in candidates
            ],
            now_iso=now.isoformat(),
        )

        digest_body = _format_digest(proposals=proposals, window_start=since, window_end=now)

        if digest_body.strip():
            send_email(
                to_addr=Config.smtp_user,
                subject="Calendar Digest: proposed times",
                body_plain=digest_body,
            )
            logger.info("Calendar digest emailed to %s", Config.smtp_user)
            sent_any = True

        state.setdefault("last_sent_at", {})[rule.rule_id] = now.isoformat()
        _save_state(state_path, state)

    return sent_any


def _format_digest(*, proposals: list[dict], window_start: datetime, window_end: datetime) -> str:
    if not proposals:
        return (
            "Calendar digest\n\n"
            f"Window: {window_start.isoformat()} → {window_end.isoformat()}\n\n"
            "No proposed dates/times found in the monitored emails."
        )

    lines: list[str] = []
    lines.append("Calendar digest\n")
    lines.append(f"Window: {window_start.isoformat()} → {window_end.isoformat()}\n")
    lines.append("Proposed options:\n")
    for p in proposals:
        desc = (p.get("description") or "").strip()
        frm = (p.get("from") or "").strip()
        subj = (p.get("subject") or "").strip()
        times = p.get("proposed_times") or []
        if not isinstance(times, list):
            times = []
        if not (desc or times):
            continue
        header_bits = [b for b in [desc, subj, frm] if b]
        header = " — ".join(header_bits) if header_bits else "(no description)"
        lines.append(f"- {header}")
        for t in times[:10]:
            t = str(t).strip()
            if t:
                lines.append(f"  - {t}")
        lines.append("")

    return "\n".join(lines).strip()

