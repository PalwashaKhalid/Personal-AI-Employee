#!/bin/bash
# Start Bronze Tier AI Employee Services
# Usage: bash start-bronze.sh [vault_path]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_PATH="${1:-$SCRIPT_DIR/../Vault}"

echo "========================================"
echo "  AI Employee - Bronze Tier Startup"
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

# Create necessary directories
echo ""
echo "Setting up vault directories..."
mkdir -p "$VAULT_PATH"/{Drop,Files,Logs}
echo "✓ Directories ready"

# Start File System Watcher in background
echo ""
echo "Starting File System Watcher..."
python3 "$SCRIPT_DIR/filesystem_watcher.py" "$VAULT_PATH" --interval 30 &
WATCHER_PID=$!
echo "✓ Watcher started (PID: $WATCHER_PID)"

# Start Orchestrator in background
echo ""
echo "Starting Orchestrator..."
python3 "$SCRIPT_DIR/orchestrator.py" "$VAULT_PATH" --interval 30 &
ORCHESTRATOR_PID=$!
echo "✓ Orchestrator started (PID: $ORCHESTRATOR_PID)"

# Save PIDs for cleanup
echo "$WATCHER_PID" > "$SCRIPT_DIR/watcher.pid"
echo "$ORCHESTRATOR_PID" > "$SCRIPT_DIR/orchestrator.pid"

echo ""
echo "========================================"
echo "  Bronze Tier Services Running"
echo "========================================"
echo ""
echo "To test:"
echo "  1. Drop a file: echo 'test' > $VAULT_PATH/Drop/test.txt"
echo "  2. Check Needs_Action folder for new action file"
echo "  3. Run Claude Code: cd $VAULT_PATH && claude"
echo ""
echo "To stop: bash $SCRIPT_DIR/stop-bronze.sh"
echo ""

# Keep script running to show logs
wait
