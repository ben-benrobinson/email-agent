"""Configuration loaded from environment variables."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

from .secrets_manager import get_secret_string

# Load .env from project root (parent of this package)
_root = Path(__file__).resolve().parent.parent
project_root = _root  # Public alias for CLI and other callers
load_dotenv(_root / ".env")


def get_env(key: str, default: str = "") -> str:
    """Get environment variable, stripping whitespace."""
    return os.environ.get(key, default).strip()


def load_knowledge() -> str:
    """
    Load knowledge from knowledge.txt or KNOWLEDGE env var.
    Returns a string of facts to inject into the LLM context.
    """
    knowledge_path = _root / "knowledge.txt"
    if knowledge_path.exists():
        lines = []
        with open(knowledge_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    lines.append(line)
        return "\n".join(lines) if lines else ""

    env_val = get_env("KNOWLEDGE")
    return env_val if env_val else ""


def load_allowlist() -> dict[str, str]:
    """
    Load allowlist from allowlist.txt or ALLOWLIST env var.
    Returns dict: email (lowercase) -> optional instruction (e.g. "be witty").
    Format: "email@example.com" or "email@example.com | be witty and sarcastic"
    """
    result: dict[str, str] = {}

    allowlist_path = _root / "allowlist.txt"
    if allowlist_path.exists():
        with open(allowlist_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if " | " in line:
                        email_part, instruction = line.split(" | ", 1)
                        email = email_part.strip().lower()
                        instruction = instruction.strip()
                    else:
                        email = line.lower()
                        instruction = ""
                    if email:
                        result[email] = instruction
        return result

    # Fall back to env var (comma-separated, no per-email instructions)
    env_val = get_env("ALLOWLIST")
    if env_val:
        for addr in env_val.split(","):
            addr = addr.strip().lower()
            if addr:
                result[addr] = ""
    return result


def load_signoff() -> str:
    """
    Load email signoff from signoff.txt or EMAIL_SIGNOFF env var.
    Used as the closing of every sent email (e.g. "Best,\nBen").
    """
    env_val = get_env("EMAIL_SIGNOFF")
    if env_val:
        return env_val.replace("\\n", "\n").strip()
    signoff_path = _root / "signoff.txt"
    if signoff_path.exists():
        with open(signoff_path, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def get_feedback_path() -> Path:
    """Path to the JSON file where user feedback is stored."""
    path_str = get_env("FEEDBACK_FILE")
    if path_str:
        return Path(path_str).expanduser().resolve()
    return _root / "feedback.json"


def _env_flag(key: str, default: bool = False) -> bool:
    v = get_env(key, "1" if default else "0").lower()
    return v in ("1", "true", "yes", "y", "on")


def load_secret_if_enabled(*, env_value: str, secret_id: str, enabled: bool, region: str) -> str:
    """
    Prefer the direct env_value if present; otherwise fetch from AWS Secrets Manager if enabled.
    """
    if env_value:
        return env_value
    if not enabled:
        return ""
    try:
        return get_secret_string(secret_id=secret_id, region=region)
    except ModuleNotFoundError:
        # Fail fast: without boto3 we can't reach AWS Secrets Manager.
        raise
    except Exception:
        # Validation will provide the actionable error message.
        return ""


def load_calendar_allowlist() -> set[str]:
    """
    Load calendar allowlist from calendar_allowlist.txt or CALENDAR_ALLOWLIST env var.
    Returns set of lowercase emails.
    """
    allowlist_path = _root / "calendar_allowlist.txt"
    if allowlist_path.exists():
        out: set[str] = set()
        with open(allowlist_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    out.add(line.lower())
        return out

    env_val = get_env("CALENDAR_ALLOWLIST")
    if env_val:
        return {a.strip().lower() for a in env_val.split(",") if a.strip()}
    return set()


def load_calendar_schedule() -> list[dict]:
    """
    Load calendar digest schedule rules from calendar_schedule.txt or CALENDAR_SCHEDULE env var.

    Each rule line format:
      - "18:00 daily"
      - "10:00 sat"
      - "09:30 mon,wed,fri"

    Returns list of dicts: {"time_hhmm": "18:00", "dows": set[int], "rule_id": str}
    where dows are Python weekday ints (Mon=0..Sun=6).
    """
    dow_map = {
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
    }

    def parse_line(line: str) -> dict | None:
        line = line.strip()
        if not line or line.startswith("#"):
            return None
        m = re.match(r"^(?P<time>\d{1,2}:\d{2})\s+(?P<days>.+)$", line, flags=re.IGNORECASE)
        if not m:
            return None
        time_hhmm = m.group("time")
        days = m.group("days").strip().lower()
        if days == "daily":
            dows = set(range(7))
        else:
            parts = [p.strip() for p in days.split(",") if p.strip()]
            dows = {dow_map[p[:3]] for p in parts if p[:3] in dow_map}
        if not dows:
            return None
        rule_id = f"{time_hhmm}|{','.join(str(d) for d in sorted(dows))}"
        return {"time_hhmm": time_hhmm, "dows": dows, "rule_id": rule_id}

    schedule_path = _root / "calendar_schedule.txt"
    lines: list[str] = []
    if schedule_path.exists():
        with open(schedule_path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        env_val = get_env("CALENDAR_SCHEDULE")
        if env_val:
            lines = env_val.split(";")

    rules: list[dict] = []
    for line in lines:
        rule = parse_line(line)
        if rule:
            rules.append(rule)
    return rules


def get_calendar_state_path() -> Path:
    """Path to the JSON file that stores last-run timestamps for calendar digest schedules."""
    path_str = get_env("CALENDAR_STATE_FILE")
    if path_str:
        return Path(path_str).expanduser().resolve()
    return _root / "calendar_state.json"


class Config:
    """Application configuration."""

    # AWS Secrets Manager (for secrets at runtime, e.g. on EC2 w/ IAM role)
    aws_secrets_manager_enabled: bool = _env_flag("AWS_SECRETS_MANAGER_ENABLED", default=False)
    aws_secrets_manager_region: str = get_env("AWS_SECRETS_MANAGER_REGION", "us-east-2")
    aws_secret_imap_password_id: str = get_env("AWS_SECRET_IMAP_PASSWORD_ID", "email-agent/imap-password")
    aws_secret_smtp_password_id: str = get_env("AWS_SECRET_SMTP_PASSWORD_ID", "email-agent/smtp-password")
    aws_secret_anthropic_api_key_id: str = get_env(
        "AWS_SECRET_ANTHROPIC_API_KEY_ID", "email-agent/anthropic-api-key"
    )

    # IMAP (receiving)
    imap_host: str = get_env("IMAP_HOST", "127.0.0.1")
    imap_port: int = int(get_env("IMAP_PORT", "1143"))
    imap_user: str = get_env("IMAP_USER", "")
    imap_password: str = load_secret_if_enabled(
        env_value=get_env("IMAP_PASSWORD", ""),
        secret_id=aws_secret_imap_password_id,
        enabled=aws_secrets_manager_enabled,
        region=aws_secrets_manager_region,
    )

    # SMTP (sending)
    smtp_host: str = get_env("SMTP_HOST", "127.0.0.1")
    smtp_port: int = int(get_env("SMTP_PORT", "1025"))
    smtp_user: str = get_env("SMTP_USER", "")
    smtp_password: str = load_secret_if_enabled(
        env_value=get_env("SMTP_PASSWORD", ""),
        secret_id=aws_secret_smtp_password_id,
        enabled=aws_secrets_manager_enabled,
        region=aws_secrets_manager_region,
    )

    # LLM (Claude / Anthropic)
    anthropic_api_key: str = load_secret_if_enabled(
        env_value=get_env("ANTHROPIC_API_KEY", ""),
        secret_id=aws_secret_anthropic_api_key_id,
        enabled=aws_secrets_manager_enabled,
        region=aws_secrets_manager_region,
    )
    anthropic_model: str = get_env("ANTHROPIC_MODEL", "claude-haiku-4-5")

    # Allowlist: email -> optional tone instruction (e.g. "be witty")
    allowlist: dict[str, str] = load_allowlist()

    # Knowledge base (personal facts for response context)
    knowledge: str = load_knowledge()

    # Email signoff appended to every sent email (e.g. "Best,\nBen")
    signoff: str = load_signoff()

    # Calendar digest: senders to scan + schedule rules
    calendar_allowlist: set[str] = load_calendar_allowlist()
    calendar_schedule: list[dict] = load_calendar_schedule()

    # SSL: set IMAP_SSL_SKIP_VERIFY=1 for Proton Bridge (self-signed local cert)
    imap_ssl_skip_verify: bool = get_env("IMAP_SSL_SKIP_VERIFY", "").lower() in ("1", "true", "yes")
    smtp_ssl_skip_verify: bool = get_env("SMTP_SSL_SKIP_VERIFY", "").lower() in ("1", "true", "yes")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate config and return list of error messages."""
        errors = []
        if not cls.imap_user or not cls.imap_password:
            if not cls.imap_user:
                errors.append("IMAP_USER must be set")
            else:
                if cls.aws_secrets_manager_enabled:
                    errors.append(
                        f"IMAP password missing. Ensure Secrets Manager access to `{cls.aws_secret_imap_password_id}` "
                        f"(and that the secret contains a string value)."
                    )
                else:
                    errors.append("IMAP_PASSWORD must be set (or enable AWS Secrets Manager).")
        if not cls.smtp_user or not cls.smtp_password:
            if not cls.smtp_user:
                errors.append("SMTP_USER must be set")
            else:
                if cls.aws_secrets_manager_enabled:
                    errors.append(
                        f"SMTP password missing. Ensure Secrets Manager access to `{cls.aws_secret_smtp_password_id}` "
                        f"(and that the secret contains a string value)."
                    )
                else:
                    errors.append("SMTP_PASSWORD must be set (or enable AWS Secrets Manager).")
        if not cls.anthropic_api_key:
            if cls.aws_secrets_manager_enabled:
                errors.append(
                    f"Anthropic API key missing. Ensure Secrets Manager access to `{cls.aws_secret_anthropic_api_key_id}`."
                )
            else:
                errors.append("ANTHROPIC_API_KEY must be set (or enable AWS Secrets Manager).")
        if not cls.allowlist:
            errors.append(
                "Allowlist is empty. Create allowlist.txt (copy from allowlist.example.txt) "
                "or set ALLOWLIST env var with comma-separated emails"
            )
        return errors
