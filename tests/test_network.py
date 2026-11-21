# -*- coding: utf-8 -*-
"""FLOKTRON network check: network and process code may live only in the files listed in docs/TRANSPARENCY.md.
(urllib.parse only builds text for links and is not network code.)"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
NET = re.compile(r"^\s*(import|from)\s+(urllib(?!\.parse)|http|socket|smtplib|imaplib|poplib|ftplib|telnetlib|requests|httpx|aiohttp|websocket|webbrowser)\b", re.M)
PROC = re.compile(r"^\s*(import|from)\s+subprocess\b", re.M)
ALLOWED_NET = {"mail/read.py", "mail/send.py", "news_slice.py", "registry_lv.py", "bot/telegram_bot.py", "tg_watch.py", "supply_watch.py", "calendar_read.py"}
ALLOWED_PROC = {"run.py", "mail/send.py", "bot/telegram_bot.py", "security_check.py"}


def _py():
    for d, _, files in os.walk(S):
        if "__pycache__" in d:
            continue
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(d, f)
                yield os.path.relpath(p, S).replace(os.sep, "/"), open(p, encoding="utf-8").read()


def test_network_only_in_known_files():
    bad = [r for r, s in _py() if NET.search(s) and r not in ALLOWED_NET]
    assert not bad, f"network code outside the allowed files: {bad}"


def test_processes_only_in_known_files():
    bad = [r for r, s in _py() if PROC.search(s) and r not in ALLOWED_PROC]
    assert not bad, f"subprocess outside the allowed files: {bad}"
