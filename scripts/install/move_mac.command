#!/bin/zsh
# FLOKTRON · move and backup on a Mac (double-click). One archive with the whole setup, password-protected (docs/MOVE.md).
cd "$(dirname "$0")/../.." || exit 1
ROOT="$PWD"
PY=$(command -v python3); [[ -z "$PY" ]] && { echo "python3 not found — install it from python.org"; read; exit 1; }
"$PY" -c "import openpyxl, yaml, pyzipper" 2>/dev/null || "$PY" -m pip install --user -q openpyxl pyyaml pyzipper
echo "FLOKTRON in: $ROOT"
echo "  1  Pack everything for a move (to another computer or AI assistant)"
echo "  2  Unpack a move archive here"
echo "  3  Check an archive"
echo "  4  Backup now"
echo "  5  Pack for a new manager (handover: without people's contacts)"
echo -n "Choose 1-5: "; read ans
pick() {   # newest archive in this folder or Downloads, or the file dragged into this window
  local f=$(ls -t "$ROOT"/FLOKTRON_*.zip "$ROOT"/data/move/out/FLOKTRON_*.zip "$HOME"/Downloads/FLOKTRON_*.zip 2>/dev/null | head -1)
  [[ -n "$f" ]] && { echo -n "Archive: $f — Enter to use it, or drag another file here: "; read g; [[ -n "$g" ]] && f="${g//\'/}"; } \
               || { echo -n "Drag the archive file into this window and press Enter: "; read f; f="${f//\'/}"; }
  echo "${f%% }"
}
case "$ans" in
  1) "$PY" scripts/move.py pack; open data/move/out 2>/dev/null ;;
  2) f=$(pick); "$PY" scripts/move.py unpack "$f" && open data/move/AFTER_MOVE.md ;;
  3) f=$(pick); "$PY" scripts/move.py check "$f" ;;
  4) "$PY" scripts/move.py backup ;;
  5) "$PY" scripts/move.py pack --profile handover; open data/move/out 2>/dev/null ;;
  *) echo "Nothing done." ;;
esac
echo; echo "Press any key."; read -k 1
