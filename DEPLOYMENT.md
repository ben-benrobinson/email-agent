# Deploying the Email Agent on AWS

Step-by-step guide to run the agent 24/7 on an EC2 instance.

---

## Option A: Gmail (Simplest)

Use Gmail instead of Proton—no Bridge required.

### 1. Create an EC2 instance

1. **AWS Console** → EC2 → Launch instance
2. **Name:** `email-agent`
3. **AMI:** Ubuntu 22.04 LTS
4. **Instance type:** `t3.micro` (free tier eligible)
5. **Key pair:** Create new or select existing (download `.pem`)
6. **Security group:** Allow SSH (22) from your IP
7. Launch

### 2. Connect and install dependencies

```bash
# Replace with your instance's public IP and key path
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install -y python3 python3-venv python3-pip git
```

### 3. Set up Gmail (if not already)

1. Enable 2FA on your Google account
2. Create an [App Password](https://myaccount.google.com/apppasswords): Google Account → Security → 2-Step Verification → App passwords
3. Generate a 16-character password for "Mail"

### 4. Deploy the agent

```bash
# Clone (or scp your repo)
git clone https://github.com/YOUR_USERNAME/email-agent.git
cd email-agent

# Create venv and install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Create config files

```bash
# .env (use your Gmail and Anthropic key)
cat > .env << 'EOF'
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=you@gmail.com
IMAP_PASSWORD=your-app-password

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password

ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_MODEL=claude-haiku-4-5
EOF

# allowlist.txt
cat > allowlist.txt << 'EOF'
friend@example.com
EOF

# knowledge.txt
cat > knowledge.txt << 'EOF'
I work at Google
My wife is allergic to nuts
EOF
```

**Note:** Gmail uses SSL on 993/587. The current code uses STARTTLS; you may need `imaplib.IMAP4_SSL` for port 993 and `smtplib.SMTP` with `starttls()` for 587. See "Gmail Compatibility" below if connection fails.

### 6. Create systemd service

```bash
sudo nano /etc/systemd/system/email-agent.service
```

```ini
[Unit]
Description=Email Agent
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=30
User=ubuntu
WorkingDirectory=/home/ubuntu/email-agent
ExecStart=/home/ubuntu/email-agent/venv/bin/python run.py
Environment="PATH=/home/ubuntu/email-agent/venv/bin"

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable email-agent
sudo systemctl start email-agent
sudo systemctl status email-agent
```

### 7. View logs

```bash
journalctl -u email-agent -f
```

---

## Option B: Proton Mail (Bridge on EC2)

Keep Proton—run Bridge headless on the same EC2 instance.

### 1. Create EC2 instance

Same as Option A: Ubuntu 22.04, t3.micro, SSH access.

### 2. Install Proton Bridge via Docker

```bash
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose python3 python3-venv python3-pip git
sudo usermod -aG docker ubuntu
# Log out and back in for docker group to take effect
exit
```

Reconnect, then:

```bash
# Create directory for Bridge
mkdir -p ~/proton-bridge && cd ~/proton-bridge

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3'
services:
  proton-bridge:
    image: syphr/proton-bridge:latest
    container_name: proton-bridge
    restart: unless-stopped
    ports:
      - "1143:1143"  # IMAP
      - "1025:1025"  # SMTP
    volumes:
      - ./bridge-data:/root/.config/protonmail/bridge
    environment:
      - BRIDGE_PASSWORD=changeme
EOF

# Initial login (interactive - run once)
docker compose run --rm -it proton-bridge
# Follow prompts: log in with Proton credentials, get Bridge password
# Save the Bridge password for .env
# Ctrl+C when done
```

### 3. Start Bridge in background

```bash
cd ~/proton-bridge
docker compose up -d
```

Update `docker-compose.yml` to bind to 127.0.0.1 only (so Bridge is not exposed):

```yaml
ports:
  - "127.0.0.1:1143:1143"
  - "127.0.0.1:1025:1025"
```

Then `docker compose up -d --force-recreate`.

### 4. Deploy the agent

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/email-agent.git
cd email-agent

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Create .env (Proton)

```bash
cat > .env << 'EOF'
IMAP_HOST=127.0.0.1
IMAP_PORT=1143
IMAP_USER=ben@benrobinson.io
IMAP_PASSWORD=your-bridge-password

SMTP_HOST=127.0.0.1
SMTP_PORT=1025
SMTP_USER=ben@benrobinson.io
SMTP_PASSWORD=your-bridge-password

IMAP_SSL_SKIP_VERIFY=1
SMTP_SSL_SKIP_VERIFY=1

ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_MODEL=claude-haiku-4-5
EOF
```

Create `allowlist.txt` and `knowledge.txt` as in Option A.

### 6. Create systemd service

Same as Option A, but ensure Bridge starts before the agent. Add to the service file:

```ini
[Unit]
Description=Email Agent
After=network.target docker.service
Requires=docker.service
```

### 7. Ensure Bridge starts on boot

Docker Compose with `restart: unless-stopped` will auto-start Bridge. Reboot the instance to test:

```bash
sudo reboot
```

After reconnect, check:

```bash
docker ps
sudo systemctl status email-agent
```

---

## Gmail Compatibility

If using Gmail (Option A), the default IMAP/SMTP code uses plain TCP + STARTTLS. Gmail's IMAP uses SSL on port 993 (direct TLS), not STARTTLS. You may need code changes:

- **IMAP 993:** Use `imaplib.IMAP4_SSL` instead of `IMAP4` + `starttls()`
- **SMTP 587:** `smtplib.SMTP` + `starttls()` is correct

If you hit connection errors with Gmail, open an issue or adapt `email_client.py` for SSL connections.

---

## Costs

- **t3.micro:** Free tier (750 hrs/month) or ~$7.50/month
- **EBS:** ~$0.80/month for 8GB
- **Data transfer:** Minimal for email polling

---

## Updating the agent

```bash
cd ~/email-agent
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart email-agent
```
