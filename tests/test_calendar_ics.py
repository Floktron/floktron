# -*- coding: utf-8 -*-
"""Calendar (.ics): reading the shapes real calendars send, repeating events, writing files; offline."""
import datetime
import os
import subprocess
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
sys.path.insert(0, S)
import calendar_read  # noqa: E402
import ics  # noqa: E402

CAL = "\r\n".join([
    "BEGIN:VCALENDAR", "VERSION:2.0",
    # Google style: UTC time, folded long title, escaped comma
    "BEGIN:VEVENT", "UID:a1", "DTSTART:20261120T080000Z", "DTEND:20261120T100000Z",
    "SUMMARY:Meeting with the supplier\\, warehouse tour and a very long title that is folded by the",
    "  calendar server", "LOCATION:Latgales iela", "END:VEVENT",
    # Outlook / Proton style: local time with TZID
    "BEGIN:VEVENT", "UID:a2", "DTSTART;TZID=Europe/Riga:20261120T140000", "DTEND;TZID=Europe/Riga:20261120T150000",
    "SUMMARY:Call", "END:VEVENT",
    # all-day
    "BEGIN:VEVENT", "UID:a3", "DTSTART;VALUE=DATE:20261120", "DTEND;VALUE=DATE:20261121", "SUMMARY:Fair", "END:VEVENT",
    # weekly on Mon and Thu, one Thursday cancelled by EXDATE, until end of year
    "BEGIN:VEVENT", "UID:a4", "DTSTART;TZID=Europe/Riga:20261102T090000", "DTEND;TZID=Europe/Riga:20261102T093000",
    "RRULE:FREQ=WEEKLY;BYDAY=MO,TH;UNTIL=20261231T235959Z", "EXDATE;TZID=Europe/Riga:20261126T090000",
    "SUMMARY:Team stand-up", "END:VEVENT",
    # daily, 3 times only
    "BEGIN:VEVENT", "UID:a5", "DTSTART:20261118T060000Z", "DTEND:20261118T061500Z", "RRULE:FREQ=DAILY;COUNT=3",
    "SUMMARY:Check stock", "END:VEVENT",
    # cancelled
    "BEGIN:VEVENT", "UID:a6", "DTSTART:20261120T120000Z", "STATUS:CANCELLED", "SUMMARY:Gone", "END:VEVENT",
    "END:VCALENDAR", ""])


def day(s):
    return datetime.date.fromisoformat(s)


def titles(d):
    return [e["title"] for e in ics.events_on(ics.parse(CAL, "Europe/Riga"), day(d))]


def test_one_day_all_kinds():
    t = titles("2026-11-20")
    assert t[0] == "Fair"                               # all-day first
    assert "Meeting with the supplier, warehouse tour and a very long title that is folded by the calendar server" in t
    assert "Call" in t and "Check stock" in t and "Gone" not in t
    assert "Team stand-up" not in t                     # Friday


def test_times_in_local_zone():
    evs = ics.events_on(ics.parse(CAL, "Europe/Riga"), day("2026-11-20"))
    meet = [e for e in evs if e["uid"] == "a1"][0]
    assert ics.line(meet) == "10:00–12:00 Meeting with the supplier, warehouse tour and a very long title that is folded by the calendar server (Latgales iela)"
    assert ics.line(meet, busy_only=True) == "10:00–12:00 busy"


def test_repeats_exdate_until_count():
    assert "Team stand-up" in titles("2026-11-23")      # Monday
    assert "Team stand-up" in titles("2026-11-19")      # Thursday
    assert "Team stand-up" not in titles("2026-11-26")  # Thursday cancelled
    assert "Team stand-up" not in titles("2027-01-04")  # after UNTIL
    assert "Check stock" in titles("2026-11-18") and "Check stock" in titles("2026-11-20")
    assert "Check stock" not in titles("2026-11-21")    # COUNT=3


def test_write_then_read_back():
    txt = ics.make_calendar([ics.event("Report due, final", day("2026-11-25"), alarm_minutes=60),
                             ics.event("Meeting", datetime.datetime(2026, 11, 20, 10, 0), location="Office; 2nd floor")])
    assert txt.startswith("BEGIN:VCALENDAR\r\n") and all(len(x.encode()) <= 75 for x in txt.split("\r\n"))
    back = ics.parse(txt)
    assert [e["title"] for e in back] == ["Report due, final", "Meeting"]
    assert back[0]["all_day"] and back[1]["location"] == "Office; 2nd floor"


def test_agenda_off_and_on():
    assert calendar_read.agenda({}, day("2026-11-20"), CAL) == []
    cfg = {"calendar": {"enabled": True, "timezone": "Europe/Riga", "busy_only": True}}
    lines = calendar_read.agenda(cfg, day("2026-11-20"), CAL)
    assert lines[0] == "all day busy" and all("busy" in x for x in lines)


def test_calendar_cli_makes_file(tmp_path):
    out = tmp_path / "m.ics"
    subprocess.run([sys.executable, os.path.join(S, "ics.py"), "--title", "Visit", "--start", "2026-11-20 10:00",
                    "--end", "2026-11-20 12:00", "--out", str(out)], check=True)
    assert "SUMMARY:Visit" in out.read_text(encoding="utf-8")


def test_morning_letter_survives_broken_calendar_and_attaches_due_dates(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text('company: {name: "Test SIA"}\nmail: {provider: smtp, user: me@t.lv, reply_to: f@t.lv}\n'
                   'calendar: {enabled: true, url_env: "FLOKTRON_NO_SUCH_VAR", keychain_service: "", rays: ["L1"]}\n',
                   encoding="utf-8")
    base = tmp_path / "base.xlsx"
    subprocess.run([sys.executable, os.path.join(S, "base_create.py"), "--config", str(cfg), "--out", str(base)], check=True)
    wb = openpyxl.load_workbook(base)
    wb["Rays"].cell(2, 4, "sales@t.lv")
    today = datetime.date.today().isoformat()
    wb["Tasks"].append(["T009", today, "L1", "Send the offer", "test", today, "New", "", "", "", ""])
    wb.save(base)
    env = dict(os.environ)
    env.pop("FLOKTRON_NO_SUCH_VAR", None)
    r = subprocess.run([sys.executable, os.path.join(S, "send_morning.py"), "--config", str(cfg), "--base", str(base),
                        "--dry", "--force"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "calendar: not read" in r.stdout and "L1: built" in r.stdout
    folder = os.path.join(ROOT, "data", "letters", today)
    made = [f for f in os.listdir(folder) if f.endswith("-L1.ics")]
    assert made and "SUMMARY:Send the offer" in open(os.path.join(folder, made[0]), encoding="utf-8").read()


def test_masked_link_hides_secrets():
    m = calendar_read.masked("https://calendar.example/api/v1/url/SECRETSECRETSECRET/calendar.ics?CacheKey=K1&PassphraseKey=K2")
    assert "SECRETSECRET" not in m and "K1" not in m and "K2" not in m
    assert m.startswith("https://calendar.example/api/v1/url/SECR…(18)/calendar.ics ?[CacheKey,PassphraseKey]")
    assert "cut off" in calendar_read.masked("https://x.example/" + "a" * 110)
