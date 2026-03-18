#!/bin/bash
# Setup Cron Jobs for AI Employee
# Usage: bash setup_cron.sh [vault_path]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_PATH="${1:-$SCRIPT_DIR/../Vault}"
PYTHON_VENV="$SCRIPT_DIR/.venv/bin/python3"

echo "========================================"
echo "  AI Employee - Cron Setup"
echo "========================================"
echo ""
echo "Vault Path: $VAULT_PATH"
echo "Python: $PYTHON_VENV"
echo ""

# Get current crontab
CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

# Define cron jobs
CRON_JOBS=""

# Daily briefing at 8 AM
CRON_JOBS+="0 8 * * * $PYTHON_VENV $SCRIPT_DIR/briefing_generator.py $VAULT_PATH --type daily >> $VAULT_PATH/Logs/cron_briefing.log 2>&1\n"

# Weekly briefing on Monday at 7 AM
CRON_JOBS+="0 7 * * 1 $PYTHON_VENV $SCRIPT_DIR/briefing_generator.py $VAULT_PATH --type weekly --days 7 >> $VAULT_PATH/Logs/cron_weekly.log 2>&1\n"

# Hourly orchestrator health check (optional)
# CRON_JOBS+="0 * * * * $PYTHON_VENV $SCRIPT_DIR/orchestrator.py $VAULT_PATH --once >> $VAULT_PATH/Logs/cron_orchestrator.log 2>&1\n"

echo "Cron jobs to be added:"
echo "----------------------"
echo -e "$CRON_JOBS"
echo "----------------------"
echo ""

# Ask for confirmation
read -p "Add these cron jobs? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Add new cron jobs
    NEW_CRON="$CURRENT_CRON"$'\n'"$(echo -e "$CRON_JOBS")"
    echo "$NEW_CRON" | crontab -
    echo ""
    echo "✓ Cron jobs added successfully"
    echo ""
    echo "Current crontab:"
    crontab -l
else
    echo "Cron jobs not added"
fi

echo ""
echo "To view cron logs:"
echo "  tail -f $VAULT_PATH/Logs/cron_*.log"
echo ""
echo "To remove cron jobs:"
echo "  crontab -e  # Edit and remove unwanted lines"
