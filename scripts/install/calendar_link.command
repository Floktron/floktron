#!/bin/bash
# FLOKTRON · save the private link of your calendar (.ics) to the macOS Keychain (never into files, chat or Terminal history).
# config.yaml → calendar: keychain_service: "FLOKTRON_CAL". How to find the link: docs/CALENDAR.md
# The link is read in full: the macOS password prompt cuts input at 128 characters, and calendar links are longer.
echo "Paste the private calendar link (starts with https:// or webcal://, Cmd+V) and press Enter. Nothing is shown — that is normal."
IFS= read -rs LINK; echo
LINK="$(printf '%s' "$LINK" | tr -d '[:space:]')"
case "$LINK" in
  https://*|webcal://*) ;;
  *) echo "⚠️ This is not a link (must start with https:// or webcal://). Nothing saved."; read -p "Press Enter to close"; exit 1;;
esac
echo "Link length: ${#LINK} characters."
security add-generic-password -U -s FLOKTRON_CAL -a floktron -w "$LINK" && echo "✅ Link saved (Keychain item FLOKTRON_CAL)." || echo "⚠️ Not saved."
unset LINK
cd "$(dirname "$0")/../.." && python3 scripts/calendar_read.py --check --diagnose
read -p "Press Enter to close"
