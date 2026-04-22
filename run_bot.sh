#!/bin/bash
# run_bot.sh — Called by cron at 9:28 AM ET Monday–Friday
# Loads env vars, activates venv, runs the bot

set -e

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env
if [ -f "$BOT_DIR/.env" ]; then
    export $(grep -v '^#' "$BOT_DIR/.env" | xargs)
fi

# Activate virtual environment
source "$BOT_DIR/.venv/bin/activate"

# Run the bot — logs go to dated log file
LOG_FILE="$BOT_DIR/logs/bot_$(date +%Y-%m-%d).log"
mkdir -p "$BOT_DIR/logs"

echo "=== Bot started at $(date) ===" >> "$LOG_FILE"
python "$BOT_DIR/bot/main.py" >> "$LOG_FILE" 2>&1
echo "=== Bot finished at $(date) ===" >> "$LOG_FILE"
