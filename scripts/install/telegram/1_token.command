#!/bin/bash
# FLOKTRON · save the Telegram bot token to the macOS Keychain (never into files, chat or Terminal history).
# config.yaml → telegram: keychain_service: "FLOKTRON_TG_BOT"
echo "Paste the token from @BotFather (Cmd+V) and press Enter. Nothing is shown — that is normal. Then once more."
security add-generic-password -U -s FLOKTRON_TG_BOT -a floktron -w && echo "✅ Token saved (Keychain item FLOKTRON_TG_BOT)." || echo "⚠️ Not saved."
read -p "Press Enter to close"
