# -*- coding: utf-8 -*-
"""FLOKTRON · ics.py — the calendar language every calendar speaks (iCalendar, .ics). No network here.

Read:   parse(text) → events; events_on(events, day, tz) → that day's events (repeating events expanded:
        DAILY / WEEKLY with BYDAY / MONTHLY / YEARLY, INTERVAL, COUNT, UNTIL, EXDATE).
Write:  make_calendar([event(...), ...]) → .ics text that Proton, Google, Outlook, Apple and others open with one tap.

Command line (makes a file, sends nothing):
    python3 scripts/ics.py --title "Meeting" --start "2026-11-20 10:00" --end "2026-11-20 12:00" \\
        --location "Office" --out data/meeting.ics
    python3 scripts/ics.py --title "Report due" --date 2026-11-25 --out data/due.ics     # all-day
"""
import argparse
import datetime
import hashlib
import re

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

DAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
MAX_REPEAT = 20000  # safety: never expand a repeating event more than this (≈ 55 years of a daily event)


def zone(name):
    if not name or ZoneInfo is None:
        return None
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 — unknown or Windows-only zone name → treat as local time
        return None


# ---------- read ----------
def unfold(text):
    """Long lines in .ics continue on the next line that starts with a space or tab."""
    return re.sub(r"\r?\n[ \t]", "", text.replace("\r\n", "\n"))


def unescape(v):
    return v.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def parse_dt(value, params, tz):
    """→ (datetime aware in tz, or date for all-day, all_day flag)."""
    value = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        return datetime.date(int(value[:4]), int(value[4:6]), int(value[6:8])), True
    d = datetime.datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    if value.endswith("Z"):
        d = d.replace(tzinfo=datetime.timezone.utc)
    else:
        src = zone(params.get("TZID")) or tz
        d = d.replace(tzinfo=src) if src else d
    if tz and d.tzinfo:
        d = d.astimezone(tz)
    return d, False


def parse(text, tz_name=""):
    """Events from .ics text. Each: dict(start, end, all_day, title, location, rrule, exdates, uid)."""
    tz = zone(tz_name)
    events, cur = [], None
    for line in unfold(text).split("\n"):
        if line == "BEGIN:VEVENT":
            cur = {"exdates": set(), "rrule": None, "title": "", "location": "", "end": None, "uid": ""}
        elif line == "END:VEVENT" and cur is not None:
            if cur.get("start") is not None and cur.get("status") != "CANCELLED":
                if cur["end"] is None:
                    cur["end"] = cur["start"] + (datetime.timedelta(days=1) if cur["all_day"] else datetime.timedelta(0))
                events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, value = line.split(":", 1)
            name, *ps = head.split(";")
            params = dict(p.split("=", 1) for p in ps if "=" in p)
            name = name.upper()
            try:
                if name == "DTSTART":
                    cur["start"], cur["all_day"] = parse_dt(value, params, tz)
                elif name == "DTEND":
                    cur["end"], _ = parse_dt(value, params, tz)
                elif name == "SUMMARY":
                    cur["title"] = unescape(value)
                elif name == "LOCATION":
                    cur["location"] = unescape(value)
                elif name == "UID":
                    cur["uid"] = value
                elif name == "STATUS":
                    cur["status"] = value.upper()
                elif name == "RRULE":
                    cur["rrule"] = dict(p.split("=", 1) for p in value.split(";") if "=" in p)
                elif name == "EXDATE":
                    for v in value.split(","):
                        d, _ = parse_dt(v, params, tz)
                        cur["exdates"].add(d if isinstance(d, datetime.date) and not isinstance(d, datetime.datetime) else d.date())
            except (ValueError, IndexError):
                continue  # a broken line is skipped, not fatal
    return events


def _day(d):
    return d if not isinstance(d, datetime.datetime) else d.date()


def _add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    try:
        return d.replace(year=y, month=m)
    except ValueError:  # 31st in a short month — skipped, like calendars do
        return None


