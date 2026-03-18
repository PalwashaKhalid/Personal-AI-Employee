# AI Employee Scripts - Silver Tier

Python scripts for the Personal AI Employee system.

## Quick Start (Silver Tier)

### 1. Install Dependencies

```bash
cd scripts
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Silver Tier Services

```bash
# Start all services
bash start-silver.sh ../Vault

# Or with custom vault path
bash start-silver.sh /path/to/vault
```

### 3. Test the Flow

```bash
# Drop a file
echo "Test content" > ../Vault/Drop/test_file.txt

# Wait for watcher to detect (30 seconds)

# Check Needs_Action folder
ls ../Vault/Needs_Action/

# Generate daily briefing
python3 briefing_generator.py ../Vault --type daily
```

### 4. Stop Services

```bash
bash stop-silver.sh
```

## Scripts Overview

| Script | Purpose | Tier |
|--------|---------|------|
| `base_watcher.py` | Abstract base class for all watchers | Bronze |
| `filesystem_watcher.py` | Monitors drop folder for new files | Bronze |
| `gmail_watcher.py` | Monitors Gmail for new emails | Silver |
| `whatsapp_watcher.py` | Monitors WhatsApp Web for messages | Silver |
| `orchestrator.py` | Triggers Qwen Code, manages tasks | Silver |
| `planning.py` | Generates task plans | Silver |
| `approval_workflow.py` | Human-in-the-loop approvals | Silver |
| `briefing_generator.py` | CEO briefing generation | Silver |
| `email_mcp_server.py` | Email sending via MCP | Silver |

## Shell Scripts

| Script | Purpose |
|--------|---------|
| `start-silver.sh` | Start all Silver tier services |
| `stop-silver.sh` | Stop all services |
| `setup_cron.sh` | Set up scheduled tasks |

## Folder Structure

```
Vault/
├── Drop/               # Drop files here for processing
├── Needs_Action/       # Pending action items
├── Plans/              # Task plans (auto-generated)
├── Done/               # Completed tasks
├── Pending_Approval/   # Awaiting human approval
├── Approved/           # Approved, ready to execute
├── Rejected/           # Declined actions
├── Files/              # Processed files
├── Briefings/          # CEO briefings
├── Logs/               # Activity logs
├── Dashboard.md        # Main dashboard
├── Company_Handbook.md # Rules of engagement
└── Business_Goals.md   # Objectives and metrics
```

## Watcher Configuration

### Gmail Watcher Setup

1. Enable Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com
2. Create OAuth2 credentials
3. Download `credentials.json` to `scripts/` folder
4. First run will require OAuth authentication

```bash
python3 gmail_watcher.py ../Vault --credentials credentials.json
```

### WhatsApp Watcher Setup

```bash
# First run creates session
python3 whatsapp_watcher.py ../Vault

# Session stored in Vault/Logs/whatsapp_session/
```

**Note:** WhatsApp Web automation may violate WhatsApp's terms of service. For production, use the official WhatsApp Business API.

## Scheduled Tasks

### Set Up Cron Jobs

```bash
bash setup_cron.sh ../Vault
```

This adds:
- Daily briefing at 8:00 AM
- Weekly briefing on Monday at 7:00 AM

### Manual Briefing Generation

```bash
# Daily briefing
python3 briefing_generator.py ../Vault --type daily

# Weekly briefing
python3 briefing_generator.py ../Vault --type weekly --days 7

# Monthly briefing
python3 briefing_generator.py ../Vault --type monthly --days 30
```

## Human-in-the-Loop Workflow

1. **Sensitive action detected** → Approval request created in `Pending_Approval/`
2. **Human reviews** → Move file to `Approved/` or `Rejected/`
3. **Orchestrator executes** → Approved actions executed, moved to `Done/`

### Approval File Example

```markdown
---
type: approval_request
action: send_email
created: 2026-02-27T10:00:00
status: pending
---

# Approval Required

**Action Type:** Send Email

## Action Details
| Field | Value |
|-------|-------|
| To | client@example.com |
| Subject | Invoice #123 |

## Instructions
- Move to `/Approved` to execute
- Move to `/Rejected` to decline
```

## Troubleshooting

### Watcher not detecting files

1. Check logs in `Vault/Logs/`
2. Verify the Drop folder exists
3. Ensure file permissions allow reading

### Qwen not triggering

1. Verify Qwen Code is installed: `qwen --version`
2. Check logs for error details

### Gmail authentication fails

1. Ensure `credentials.json` is in the scripts folder
2. Delete `Vault/Logs/gmail_token.json` and re-authenticate
3. Check Gmail API is enabled in Google Cloud Console

### WhatsApp watcher crashes

1. Install Playwright browsers: `playwright install chromium`
2. Check session folder permissions
3. Try running with headless=False for debugging

### Python import errors

1. Activate venv: `source .venv/bin/activate`
2. Reinstall dependencies: `pip install -r requirements.txt`

## For Gold Tier

To upgrade to Gold tier, add:
- Odoo accounting integration
- Social media posting (LinkedIn, Twitter, Facebook)
- Ralph Wiggum loop for autonomous operation
- Comprehensive error recovery
- Audit logging

## Security Notes

- Never commit `credentials.json` or `.env` files
- Store tokens in `Vault/Logs/` (gitignored)
- Review all approval requests before approving
- Regularly rotate API credentials
