#!/bin/bash
# Stop Bronze Tier AI Employee Services
# Usage: bash stop-bronze.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping AI Employee services..."

# Stop Watcher
if [ -f "$SCRIPT_DIR/watcher.pid" ]; then
    WATCHER_PID=$(cat "$SCRIPT_DIR/watcher.pid")
    if kill -0 "$WATCHER_PID" 2>/dev/null; then
        kill "$WATCHER_PID"
        echo "✓ Watcher stopped (PID: $WATCHER_PID)"
    else
        echo "⚠️  Watcher not running"
    fi
    rm "$SCRIPT_DIR/watcher.pid"
fi

# Stop Orchestrator
if [ -f "$SCRIPT_DIR/orchestrator.pid" ]; then
    ORCHESTRATOR_PID=$(cat "$SCRIPT_DIR/orchestrator.pid")
    if kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
        kill "$ORCHESTRATOR_PID"
        echo "✓ Orchestrator stopped (PID: $ORCHESTRATOR_PID)"
    else
        echo "⚠️  Orchestrator not running"
    fi
    rm "$SCRIPT_DIR/orchestrator.pid"
fi

# Kill any remaining Python processes for our scripts
pkill -f "filesystem_watcher.py" 2>/dev/null && echo "✓ Cleaned up filesystem_watcher"
pkill -f "orchestrator.py" 2>/dev/null && echo "✓ Cleaned up orchestrator"

echo ""
echo "All services stopped."
