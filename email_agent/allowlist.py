"""Allowlist handling for email addresses."""

from email.utils import parseaddr


def normalize_email(address: str) -> str:
    """Extract and normalize email address from a From header value."""
    _, addr = parseaddr(address)
    return addr.lower().strip() if addr else ""


def is_on_allowlist(from_header: str, allowlist: set[str]) -> bool:
    """Check if the sender (from From header) is on the allowlist."""
    addr = normalize_email(from_header)
    return addr in allowlist
