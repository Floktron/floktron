# -*- coding: utf-8 -*-
"""FLOKTRON · utf8_console.py — every script prints arrows, ✅ and Latvian letters.

A Windows console, a pipe to an AI assistant or the Task Scheduler log often uses an old code page (cp1252 …),
and Python then stops with UnicodeEncodeError in the middle of a run. Each script imports this module when it
starts (only when run as a script), so its output is UTF-8 everywhere; a sign that still cannot be shown
becomes "?" instead of a crash. Nothing else changes.
"""
import sys


def fix():
    for s in (sys.stdout, sys.stderr):
        enc = (getattr(s, "encoding", "") or "").lower().replace("-", "").replace("_", "")
        if enc == "utf8":
            continue
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


fix()
