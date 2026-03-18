#!/bin/bash
# Start Gold Tier AI Employee Services
# Usage: bash start-gold.sh [vault_path]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_PATH="${1:-$SCRIPT_DIR/../Vault}"

echo "========================================"
echo "  AI Employee - Gold Tier Startup"
echo "========================================"
echo ""
echo "Vault Path: $VAULT_PATH"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi
echo "✓ Python: $(python3 --version)"

# Check Qwen Code
if ! command -v qwen &> /dev/null; then
    echo "⚠️  Qwen Code not found. Ensure it's installed and in PATH"
else
    echo "✓ Qwen Code: $(qwen --version 2>/dev/null || echo 'Available')"
fi

# Activate virtual environment or create it
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi
source "$SCRIPT_DIR/.venv/bin/activate"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
cd "$SCRIPT_DIR"
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Install Playwright browsers if needed
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "Installing Playwright browsers..."
    playwright install chromium
fi

# Create necessary directories
echo ""
echo "Setting up vault directories..."
mkdir -p "$VAULT_PATH"/{Drop,Files,Logs,Briefings,Posts,Accounting}
mkdir -p "$VAULT_PATH/Posts"/{Pending,Approved,Rejected,Published}
mkdir -p "$VAULT_PATH/Logs/Audit"
echo "✓ Directories ready"

# Start watchers based on configuration
echo ""
echo "Starting watchers..."

# File System Watcher (always available)
echo "  - Starting File System Watcher..."
python3 "$SCRIPT_DIR/filesystem_watcher.py" "$VAULT_PATH" --interval 30 &
WATCHER_PID=$!
echo "    ✓ File Watcher started (PID: $WATCHER_PID)"

# Gmail Watcher (if credentials exist)
if [ -f "$SCRIPT_DIR/credentials.json" ] || [ -f "${GMAIL_CREDENTIALS_PATH:-}" ]; then
    echo "  - Starting Gmail Watcher..."
    python3 "$SCRIPT_DIR/gmail_watcher.py" "$VAULT_PATH" --interval 120 &
    GMAIL_PID=$!
    echo "    ✓ Gmail Watcher started (PID: $GMAIL_PID)"
else
    echo "  ⚠️  Gmail credentials not found. Skipping Gmail Watcher."
fi

# WhatsApp Watcher (optional)
if [ -d "$VAULT_PATH/whatsapp_session" ] || [ -n "${WHATSAPP_SESSION_PATH:-}" ]; then
    echo "  - Starting WhatsApp Watcher..."
    python3 "$SCRIPT_DIR/whatsapp_watcher.py" "$VAULT_PATH" --interval 60 &
    WHATSAPP_PID=$!
    echo "    ✓ WhatsApp Watcher started (PID: $WHATSAPP_PID)"
else
    echo "  ⚠️  WhatsApp session not found. Skipping WhatsApp Watcher."
fi

# LinkedIn Watcher (optional)
if [ -d "$VAULT_PATH/linkedin_session" ] || [ -n "${LINKEDIN_SESSION_PATH:-}" ]; then
    echo "  - Starting LinkedIn Watcher..."
    python3 "$SCRIPT_DIR/linkedin_watcher.py" "$VAULT_PATH" --interval 300 &
    LINKEDIN_PID=$!
    echo "    ✓ LinkedIn Watcher started (PID: $LINKEDIN_PID)"
else
    echo "  ⚠️  LinkedIn session not found. Skipping LinkedIn Watcher."
fi

# Start Orchestrator with Ralph Wiggum loop
echo ""
echo "Starting Orchestrator with Ralph Wiggum Loop..."
python3 "$SCRIPT_DIR/orchestrator.py" "$VAULT_PATH" --interval 30 &
ORCHESTRATOR_PID=$!
echo "✓ Orchestrator started (PID: $ORCHESTRATOR_PID)"

# Start Health Monitor (Gold tier)
echo ""
echo "Starting Health Monitor..."
python3 -c "
from error_recovery import HealthMonitor
from pathlib import Path
monitor = HealthMonitor(Path('$VAULT_PATH'))
print('✓ Health Monitor initialized')
" &
HEALTH_PID=$!
echo "✓ Health Monitor started (PID: $HEALTH_PID)"

# Save PIDs for cleanup
echo "$WATCHER_PID" > "$SCRIPT_DIR/watcher.pid"
echo "$ORCHESTRATOR_PID" > "$SCRIPT_DIR/orchestrator.pid"
echo "$HEALTH_PID" > "$SCRIPT_DIR/health.pid"
[ -n "$GMAIL_PID" ] && echo "$GMAIL_PID" > "$SCRIPT_DIR/gmail_watcher.pid"
[ -n "$WHATSAPP_PID" ] && echo "$WHATSAPP_PID" > "$SCRIPT_DIR/whatsapp_watcher.pid"
[ -n "$LINKEDIN_PID" ] && echo "$LINKEDIN_PID" > "$SCRIPT_DIR/linkedin_watcher.pid"

echo ""
echo "========================================"
echo "  Gold Tier Services Running"
echo "========================================"
echo ""
echo "Features enabled:"
echo "  ✓ File System Watcher"
echo "  ✓ Gmail Watcher (if configured)"
echo "  ✓ WhatsApp Watcher (if configured)"
echo "  ✓ LinkedIn Watcher (if configured)"
echo "  ✓ Orchestrator with Ralph Wiggum Loop"
echo "  ✓ Health Monitor with Auto-Recovery"
echo "  ✓ Comprehensive Audit Logging"
echo ""
echo "To test:"
echo "  1. Drop a file: echo 'test' > $VAULT_PATH/Drop/test.txt"
echo "  2. Check Needs_Action folder for new action file"
echo "  3. Run Qwen Code: cd $VAULT_PATH && qwen"
echo ""
echo "Gold tier commands:"
echo "  - Run Ralph Loop: python3 $SCRIPT_DIR/ralph_loop.py $VAULT_PATH \"Process all pending items\""
echo "  - View audit logs: ls $VAULT_PATH/Logs/Audit/"
echo "  - Health check: python3 $SCRIPT_DIR/orchestrator.py $VAULT_PATH --once"
echo ""
echo "To stop: bash $SCRIPT_DIR/stop-gold.sh"
echo ""

# Keep script running to show logs
wait
