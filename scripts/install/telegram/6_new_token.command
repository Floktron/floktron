#!/bin/bash
# FLOKTRON · replace the bot token in one step (after @BotFather → /mybots → API Token → Revoke current token).
# The new token is typed hidden, checked with Telegram and saved to the Keychain — never to a file. Then the bot restarts.
cd "$(dirname "$0")/../../.."
echo "1) In Telegram: @BotFather (blue check mark) → /mybots → your bot → API Token → Revoke current token → copy the new one."
python3 scripts/bot/telegram_bot.py --set-token || { read -p "Nothing changed. Press Enter to close"; exit 1; }
pkill -f "telegram_bot.py --loop" 2>/dev/null && echo "⏹ Old bot stopped."; sleep 2
open "scripts/install/telegram/3_bot_start.command" && echo "▶️ Bot started again with the new token (separate window)."
echo "2) Send /version to your bot — it must answer. 3) Check Telegram → Settings → Devices for unknown sessions."
read -p "Press Enter to close"
