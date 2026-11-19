#!/bin/bash
# FLOKTRON · start the bot at every login (Login Items, through Terminal — works also when FLOKTRON is in iCloud) and start it now.
DIR="$(cd "$(dirname "$0")" && pwd)"
osascript -e "tell application \"System Events\" to if not (exists login item \"3_bot_start.command\") then make login item at end with properties {path:\"$DIR/3_bot_start.command\", hidden:true}" \
  && echo "✅ The bot starts at login." || echo "⚠️ Add it by hand: System Settings → General → Login Items → + → 3_bot_start.command"
open "$DIR/3_bot_start.command"
read -p "Press Enter to close"
