#!/bin/bash
# FLOKTRON · remove the bot from Login Items (stop it by closing its Terminal window)
osascript -e 'tell application "System Events" to delete login item "3_bot_start.command"' 2>/dev/null && echo "Autostart off." || echo "Autostart was not on."
read -p "Press Enter to close"
