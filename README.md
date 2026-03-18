# Email Agent

An LLM-powered email agent that automatically responds to emails from an allowlist of addresses. Designed for use with **Proton Mail** (via Proton Bridge) or any IMAP/SMTP provider.

## Features

- **Allowlist**: Only responds to emails from addresses you've approved
- **Knowledge base**: Personal facts (job, preferences, etc.) are factored into replies
- **LLM replies**: Uses Claude (Anthropic) to generate natural responses
- **Secure**: All credentials via environment variables—no secrets in the repo
- **Portable**: Clone, configure, and run for your own email

## Requirements

- Python 3.10+
- **Proton Mail users**: [Proton Mail Bridge](https://proton.me/mail/bridge) must be installed and running (paid Proton plan required for Bridge)
- **Other providers**: Standard IMAP/SMTP credentials
- Anthropic API key (Claude)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/email-agent.git
cd email-agent
python -m venv venv
source venv/bin/activate   # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp env.example .env
# Edit .env with your credentials
```

Required variables:

| Variable | Description |
|----------|-------------|
| `IMAP_HOST` | IMAP server (use `127.0.0.1` for Proton Bridge) |
| `IMAP_PORT` | IMAP port (default `1143` for Proton Bridge) |
| `IMAP_USER` | Your email address |
| `IMAP_PASSWORD` | Password (Proton Bridge uses Bridge password) |
| `SMTP_HOST` | SMTP server (use `127.0.0.1` for Proton Bridge) |
| `SMTP_PORT` | SMTP port (default `1025` for Proton Bridge) |
| `SMTP_USER` | Your email address |
| `SMTP_PASSWORD` | Same as IMAP for Proton Bridge |
| `ANTHROPIC_API_KEY` | Your Anthropic API key ([console.anthropic.com](https://console.anthropic.com/)) |

### 3. Set up the allowlist

```bash
cp allowlist.example.txt allowlist.txt
# Edit allowlist.txt and add one email address per line
```

Example `allowlist.txt`:

```
friend@example.com
colleague@company.org
buddy@example.com | be witty and sarcastic
```

Add ` | instruction` after an email to set tone for that sender (e.g. "be witty", "be sarcastic", "keep it formal").

Or use the `ALLOWLIST` env var (comma-separated, no per-email instructions):

```
ALLOWLIST=friend@example.com,colleague@company.org
```

### 4. Set up the knowledge base (optional)

Add facts about yourself so the agent can personalize replies:

```bash
cp knowledge.example.txt knowledge.txt
# Edit knowledge.txt - one fact per line
```

Example `knowledge.txt`:

```
I work at Google
My wife is allergic to nuts
I love steak
I'm a data scientist
```

The agent will use these when relevant (e.g., declining restaurant suggestions with nuts, mentioning your job in work emails).

### 5. Set your email signoff (optional)

Every email you send can end with a fixed signoff (e.g. "Best,\nBen"):

```bash
# Option A: use the CLI (use \n for newline)
python run.py signoff "Best,\nBen"

# Option B: copy the example file and edit
cp signoff.example.txt signoff.txt
# Edit signoff.txt with your preferred closing
```

You can also set `EMAIL_SIGNOFF=Best,\nBen` in `.env` if you prefer.

### 6. Run the agent

```bash
python run.py
```

The agent polls your inbox every 60 seconds. Use `--once` to process one batch and exit:

```bash
python run.py --once
```

## Calendar digest (optional)

If you regularly receive emails proposing dates/times (e.g. “Tue at 3?”), you can configure a scheduled digest that scans your inbox for those senders and emails you a summary.

### 1. Create the calendar allowlist

```bash
cp calendar_allowlist.example.txt calendar_allowlist.txt
# Edit calendar_allowlist.txt with sender emails to monitor
```

### 2. Configure the digest schedule

```bash
cp calendar_schedule.example.txt calendar_schedule.txt
# Edit calendar_schedule.txt
```

Schedule format (one rule per line):
- `18:00 daily`
- `10:00 sat`
- `09:30 mon,wed,fri`

The agent checks on each poll cycle and will send at the **exact scheduled minute**, so keep `--poll-interval` at 60 seconds if you want it to be reliable.

### 3. Test it once

```bash
python run.py calendar-digest
```

Digests are emailed **from you to you** (`SMTP_USER` → `SMTP_USER`) and the last-run timestamps are stored locally in `calendar_state.json` so you don’t get duplicates.

## Proton Mail Bridge Setup

1. Install [Proton Mail Bridge](https://proton.me/mail/bridge)
2. Sign in with your Proton account
3. Bridge runs locally and exposes:
   - **IMAP**: `127.0.0.1:1143` (STARTTLS)
   - **SMTP**: `127.0.0.1:1025` (STARTTLS)
4. Use your full email address as username and the Bridge-generated app password (not your Proton login password)
5. If you get SSL certificate errors, add `IMAP_SSL_SKIP_VERIFY=1` and `SMTP_SSL_SKIP_VERIFY=1` to `.env` (Bridge uses a self-signed cert for localhost)

Bridge must be running whenever the agent runs.

## Other Email Providers

Use your provider's IMAP/SMTP settings in `.env`. Examples:

- **Gmail**: Enable "App passwords" and use `imap.gmail.com:993` (SSL) / `smtp.gmail.com:587`
- **Outlook**: `outlook.office365.com` for both IMAP and SMTP
- **Fastmail**: See Fastmail’s IMAP/SMTP documentation

You may need to adjust the code for SSL vs STARTTLS depending on your provider.

## Giving the agent feedback

You can store feedback so the agent improves future suggestions (e.g. what you liked or didn’t like):

```bash
python run.py feedback "beef stew and chicken tacos were good meal suggestions; fajitas weren't"
```

Feedback is saved in `feedback.json` (or the path in `FEEDBACK_FILE`) and included in the LLM context for every reply. Add more feedback anytime; it accumulates.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_MODEL` | `claude-haiku-4-5` | Model for reply generation |
| `KNOWLEDGE` | (none) | Alternative to knowledge.txt: newline-separated facts as env var |
| `EMAIL_SIGNOFF` | (none) | Signoff appended to every email; `\n` for newline. Overrides signoff.txt if set. |
| `FEEDBACK_FILE` | `feedback.json` | Path to the JSON file where feedback is stored |

## License

MIT
