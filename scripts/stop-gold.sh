#!/bin/bash
# Stop Gold Tier AI Employee Services
# Usage: bash stop-gold.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping AI Employee services..."

# Stop Watcher
if [ -f "$SCRIPT_DIR/watcher.pid" ]; then
    WATCHER_PID=$(cat "$SCRIPT_DIR/watcher.pid")
    if kill -0 "$WATCHER_PID" 2>/dev/null; then
        kill "$WATCHER_PID"
        echo "✓ File Watcher stopped (PID: $WATCHER_PID)"
    else
        echo "⚠️  File Watcher not running"
    fi
    rm "$SCRIPT_DIR/watcher.pid"
fi

# Stop Gmail Watcher
if [ -f "$SCRIPT_DIR/gmail_watcher.pid" ]; then
    GMAIL_PID=$(cat "$SCRIPT_DIR/gmail_watcher.pid")
    if kill -0 "$GMAIL_PID" 2>/dev/null; then
        kill "$GMAIL_PID"
        echo "✓ Gmail Watcher stopped (PID: $GMAIL_PID)"
    else
        echo "⚠️  Gmail Watcher not running"
    fi
    rm "$SCRIPT_DIR/gmail_watcher.pid"
fi

# Stop WhatsApp Watcher
if [ -f "$SCRIPT_DIR/whatsapp_watcher.pid" ]; then
    WHATSAPP_PID=$(cat "$SCRIPT_DIR/whatsapp_watcher.pid")
    if kill -0 "$WHATSAPP_PID" 2>/dev/null; then
        kill "$WHATSAPP_PID"
        echo "✓ WhatsApp Watcher stopped (PID: $WHATSAPP_PID)"
    else
        echo "⚠️  WhatsApp Watcher not running"
    fi
    rm "$SCRIPT_DIR/whatsapp_watcher.pid"
fi

# Stop LinkedIn Watcher
if [ -f "$SCRIPT_DIR/linkedin_watcher.pid" ]; then
    LINKEDIN_PID=$(cat "$SCRIPT_DIR/linkedin_watcher.pid")
    if kill -0 "$LINKEDIN_PID" 2>/dev/null; then
        kill "$LINKEDIN_PID"
        echo "✓ LinkedIn Watcher stopped (PID: $LINKEDIN_PID)"
    else
        echo "⚠️  LinkedIn Watcher not running"
    fi
    rm "$SCRIPT_DIR/linkedin_watcher.pid"
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

# Stop Health Monitor
if [ -f "$SCRIPT_DIR/health.pid" ]; then
    HEALTH_PID=$(cat "$SCRIPT_DIR/health.pid")
    if kill -0 "$HEALTH_PID" 2>/dev/null; then
        kill "$HEALTH_PID"
        echo "✓ Health Monitor stopped (PID: $HEALTH_PID)"
    else
        echo "⚠️  Health Monitor not running"
    fi
    rm "$SCRIPT_DIR/health.pid"
fi

# Kill any remaining Python processes for our scripts
pkill -f "filesystem_watcher.py" 2>/dev/null && echo "✓ Cleaned up filesystem_watcher"
pkill -f "gmail_watcher.py" 2>/dev/null && echo "✓ Cleaned up gmail_watcher"
pkill -f "whatsapp_watcher.py" 2>/dev/null && echo "✓ Cleaned up whatsapp_watcher"
pkill -f "linkedin_watcher.py" 2>/dev/null && echo "✓ Cleaned up linkedin_watcher"
pkill -f "orchestrator.py" 2>/dev/null && echo "✓ Cleaned up orchestrator"
pkill -f "briefing_generator.py" 2>/dev/null && echo "✓ Cleaned up briefing_generator"
pkill -f "ralph_loop.py" 2>/dev/null && echo "✓ Cleaned up ralph_loop"
pkill -f "audit_logger.py" 2>/dev/null && echo "✓ Cleaned up audit_logger"
pkill -f "error_recovery.py" 2>/dev/null && echo "✓ Cleaned up error_recovery"

echo ""
echo "All services stopped."
