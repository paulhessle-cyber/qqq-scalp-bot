#!/bin/bash
# run_alert.sh — called by cron at 8:58 AM ET Mon–Fri
# Gives the bot time to start before 9:00 AM

BOT_DIR="/root/qqq-alert-bot"

if [ -f "$BOT_DIR/.env" ]; then
    export $(grep -v '^#' "$BOT_DIR/.env" | xargs)
fi

source "$BOT_DIR/.venv/bin/activate"

LOG_FILE="$BOT_DIR/logs/alert_$(date +%Y-%m-%d).log"
mkdir -p "$BOT_DIR/logs"

echo "=== Alert bot started at $(date) ===" >> "$LOG_FILE"
python "$BOT_DIR/alert_bot.py" >> "$LOG_FILE" 2>&1
echo "=== Alert bot finished at $(date) ===" >> "$LOG_FILE"
