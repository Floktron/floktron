#!/bin/bash
# FLOKTRON · check the bot token and the dialog file
cd "$(dirname "$0")/../../.."
python3 -c "import openpyxl, yaml" 2>/dev/null || python3 -m pip install --user -r requirements.txt
python3 scripts/bot/telegram_bot.py --flow-check && python3 scripts/bot/telegram_bot.py --check
read -p "Press Enter to close"
