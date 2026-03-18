# Personal AI Employee - Project Context

## Project Overview

This is a **hackathon project** for building a "Digital FTE" (Full-Time Equivalent) - an autonomous AI employee that manages personal and business affairs 24/7. The project uses **Claude Code** as the reasoning engine and **Obsidian** (local Markdown) as the dashboard/memory system.

**Tagline:** *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

### Core Architecture

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Brain** | Claude Code | Reasoning engine, task execution |
| **Memory/GUI** | Obsidian Vault | Dashboard, knowledge base, state storage |
| **Senses** | Python Watchers | Monitor Gmail, WhatsApp, filesystems |
| **Hands** | MCP Servers | External actions (email, browser, payments) |

### Key Concepts

- **Watchers:** Lightweight Python scripts that monitor inputs and create `.md` files in `/Needs_Action` folder
- **Ralph Wiggum Loop:** A Stop hook pattern that keeps Claude iterating until tasks are complete
- **Human-in-the-Loop:** Sensitive actions require approval via file movement (`/Pending_Approval` → `/Approved`)
- **Agent Skills:** All AI functionality should be implemented as [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

## Directory Structure

```
Personal-AI-Employee/
├── .qwen/skills/           # Qwen Code skills (browsing-with-playwright)
├── scripts/                # (To be created) Watcher scripts, orchestrators
├── Vault/                  # (To be created) Obsidian vault
│   ├── Inbox/              # Raw incoming items
│   ├── Needs_Action/       # Items requiring processing
│   ├── In_Progress/        # Currently being worked on
│   ├── Done/               # Completed tasks
│   ├── Pending_Approval/   # Awaiting human approval
│   ├── Approved/           # Approved actions ready to execute
│   ├── Plans/              # Task plans with checkboxes
│   ├── Briefings/          # CEO briefings, reports
│   ├── Accounting/         # Bank transactions, invoices
│   └── Business_Goals.md   # Objectives, metrics, rules
├── QWEN.md                 # This file
├── skills-lock.json        # Qwen skills configuration
└── Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md  # Full blueprint
```

## Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| [Qwen Code](https://github.com/QwenLM/Qwen) | Active subscription | Primary reasoning engine |
| [Obsidian](https://obsidian.md/download) | v1.10.6+ | Knowledge base & dashboard |
| [Python](https://www.python.org/downloads/) | 3.13+ | Watcher scripts, orchestration |
| [Node.js](https://nodejs.org/) | v24+ LTS | MCP servers |
| [GitHub Desktop](https://desktop.github.com/download/) | Latest | Version control |

## Building & Running

### Start Playwright MCP Server (for browser automation)

```bash
# Start the browser MCP server
bash .qwen/skills/browsing-with-playwright/scripts/start-server.sh

# Verify it's running
python3 .qwen/skills/browsing-with-playwright/scripts/verify.py

# Stop when done
bash .qwen/skills/browsing-with-playwright/scripts/stop-server.sh
```

### Watcher Scripts (To be implemented)

```bash
# Example: Start Gmail watcher
python scripts/gmail_watcher.py

# Example: Start WhatsApp watcher
python scripts/whatsapp_watcher.py

# Example: Start file system watcher
python scripts/filesystem_watcher.py
```

### Qwen Code Integration

```bash
# Verify Qwen Code is installed
qwen --version

# Start autonomous loop for task completion
qwen "Process all files in /Needs_Action, move to /Done when complete"
```

### Scheduled Tasks

```bash
# Linux/Mac: Add to crontab for daily 8 AM briefing
0 8 * * * claude "Generate Monday Morning CEO Briefing from /Vault"

# Windows: Use Task Scheduler to run similar commands
```

## Development Conventions

### File Naming Patterns

- `EMAIL_{id}.md` - Email action items
- `WHATSAPP_{chat}_{timestamp}.md` - WhatsApp messages
- `FILE_{original_name}` - Dropped files for processing
- `PAYMENT_{recipient}_{date}.md` - Payment approval requests
- `{date}_{type}.md` - Briefings and reports

### Markdown Frontmatter Schema

All action files should include YAML frontmatter:

```yaml
---
type: email|whatsapp|payment|file_drop|approval_request
from: Sender name
subject: Subject line
received: ISO timestamp
priority: high|medium|low
status: pending|in_progress|completed
---
```

### Human-in-the-Loop Pattern

For sensitive actions (payments, sending messages):

1. Qwen creates approval request in `/Pending_Approval`
2. User reviews and moves file to `/Approved` or `/Rejected`
3. Orchestrator executes approved actions via MCP servers
4. Results logged, task moved to `/Done`

### Claim-by-Move Rule (Multi-Agent)

- First agent to move item from `/Needs_Action` to `/In_Progress/{agent}/` owns it
- Other agents must ignore claimed items
- Prevents duplicate work

## Available Skills

### browsing-with-playwright

Browser automation via Playwright MCP server. Use for:
- Web scraping
- Form submission
- UI testing
- Any browser interaction

**Server:** Runs on `http://localhost:8808`

**Key Tools:**
- `browser_navigate` - Navigate to URL
- `browser_snapshot` - Get page accessibility snapshot
- `browser_click` - Click element by ref
- `browser_type` - Type text into field
- `browser_fill_form` - Fill multiple form fields
- `browser_take_screenshot` - Capture screenshot
- `browser_evaluate` - Execute JavaScript

See `.qwen/skills/browsing-with-playwright/SKILL.md` for full documentation.

## Hackathon Tiers

| Tier | Requirements | Estimated Time |
|------|--------------|----------------|
| **Bronze** | Obsidian dashboard, 1 watcher, basic Claude integration | 8-12 hours |
| **Silver** | 2+ watchers, MCP server, approval workflow, scheduling | 20-30 hours |
| **Gold** | Full integration, Odoo accounting, social media, Ralph loop | 40+ hours |
| **Platinum** | Cloud deployment, 24/7 operation, multi-agent sync | 60+ hours |

## Key Resources

- **Full Blueprint:** `Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md`
- **Playwright Tools:** `.qwen/skills/browsing-with-playwright/references/playwright-tools.md`
- **Ralph Wiggum Pattern:** https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum
- **Agent Skills:** https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **MCP Servers:** https://github.com/modelcontextprotocol/servers

## Meeting Schedule

**Research & Showcase:** Every Wednesday at 10:00 PM PKT on Zoom
- First meeting: Wednesday, Jan 7th, 2026
- [Zoom Link](https://us06web.zoom.us/j/87188707642?pwd=a9XloCsinvn1JzICbPc2YGUvWTbOTr.1)
- Meeting ID: 871 8870 7642, Passcode: 744832
