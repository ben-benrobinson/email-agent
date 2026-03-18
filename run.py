#!/usr/bin/env python3
"""Run the email agent."""

import argparse

from email_agent.agent import run, run_once
from email_agent.calendar_digest import run_calendar_digest_if_due
from email_agent.config import project_root
from email_agent.feedback_store import add_feedback


def _cmd_feedback(text: str) -> None:
    """Add feedback so the agent uses it in future suggestions."""
    if not text or not text.strip():
        print("Usage: python run.py feedback \"your feedback text\"")
        raise SystemExit(1)
    add_feedback(text)
    print("Feedback saved. It will be used in future email suggestions.")


def _cmd_signoff(signoff: str) -> None:
    """Set the signoff appended to every email (e.g. 'Best,\\nBen')."""
    path = project_root / "signoff.txt"
    content = (signoff or "").replace("\\n", "\n").strip()
    path.write_text(content, encoding="utf-8")
    if content:
        print("Signoff saved to signoff.txt. Every email you send will end with:")
        print("---")
        print(content)
        print("---")
    else:
        print("Signoff cleared (signoff.txt is empty).")


def _cmd_calendar_digest() -> None:
    """Run the calendar digest once (useful for testing configuration)."""
    ran = run_calendar_digest_if_due(now=None)
    if ran:
        print("Calendar digest sent.")
    else:
        print("Calendar digest not sent (not due, or not configured).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Email agent - LLM auto-responder for allowlisted senders")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one batch of emails and exit (default: run forever)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Seconds between poll cycles (default: 60)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Customization commands")

    feedback_parser = subparsers.add_parser("feedback", help="Save feedback for future suggestions")
    feedback_parser.add_argument("text", nargs="?", default="", help="Feedback text (e.g. what worked or didn't)")

    signoff_parser = subparsers.add_parser("signoff", help="Set signoff for every email (e.g. Best,\\nBen)")
    signoff_parser.add_argument("text", nargs="?", default="", help="Signoff text; use \\n for newline")

    subparsers.add_parser("calendar-digest", help="Run calendar digest once (if configured/due)")

    args = parser.parse_args()

    if args.command == "feedback":
        _cmd_feedback(args.text)
        return
    if args.command == "signoff":
        _cmd_signoff(args.text)
        return
    if args.command == "calendar-digest":
        _cmd_calendar_digest()
        return

    if args.once:
        run_once(print_response=True)
    else:
        run(poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
