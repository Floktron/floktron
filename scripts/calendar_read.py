# -*- coding: utf-8 -*-
"""FLOKTRON · calendar_read.py — reads YOUR calendar through its private read-only link (.ics). Optional.

Works with any calendar that gives an .ics link: Proton, Google, Outlook / Microsoft 365, Apple iCloud, Nextcloud,
Fastmail and others (how to find the link: docs/CALENDAR.md). The link is a key to your calendar, so it is kept
like a password — in the environment variable or the macOS Keychain, never in config.yaml or chat.
FLOKTRON only READS: it never creates, moves or deletes your events.

config.yaml → calendar:
    enabled: true
    url_env: "FLOKTRON_CAL_URL"        # the private link comes from this environment variable...
    keychain_service: "FLOKTRON_CAL"   # ...or from the Keychain (scripts/install/calendar_link.command saves it)
    timezone: "Europe/Riga"
    rays: ["L1"]                       # morning messages of these rays show "Today in the calendar"
    busy_only: false                   # true → only "10:00–11:00 busy", no titles or places
    attach_due: true                   # morning message gets an .ics with the due dates of its tasks

Usage:
    python3 scripts/calendar_read.py --check          # can the link be read? how many events in the next 7 days
    python3 scripts/calendar_read.py --day 2026-11-20 # that day's events (shown here only, nothing is saved)
"""
import argparse
import datetime
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ics  # noqa: E402

UA = "Mozilla/5.0 (FLOKTRON calendar; read only)"


def link(cal_cfg):
    from mail.send import read_secret
    url = read_secret(cal_cfg.get("url_env") or "FLOKTRON_CAL_URL", cal_cfg.get("keychain_service") or "FLOKTRON_CAL")
    return url.strip().replace("webcal://", "https://", 1)


def masked(url):
    """The shape of the link with every secret part hidden — safe to show or send to support."""
    import urllib.parse as up
    u = up.urlsplit(url)
    segs = [x if len(x) <= 12 else x[:4] + "…(" + str(len(x)) + ")" for x in u.path.split("/")]
    q = ",".join(k for k, _ in up.parse_qsl(u.query, keep_blank_values=True))
    return (f"{u.scheme}://{u.netloc}{'/'.join(segs)}" + (f" ?[{q}]" if q else "")
            + (" #[fragment]" if u.fragment else "") + f"  length {len(url)}"
            + ("  ⚠ exactly 128 characters — probably cut off, save it again" if len(url) == 128 else ""))


def fetch(url, timeout=30):
    if not url.startswith("https://"):
        raise ValueError("the calendar link must start with https:// or webcal://")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(8_000_000).decode("utf-8", "replace")  # 8 MB is far more than any normal calendar


def agenda(cfg, day, text=None):
    """Lines for one day, or [] when the calendar is off. Raises on a broken link (caller decides)."""
    cal = (cfg or {}).get("calendar") or {}
    if not cal.get("enabled"):
        return []
    if text is None:
        url = link(cal)
        if not url:
            raise ValueError("no calendar link: set FLOKTRON_CAL_URL or the Keychain item FLOKTRON_CAL")
        text = fetch(url)
    evs = ics.events_on(ics.parse(text, cal.get("timezone") or ""), day)
    return [ics.line(e, bool(cal.get("busy_only"))) for e in evs]


def main():
    ap = argparse.ArgumentParser(description="Read your calendar (read only).")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--day", default="")
    ap.add_argument("--diagnose", action="store_true", help="show the shape of the link, secrets hidden")
    a = ap.parse_args()
    cfg = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    cal = dict(cfg.get("calendar") or {}, enabled=True)
    url = link(cal)
    if not url:
        sys.exit("No calendar link. Mac: double-click scripts/install/calendar_link.command; "
                 "other systems: environment variable FLOKTRON_CAL_URL (docs/CALENDAR.md).")
    if a.diagnose:
        print("Link shape (secrets hidden):", masked(url))
    try:
        text = fetch(url)
    except Exception as e:  # noqa: BLE001
        hint = (" — 404 means the address is wrong or cut off: copy the link again with the copy button of your "
                "calendar (not from the address bar) and save it again" if "404" in str(e) else "")
        sys.exit(f"Calendar link does not answer: {str(e)[:120]}{hint}. Link shape: {masked(url)} (docs/CALENDAR.md)")
    evs = ics.parse(text, cal.get("timezone") or "")
    if "BEGIN:VCALENDAR" not in text[:2000]:
        sys.exit("The link answered, but it is not a calendar (.ics). Copy the iCal / ICS link, not the web page.")
    if a.day:
        day = datetime.date.fromisoformat(a.day)
        for x in ics.events_on(evs, day):
            print(ics.line(x, bool(cal.get("busy_only"))))
        return
    today = datetime.date.today()
    week = sum(len(ics.events_on(evs, today + datetime.timedelta(days=i))) for i in range(7))
    print(f"OK — calendar read: {len(evs)} events in the file, {week} in the next 7 days")


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    main()
