#!/usr/bin/env python3
"""Run the email agent."""

import argparse

from email_agent.agent import run, run_once


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
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run(poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
