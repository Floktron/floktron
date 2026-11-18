#!/bin/sh
# FLOKTRON · automatic runs on Linux (cron).   sh scripts/install/install_linux.sh on | off
cd "$(dirname "$0")/../.." || exit 1
ROOT="$PWD"; PY=$(command -v python3) || { echo "python3 not found"; exit 1; }
"$PY" -c "import openpyxl, yaml" 2>/dev/null || "$PY" -m pip install --user -q openpyxl pyyaml
crontab -l 2>/dev/null | awk -v r="$ROOT" 'index($0, r)==0' > /tmp/floktron.cron
[ "$1" = "on" ] && "$PY" scripts/install/schedule.py linux "$ROOT" "$PY" >> /tmp/floktron.cron
crontab /tmp/floktron.cron && rm /tmp/floktron.cron
[ "$1" = "on" ] && echo "FLOKTRON automatic runs ON (crontab -l to see)" || echo "FLOKTRON automatic runs OFF"
