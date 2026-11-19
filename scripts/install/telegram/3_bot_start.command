#!/bin/bash
# FLOKTRON · run the bot. While this window is open the bot works (minimise it). It also runs the channel watch at telegram.watch_times.
cd "$(dirname "$0")/../../.."
if pgrep -f "telegram_bot.py --loop" >/dev/null || pgrep -f "telegram_bot.py --config" >/dev/null; then echo "The bot is already running."; sleep 3; exit 0; fi
mkdir -p data; python3 scripts/bot/telegram_bot.py --loop 2>&1 | tee -a data/bot.log
read -p "Bot stopped. Press Enter to close"
