"""IMAP/SMTP email client for receiving and sending emails."""

import ssl
import email
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid, parseaddr

from .config import Config


def _ssl_context() -> ssl.SSLContext | None:
    """Return SSL context for Proton Bridge (self-signed cert) if verification is disabled."""
    if Config.imap_ssl_skip_verify or Config.smtp_ssl_skip_verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


def fetch_unread_emails() -> list[dict]:
    """
    Fetch unread emails from INBOX.
    Returns list of dicts with: message_id, from_addr, to_addr, subject, body_plain, body_html
    """
    ctx = _ssl_context()
    with imaplib.IMAP4(Config.imap_host, Config.imap_port) as imap:
        imap.starttls(ssl_context=ctx) if ctx else imap.starttls()
        imap.login(Config.imap_user, Config.imap_password)
        imap.select("INBOX")

        _, msg_nums = imap.search(None, "UNSEEN")
        uids = msg_nums[0].split()
        if not uids:
            return []

        result = []
        for uid in uids:
            _, data = imap.fetch(uid, "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)
            info = _parse_message(msg, uid.decode() if isinstance(uid, bytes) else uid)
            if info:
                result.append(info)
        return result


def _parse_message(msg: email.message.Message, uid: str) -> dict | None:
    """Parse email message into a dict."""
    from_addr = msg.get("From", "")
    to_addr = msg.get("To", "")
    subject = msg.get("Subject", "(no subject)")
    msg_id = msg.get("Message-ID", "")

    body_plain = ""
    body_html = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                body_plain = _decode_body(part)
            elif ctype == "text/html":
                body_html = _decode_body(part)
    else:
        ctype = msg.get_content_type()
        body = _decode_body(msg)
        if ctype == "text/html":
            body_html = body
        else:
            body_plain = body

    # Prefer plain for LLM; fall back to stripping HTML if only HTML
    text_for_llm = body_plain or _strip_html(body_html) if body_html else ""

    return {
        "uid": uid,
        "message_id": msg_id,
        "from_addr": from_addr,
        "to_addr": to_addr,
        "subject": subject,
        "body_plain": body_plain,
        "body_html": body_html,
        "body_text": text_for_llm,
        "raw_message": msg,
    }


def _decode_body(part: email.message.Message) -> str:
    """Decode email part body to string."""
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except (LookupError, TypeError):
        return payload.decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    """Simple HTML stripping for LLM input."""
    import re

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def mark_as_read(uid: str) -> None:
    """Mark an email as read."""
    ctx = _ssl_context()
    with imaplib.IMAP4(Config.imap_host, Config.imap_port) as imap:
        imap.starttls(ssl_context=ctx) if ctx else imap.starttls()
        imap.login(Config.imap_user, Config.imap_password)
        imap.select("INBOX")
        imap.store(uid.encode() if isinstance(uid, str) else uid, "+FLAGS", "\\Seen")


def send_reply(
    to_addr: str,
    subject: str,
    body_plain: str,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> None:
    """Send a reply email."""
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((Config.smtp_user, Config.smtp_user))
    msg["To"] = to_addr
    msg["Subject"] = _ensure_reply_subject(subject)
    msg["Message-ID"] = make_msgid(domain=Config.smtp_user.split("@")[-1])
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

    # Append user-configured signoff to every sent email
    if Config.signoff:
        body_plain = body_plain.rstrip() + "\n\n" + Config.signoff

    msg.attach(MIMEText(body_plain, "plain", "utf-8"))

    ctx = _ssl_context()
    with smtplib.SMTP(Config.smtp_host, Config.smtp_port) as smtp:
        smtp.starttls(context=ctx) if ctx else smtp.starttls()
        smtp.login(Config.smtp_user, Config.smtp_password)
        smtp.sendmail(Config.smtp_user, [to_addr], msg.as_string())


def _ensure_reply_subject(subject: str) -> str:
    """Ensure subject has Re: prefix for replies."""
    sub = subject.strip()
    if sub.lower().startswith("re:"):
        return sub
    return f"Re: {sub}"
