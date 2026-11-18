#!/bin/zsh
# FLOKTRON · switch on automatic runs on a Mac (double-click). Switch off: run again and answer "off".
# Times come from config/config.yaml → schedule. The Mac must be on (sleep is OK if "wake" is set in Energy settings).
cd "$(dirname "$0")/../.." || exit 1
ROOT="$PWD"; LA="$HOME/Library/LaunchAgents"; U=$(id -u)
PY=$(command -v python3); [[ -z "$PY" ]] && { echo "python3 not found — install it from python.org"; read; exit 1; }
"$PY" -c "import openpyxl, yaml" 2>/dev/null || "$PY" -m pip install --user -q openpyxl pyyaml
ID=$("$PY" -c "import hashlib,sys;print(hashlib.md5(sys.argv[1].encode()).hexdigest()[:6])" "$ROOT")
for f in "$LA"/floktron.$ID.*.plist(N); do launchctl bootout gui/$U "$f" 2>/dev/null; rm -f "$f"; done
echo "FLOKTRON in: $ROOT"
echo -n "Type 'on' to switch automatic runs on, 'off' to switch them off: "; read ans
[[ "$ans" != "on" ]] && { echo "FLOKTRON automatic runs are OFF."; read -k 1; exit 0; }
mkdir -p "$LA"
"$PY" "$ROOT/scripts/install/schedule.py" mac "$ROOT" "$PY" "$ID" "$LA" || { read; exit 1; }
for f in "$LA"/floktron.$ID.*.plist(N); do launchctl bootstrap gui/$U "$f" && echo "on: $(basename $f .plist)"; done
echo; echo "Done. Log: $ROOT/data/run.log  ·  Mac must stay on. Press any key."; read -k 1
