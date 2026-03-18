#!/bin/bash
# Start Silver Tier AI Employee Services
# Usage: bash start-silver.sh [vault_path]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_PATH="${1:-$SCRIPT_DIR/../Vault}"

echo "========================================"
echo "  AI Employee - Silver Tier Startup"
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
mkdir -p "$VAULT_PATH"/{Drop,Files,Logs,Briefings}
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
    echo "      To enable: Add credentials.json to scripts/ folder"
fi

# WhatsApp Watcher (optional - requires manual setup)
if [ -d "$VAULT_PATH/whatsapp_session" ] || [ -n "${WHATSAPP_SESSION_PATH:-}" ]; then
    echo "  - Starting WhatsApp Watcher..."
    python3 "$SCRIPT_DIR/whatsapp_watcher.py" "$VAULT_PATH" --interval 60 &
    WHATSAPP_PID=$!
    echo "    ✓ WhatsApp Watcher started (PID: $WHATSAPP_PID)"
else
    echo "  ⚠️  WhatsApp session not found. Skipping WhatsApp Watcher."
    echo "      To enable: Run WhatsApp watcher once to create session"
fi

# LinkedIn Watcher (for auto-posting)
if [ -d "$VAULT_PATH/linkedin_session" ] || [ -n "${LINKEDIN_SESSION_PATH:-}" ]; then
    echo "  - Starting LinkedIn Watcher..."
    python3 "$SCRIPT_DIR/linkedin_watcher.py" "$VAULT_PATH" --interval 300 &
    LINKEDIN_PID=$!
    echo "    ✓ LinkedIn Watcher started (PID: $LINKEDIN_PID)"
else
    echo "  ⚠️  LinkedIn session not found. Skipping LinkedIn Watcher."
    echo "      To enable: Run 'python3 linkedin_watcher.py VAULT_PATH --post \"Test\"' to authenticate"
fi

# Start Orchestrator
echo ""
echo "Starting Orchestrator..."
python3 "$SCRIPT_DIR/orchestrator.py" "$VAULT_PATH" --interval 30 &
ORCHESTRATOR_PID=$!
echo "✓ Orchestrator started (PID: $ORCHESTRATOR_PID)"

# Save PIDs for cleanup
echo "$WATCHER_PID" > "$SCRIPT_DIR/watcher.pid"
echo "$ORCHESTRATOR_PID" > "$SCRIPT_DIR/orchestrator.pid"
[ -n "$GMAIL_PID" ] && echo "$GMAIL_PID" > "$SCRIPT_DIR/gmail_watcher.pid"
[ -n "$WHATSAPP_PID" ] && echo "$WHATSAPP_PID" > "$SCRIPT_DIR/whatsapp_watcher.pid"
[ -n "$LINKEDIN_PID" ] && echo "$LINKEDIN_PID" > "$SCRIPT_DIR/linkedin_watcher.pid"

echo ""
echo "========================================"
echo "  Silver Tier Services Running"
echo "========================================"
echo ""
echo "To test:"
echo "  1. Drop a file: echo 'test' > $VAULT_PATH/Drop/test.txt"
echo "  2. Check Needs_Action folder for new action file"
echo "  3. Run Qwen Code: cd $VAULT_PATH && qwen"
echo ""
echo "To generate daily briefing:"
echo "  python3 $SCRIPT_DIR/briefing_generator.py $VAULT_PATH --type daily"
echo ""
echo "To stop: bash $SCRIPT_DIR/stop-silver.sh"
echo ""

# Keep script running to show logs
wait
