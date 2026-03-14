# Email Agent

An LLM-powered email agent that automatically responds to emails from an allowlist of addresses. Designed for use with **Proton Mail** (via Proton Bridge) or any IMAP/SMTP provider.

## Features

- **Allowlist**: Only responds to emails from addresses you've approved
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
```

Or use the `ALLOWLIST` env var (comma-separated):

```
ALLOWLIST=friend@example.com,colleague@company.org
```

### 4. Run the agent

```bash
python run.py
```

The agent polls your inbox every 60 seconds. Use `--once` to process one batch and exit:

```bash
python run.py --once
```

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

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_MODEL` | `claude-haiku-4-5` | Model for reply generation |

## License

MIT
