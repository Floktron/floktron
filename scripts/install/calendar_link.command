#!/bin/bash
# FLOKTRON · save the private link of your calendar (.ics) to the macOS Keychain (never into files, chat or Terminal history).
# config.yaml → calendar: keychain_service: "FLOKTRON_CAL". How to find the link: docs/CALENDAR.md
echo "Paste the private calendar link (starts with https:// or webcal://, Cmd+V) and press Enter. Nothing is shown — that is normal. Then once more."
security add-generic-password -U -s FLOKTRON_CAL -a floktron -w && echo "✅ Link saved (Keychain item FLOKTRON_CAL)." || echo "⚠️ Not saved."
cd "$(dirname "$0")/../.." && python3 scripts/calendar_read.py --check
read -p "Press Enter to close"