def occurs_on(ev, day):
    """True if the event (or one of its repeats) touches `day`."""
    first = _day(ev["start"])
    length = max((_day(ev["end"]) - first).days - (1 if ev["all_day"] else 0), 0)
    rr = ev.get("rrule")
    if not rr:
        return first <= day <= first + datetime.timedelta(days=length)
    if day < first or day in ev["exdates"]:
        return False
    freq = rr.get("FREQ", "").upper()
    step = max(int(rr.get("INTERVAL", "1") or 1), 1)
    count = int(rr["COUNT"]) if rr.get("COUNT", "").isdigit() else None
    until = None
    if rr.get("UNTIL"):
        until = datetime.date(int(rr["UNTIL"][:4]), int(rr["UNTIL"][4:6]), int(rr["UNTIL"][6:8]))
    bydays = [DAYS[x[-2:]] for x in rr.get("BYDAY", "").split(",") if x[-2:] in DAYS] if freq == "WEEKLY" else []
    if freq == "WEEKLY" and not bydays:
        bydays = [first.weekday()]
    n, k, d = 0, 0, first
    while k < MAX_REPEAT:
        k += 1
        if freq == "DAILY":
            cand = [first + datetime.timedelta(days=(k - 1) * step)]
        elif freq == "WEEKLY":
            week0 = first - datetime.timedelta(days=first.weekday()) + datetime.timedelta(weeks=(k - 1) * step)
            cand = [week0 + datetime.timedelta(days=b) for b in sorted(bydays)]
        elif freq == "MONTHLY":
            cand = [_add_months(first, (k - 1) * step)]
        elif freq == "YEARLY":
            cand = [_add_months(first, (k - 1) * step * 12)]
        else:
            return first <= day <= first + datetime.timedelta(days=length)
        for d in cand:
            if d is None or d < first:
                continue
            if until and d > until:
                return False
            n += 1
            if count is not None and n > count:
                return False
            if d not in ev["exdates"] and d <= day <= d + datetime.timedelta(days=length):
                return True
        if d is not None and d > day:
            return False
    return False


def events_on(events, day):
    out = [e for e in events if occurs_on(e, day)]
    return sorted(out, key=lambda e: (not e["all_day"], e["start"].time() if not e["all_day"] else datetime.time(0)))


def line(ev, busy_only=False):
    """'10:00–12:00 Title (Place)' or 'all day Title'. busy_only → no title or place, only 'busy'."""
    when = "all day" if ev["all_day"] else f"{ev['start']:%H:%M}–{ev['end']:%H:%M}" if isinstance(ev["end"], datetime.datetime) else f"{ev['start']:%H:%M}"
    if busy_only:
        return f"{when} busy"
    place = f" ({ev['location']})" if ev.get("location") else ""
    return f"{when} {ev['title']}{place}".strip()


# ---------- write ----------
def esc(v):
    return str(v or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def fold(s):
    """Lines longer than 75 bytes continue on the next line with a leading space."""
    out, b = [], s.encode("utf-8")
    while len(b) > 75:
        cut = 75
        while cut and (b[cut] & 0xC0) == 0x80:  # never cut inside a UTF-8 character
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b" " + b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n".join(out)


def event(title, start, end=None, location="", description="", uid="", alarm_minutes=None):
    """start/end: datetime (aware or local) or date (all-day). Returns VEVENT lines."""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uid = uid or hashlib.sha1(f"{title}|{start}|{location}".encode("utf-8")).hexdigest()[:20] + "@floktron"
    if isinstance(start, datetime.datetime):
        end = end or start + datetime.timedelta(hours=1)
        fmt = lambda d: (d.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
                         if d.tzinfo else d.strftime("%Y%m%dT%H%M%S"))
        when = [f"DTSTART:{fmt(start)}", f"DTEND:{fmt(end)}"]
    else:
        end = end or start + datetime.timedelta(days=1)
        when = [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{end:%Y%m%d}"]
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}"] + when + [f"SUMMARY:{esc(title)}"]
    if location:
        lines.append(f"LOCATION:{esc(location)}")
    if description:
        lines.append(f"DESCRIPTION:{esc(description)}")
    if alarm_minutes is not None:
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc(title)}",
                  f"TRIGGER:-PT{int(alarm_minutes)}M", "END:VALARM"]
    return lines + ["END:VEVENT"]


def make_calendar(events, name="FLOKTRON"):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//FLOKTRON//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             f"X-WR-CALNAME:{esc(name)}"]
    for e in events:
        lines += e
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(x) for x in lines) + "\r\n"


def main():
    ap = argparse.ArgumentParser(description="Make an .ics file (one event) that any calendar opens.")
    ap.add_argument("--title", required=True)
    ap.add_argument("--start", help='"YYYY-MM-DD HH:MM" (local time)')
    ap.add_argument("--end", help='"YYYY-MM-DD HH:MM"')
    ap.add_argument("--date", help="YYYY-MM-DD — all-day event")
    ap.add_argument("--location", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--alarm", type=int, default=None, help="reminder, minutes before")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.date:
        ev = event(a.title, datetime.date.fromisoformat(a.date), location=a.location, description=a.description,
                   alarm_minutes=a.alarm)
    elif a.start:
        p = lambda s: datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")  # noqa: E731
        ev = event(a.title, p(a.start), p(a.end) if a.end else None, a.location, a.description, alarm_minutes=a.alarm)
    else:
        ap.error("give --date (all day) or --start")
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        f.write(make_calendar([ev]))
    print("OK:", a.out)


if __name__ == "__main__":
    main()
