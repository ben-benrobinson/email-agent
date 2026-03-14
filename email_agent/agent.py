"""Main agent loop: poll inbox, filter by allowlist, generate and send replies."""

import logging
import time

from .allowlist import is_on_allowlist, normalize_email
from .config import Config
from .email_client import fetch_unread_emails, mark_as_read, send_reply
from .llm_client import generate_reply

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 60


def run_once() -> int:
    """
    Process one batch of unread emails. Returns count of emails replied to.
    """
    errors = Config.validate()
    if errors:
        for e in errors:
            logger.error("%s", e)
        raise SystemExit(1)

    emails = fetch_unread_emails()
    replied = 0

    for em in emails:
        from_header = em["from_addr"]
        if not is_on_allowlist(from_header, Config.allowlist):
            logger.info("Skipping %s (not on allowlist)", from_header)
            continue

        reply_to_addr = normalize_email(from_header)
        if not reply_to_addr:
            logger.warning("Could not parse From address: %s", from_header)
            continue

        subject = em["subject"]
        body = em["body_text"]

        try:
            reply_body = generate_reply(
                from_addr=from_header,
                subject=subject,
                original_body=body,
            )
        except Exception as e:
            logger.exception("LLM failed for %s: %s", reply_to_addr, e)
            continue

        try:
            send_reply(
                to_addr=reply_to_addr,
                subject=subject,
                body_plain=reply_body,
                in_reply_to=em.get("message_id") or None,
                references=em.get("message_id") or None,
            )
            logger.info("Replied to %s: %s", reply_to_addr, subject[:50])
            mark_as_read(em["uid"])
            replied += 1
        except Exception as e:
            logger.exception("Failed to send reply to %s: %s", reply_to_addr, e)

    return replied


def run(poll_interval: int = POLL_INTERVAL_SEC) -> None:
    """Run the agent loop indefinitely, polling for new emails."""
    errors = Config.validate()
    if errors:
        for e in errors:
            logger.error("%s", e)
        raise SystemExit(1)

    logger.info(
        "Starting email agent. Allowlist: %d addresses. Poll interval: %ds",
        len(Config.allowlist),
        poll_interval,
    )

    while True:
        try:
            run_once()
        except Exception as e:
            logger.exception("Poll cycle error: %s", e)
        time.sleep(poll_interval)
