#!/bin/sh
# FLOKTRON · move and backup on Linux:  sh scripts/install/move_linux.sh   (docs/MOVE.md)
cd "$(dirname "$0")/../.." || exit 1
PY=$(command -v python3) || { echo "python3 not found"; exit 1; }
"$PY" -c "import openpyxl, yaml, pyzipper" 2>/dev/null || "$PY" -m pip install --user -q openpyxl pyyaml pyzipper
echo "1 pack · 2 unpack · 3 check · 4 backup now · 5 pack for a new manager (handover)"
printf "Choose 1-5: "; read ans
case "$ans" in
  1) "$PY" scripts/move.py pack ;;
  2|3) printf "Path of the archive: "; read f; [ "$ans" = 2 ] && "$PY" scripts/move.py unpack "$f" || "$PY" scripts/move.py check "$f" ;;
  4) "$PY" scripts/move.py backup ;;
  5) "$PY" scripts/move.py pack --profile handover ;;
  *) echo "Nothing done." ;;
esac
