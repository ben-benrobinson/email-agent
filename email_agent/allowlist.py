"""Allowlist handling for email addresses and per-sender tone instructions."""

from email.utils import parseaddr


def normalize_email(address: str) -> str:
    """Extract and normalize email address from a From header value."""
    _, addr = parseaddr(address)
    return addr.lower().strip() if addr else ""


def is_on_allowlist(from_header: str, allowlist: dict[str, str]) -> bool:
    """Check if the sender (from From header) is on the allowlist."""
    addr = normalize_email(from_header)
    return addr in allowlist


def get_instruction(from_header: str, allowlist: dict[str, str]) -> str:
    """Get the tone/style instruction for this sender, or empty string if none."""
    addr = normalize_email(from_header)
    return allowlist.get(addr, "")
