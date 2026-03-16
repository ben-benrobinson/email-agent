"""Configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

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


class Config:
    """Application configuration."""

    # IMAP (receiving)
    imap_host: str = get_env("IMAP_HOST", "127.0.0.1")
    imap_port: int = int(get_env("IMAP_PORT", "1143"))
    imap_user: str = get_env("IMAP_USER", "")
    imap_password: str = get_env("IMAP_PASSWORD", "")

    # SMTP (sending)
    smtp_host: str = get_env("SMTP_HOST", "127.0.0.1")
    smtp_port: int = int(get_env("SMTP_PORT", "1025"))
    smtp_user: str = get_env("SMTP_USER", "")
    smtp_password: str = get_env("SMTP_PASSWORD", "")

    # LLM (Claude / Anthropic)
    anthropic_api_key: str = get_env("ANTHROPIC_API_KEY", "")
    anthropic_model: str = get_env("ANTHROPIC_MODEL", "claude-haiku-4-5")

    # Allowlist: email -> optional tone instruction (e.g. "be witty")
    allowlist: dict[str, str] = load_allowlist()

    # Knowledge base (personal facts for response context)
    knowledge: str = load_knowledge()

    # Email signoff appended to every sent email (e.g. "Best,\nBen")
    signoff: str = load_signoff()

    # SSL: set IMAP_SSL_SKIP_VERIFY=1 for Proton Bridge (self-signed local cert)
    imap_ssl_skip_verify: bool = get_env("IMAP_SSL_SKIP_VERIFY", "").lower() in ("1", "true", "yes")
    smtp_ssl_skip_verify: bool = get_env("SMTP_SSL_SKIP_VERIFY", "").lower() in ("1", "true", "yes")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate config and return list of error messages."""
        errors = []
        if not cls.imap_user or not cls.imap_password:
            errors.append("IMAP_USER and IMAP_PASSWORD must be set")
        if not cls.smtp_user or not cls.smtp_password:
            errors.append("SMTP_USER and SMTP_PASSWORD must be set")
        if not cls.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY must be set")
        if not cls.allowlist:
            errors.append(
                "Allowlist is empty. Create allowlist.txt (copy from allowlist.example.txt) "
                "or set ALLOWLIST env var with comma-separated emails"
            )
        return errors
