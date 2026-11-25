# -*- coding: utf-8 -*-
"""FLOKTRON · post_link.py — what a post link tells without opening it: platform and publishing time.

Feeds often show only "1d" or "11h". Some platforms keep the exact time inside the post ID:
- LinkedIn  …/feed/update/urn:li:activity:<ID>   → time = ID >> 22 (milliseconds, UTC)
- X         …/status/<ID>                         → time = (ID >> 22) + 1288834974657 (milliseconds, UTC)
Other platforms: platform only, time unknown (None).

Usage:
    python3 scripts/post_link.py <link> [<link> …]
"""
import datetime
import re
import sys

DOMAINS = [("facebook.com", "Facebook"), ("fb.com", "Facebook"), ("fb.watch", "Facebook"),
           ("instagram.com", "Instagram"), ("linkedin.com", "LinkedIn"), ("lnkd.in", "LinkedIn"),
           ("tiktok.com", "TikTok"), ("youtube.com", "YouTube"), ("youtu.be", "YouTube"),
           ("x.com", "X"), ("twitter.com", "X"), ("t.me", "Telegram"), ("whatsapp.com", "WhatsApp")]
X_EPOCH_MS = 1288834974657
URL = re.compile(r"https?://\S+")


def first_url(text):
    m = URL.search(text or "")
    return m.group(0).rstrip(").,;»\"'") if m else None


def platform_of(url_or_text):
    """Platform name from a link; for plain text, from a platform word in it."""
    s = (url_or_text or "").lower()
    host = re.sub(r"^https?://", "", s).split("/")[0]
    for dom, name in DOMAINS:
        if host == dom or host.endswith("." + dom):
            return name
    for _, name in DOMAINS:
        if re.search(r"\b" + re.escape(name.lower()) + r"\b", s):
            return name
    return None


def _utc(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).replace(tzinfo=None)


def time_of(url):
    """Publishing time (UTC, naive datetime) when the link carries it, else None."""
    u = url or ""
    m = re.search(r"urn:li:(?:activity|share|ugcPost):(\d{15,20})", u) or re.search(r"activity-(\d{15,20})", u)
    if m and "linkedin" in u:
        return _utc(int(m.group(1)) >> 22)
    m = re.search(r"(?:x|twitter)\.com/[^/]+/status/(\d{15,20})", u)
    if m:
        return _utc((int(m.group(1)) >> 22) + X_EPOCH_MS)
    return None


def date_in_text(text, year):
    """A dd.mm or yyyy-mm-dd date written next to the link, if any."""
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text or "")
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\b", re.sub(URL, " ", text or ""))
    if m:
        try:
            return datetime.date(year, int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    for arg in sys.argv[1:]:
        t = time_of(arg)
        print(f"{platform_of(arg) or '?'}\t{t:%Y-%m-%d %H:%M} UTC" if t else f"{platform_of(arg) or '?'}\ttime not in link")
