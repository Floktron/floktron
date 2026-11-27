# -*- coding: utf-8 -*-
"""Online meeting links (TEST · FICTIONAL): only official addresses pass, trick links become a warning, the time
comes from the invitation / «today at» / the letter, cancelled meetings disappear, the dashboard shows the full link.
All companies, people and meeting numbers are made up. No network: a fake mailbox and calendar text."""
import datetime
import json
import os
import sys
from email.message import EmailMessage
from email.utils import format_datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import dashboard as db  # noqa: E402
import meeting_links as ml  # noqa: E402

RIGA = ZoneInfo("Europe/Riga")
NOW = datetime.datetime(2026, 11, 27, 16, 30, tzinfo=RIGA)
CFG = {"company": {"language": "en"}, "calendar": {"timezone": "Europe/Riga"}, "meetings": {"enabled": True}}
Z = "https://us06web.zoom.us/j/81234567890?pwd=TESTfictional1"
TM = "https://teams.microsoft.com/meet/3999000111222?p=TESTfictionalP"
TM2 = "https://teams.microsoft.com/meet/3999000555666?p=TESTfictionalQ"
TL = "https://teams.microsoft.com/l/meetup-join/19%3ameeting_TESTFICTIONAL%40thread.v2/0?context=%7b%22Tid%22%3a%22test%22%7d"
GM = "https://meet.google.com/tst-fict-onl"


def test_official_addresses_pass():
    assert ml.check(Z) == ("Zoom", Z)
    assert ml.check(TM) == ("Microsoft Teams", TM)
    assert ml.check(TL) == ("Microsoft Teams", TL)
    assert ml.check(GM) == ("Google Meet", GM)
    assert ml.check("https://testfictional.webex.com/meet/paraugs")[0] == "Webex"
    assert ml.check("https://teams.cloud.microsoft/meet/3999000111222?p=x")[0] == "Microsoft Teams"
    assert ml.check("http://zoom.us/j/81234567890") == ("Zoom", "https://zoom.us/j/81234567890")


def test_wrappers_are_unwrapped_only_to_official():
    assert ml.check("https://www.google.com/url?q=https://rtucloud0.zoom.us/j/90000000001&sa=D&usg=TEST") == ("Zoom", "https://rtucloud0.zoom.us/j/90000000001")
    assert ml.check("https://eur01.safelinks.protection.outlook.com/?url=https%3A%2F%2Fmeet.google.com%2Ftst-fict-onl&data=TEST") == ("Google Meet", GM)
    assert ml.check("https://www.google.com/url?q=https://evil-test.example/zoom.us/j/1") is None


def test_look_alikes_and_non_meeting_links_refused():
    for bad in ("https://zoom.us.evil-test.example/j/81234567890", "https://evilzoom.us/j/81234567890",
                "https://zoom.us@evil-test.example/j/81234567890", "https://zoom.us:8443/j/81234567890",
                "https://xn--zom-test.us/j/1", "javascript:alert(1)//zoom.us/j/1", "https://zoom.us/signin",
                "https://meet.google.com/", "ftp://zoom.us/j/81234567890", "https://teams.microsoft.com/l/app/xyz"):
        assert ml.check(bad) is None, bad


def test_trick_link_becomes_warning():
    htm = f'<p>Join: <a href="https://evil-test.example/login">{Z}</a></p><p><a href="{GM}">Join</a></p>'
    links, warns = ml.find("", htm)
    assert all(x["svc"] != "Zoom" for x in links)
    assert warns and warns[0]["svc"] == "Zoom" and warns[0]["real"] == "evil-test.example"
    assert {"svc": "Google Meet", "url": GM} in links


def test_teams_short_link_and_extras():
    assert ml.find(f"Join here {TL}\nor {TM}")[0] == [dict(svc="Microsoft Teams", url=TM)]
    assert ml.extras("Meeting ID: 399 900 011 122 2\nPasscode: TsT9xY") == dict(mid="399 900 011 122 2", code="TsT9xY")


def vev(uid, start, title, extra="", end=None, rrule=""):
    return (f"BEGIN:VEVENT\nUID:{uid}\nDTSTART;TZID=Europe/Riga:{start}\n" + (f"DTEND;TZID=Europe/Riga:{end}\n" if end else "")
            + f"SUMMARY:{title}\n{extra}" + (f"RRULE:{rrule}\n" if rrule else "") + "END:VEVENT\n")


CAL = ("BEGIN:VCALENDAR\nVERSION:2.0\n"
       + vev("t1@test", "20261127T170000", "TEST Paraugs Būve — site meeting", f"LOCATION:{Z}\n", "20261127T180000")
       + vev("t2@test", "20261201T100000", "TEST Muster Bau GmbH — Abstimmung",
             f"X-MICROSOFT-SKYPETEAMSMEETINGURL:{TL}\nDESCRIPTION:Microsoft Teams meeting\\nJoin: {TM}\\nMeeting ID: 399 900 011 122 2\\nPasscode: TsT9xY\n", "20261201T110000")
       + vev("t3@test", "20261124T090000", "TEST weekly planning", f"DESCRIPTION:Google Meet: {GM}\n", "20261124T093000", "FREQ=WEEKLY;BYDAY=TU")
       + vev("t4@test", "20261126T090000", "TEST yesterday", f"LOCATION:{Z}\n")
       + vev("t5@test", "20261203T120000", "TEST Demo SIA — in person", "LOCATION:Riga\\, Test street 1\n")
       + vev("t6@test", "20261204T150000", "TEST join the meeting", "LOCATION:https://zoom.us.evil-test.example/j/81234567890\n")
       + vev("t7@test", "20261202T160000", "TEST seminar for suppliers (online)", "LOCATION:online\n", "20261202T180000")
       + "END:VCALENDAR\n")


def test_calendar_events():
    ev = ml.ics_meetings(CAL, NOW.date(), "Europe/Riga")
    by = {e["uid"]: e for e in ev}
    assert by["t1@test"]["links"][0]["url"] == Z
    assert by["t2@test"]["links"] == [dict(svc="Microsoft Teams", url=TM)] and by["t2@test"]["extra"]["code"] == "TsT9xY"
    assert [e["day"] for e in ev if e["uid"] == "t3@test"] == ["2026-12-01", "2026-12-08"]
    assert "t4@test" not in by and by["t6@test"]["links"] == []


def mail(subj, frm, body="", htm="", cal="", date=NOW - datetime.timedelta(hours=3), bulk=False):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Date"] = frm, "test@example.invalid", subj, format_datetime(date)
    m["Message-ID"] = f"<{abs(hash(subj))}@test.invalid>"
    if bulk:
        m["List-Unsubscribe"] = "<mailto:unsub@test.invalid>"
    m.set_content(body or "TEST")
    if htm:
        m.add_alternative(htm, subtype="html")
    if cal:
        m.add_attachment(cal.encode(), maintype="text", subtype="calendar", filename="invite.ics")
    return m.as_bytes()


INV = "BEGIN:VCALENDAR\nMETHOD:REQUEST\n" + vev("inv1@test", "20261202T140000", "TEST Paraugs Logistics — delivery plan", f"DESCRIPTION:Join Zoom Meeting\\n{Z}\n", "20261202T150000") + "END:VCALENDAR\n"
INV9 = "BEGIN:VCALENDAR\nMETHOD:REQUEST\n" + vev("inv9@test", "20261205T100000", "TEST cancelled meeting", f"LOCATION:{GM}\n") + "END:VCALENDAR\n"
MAILS = [
    mail("Invitation: TEST Paraugs Logistics — delivery plan", "TEST Anna Paraugs <anna@paraugs-logistics.test>", f"Join Zoom Meeting\n{Z}\nMeeting ID: 812 3456 7890\nPasscode: TsT123", cal=INV),
    mail("TEST: See you today at 5 PM for Session 3", "TEST Incubator <info@incubator.test>", "See you today at 5 PM (EET) on Zoom.\nJoin: https://www.google.com/url?q=https://rtucloud0.zoom.us/j/90000000001&sa=D"),
    mail("TEST news: webinar", "TEST News <news@news.test>", "Webinar Zoom: https://zoom.us/j/80000000002", bulk=True),
    mail("TEST urgent: join the meeting", "TEST Unknown <x@evil-test.example>", "Meeting", htm=f'<a href="https://evil-test.example/l">{TM}</a>'),
    mail("TEST Muster Bau GmbH — Abstimmung (Teams)", "TEST Max Muster <max@musterbau.test>", f"Join: {TM}", date=NOW - datetime.timedelta(days=2)),
    mail("TEST cancelled meeting", "TEST Demo <demo@demo.test>", "", cal=INV9, date=NOW - datetime.timedelta(days=3)),
    mail("Cancelled: TEST cancelled meeting", "TEST Demo <demo@demo.test>", "", cal=INV9.replace("METHOD:REQUEST", "METHOD:CANCEL"), date=NOW - datetime.timedelta(days=1)),
    mail("TEST invoice", "TEST Bookkeeper <b@paraugs.test>", "Invoice attached, no links."),
    mail("Confirmation: TEST supplier webinar", "TEST Ministry <info@ministry.test>",
         f"The webinar will be on 2 December 2026 at 16:00 online.\nJoin: {TM2}", date=NOW - datetime.timedelta(days=5)),
]


def test_letters():
    p1 = ml.parse_mail(MAILS[0], NOW.date(), "Europe/Riga")
    assert p1["meets"][0]["start"].startswith("2026-12-02T14:00") and p1["extra"] == dict(mid="812 3456 7890", code="TsT123")
    p2 = ml.parse_mail(MAILS[1], NOW.date(), "Europe/Riga")
    assert (p2["when"] or "").startswith("2026-11-27T17:00")
    assert p2["links"] == [dict(svc="Zoom", url="https://rtucloud0.zoom.us/j/90000000001")]
    p4 = ml.parse_mail(MAILS[3], NOW.date(), "Europe/Riga")
    assert not p4["links"] and p4["warns"]
    assert "02:12" not in ml.parse_mail(MAILS[8], NOW.date())["times"]


def msgs():
    import email as _e
    return [dict(mid=_e.message_from_bytes(m)["Message-ID"], raw=m) for m in MAILS]


def test_run_builds_one_line_per_meeting(tmp_path):
    items = ml.run(CFG, str(tmp_path), NOW, messages=msgs(), texts_=[("calendar", CAL)], log=lambda s: None)
    data = json.load(open(tmp_path / "meetings.json", encoding="utf-8"))
    assert data["items"] == items
    ti = {i["title"]: i for i in items}
    assert ti["TEST Paraugs Būve — site meeting"]["url"] == Z and items[0]["start"].startswith("2026-11-27T17:00")
    assert ti["TEST Paraugs Logistics — delivery plan"]["extra"]["code"] == "TsT123"
    assert ti["TEST: See you today at 5 PM for Session 3"]["start"].startswith("2026-11-27T17:00")
    assert "TEST news: webinar" not in ti and "TEST cancelled meeting" not in ti and "TEST invoice" not in ti
    assert ti["TEST urgent: join the meeting"]["warn"] and not ti["TEST urgent: join the meeting"]["url"]
    assert sum(1 for i in items if i["url"] == TM) == 1 and ti["TEST Muster Bau GmbH — Abstimmung"]["src"] == "calendar"
    assert ti["TEST seminar for suppliers (online)"]["url"] == TM2           # the letter names its date and time
    assert "TEST Demo SIA — in person" not in ti


def test_letter_body_read_once(tmp_path):
    ml.run(CFG, str(tmp_path), NOW, messages=msgs(), texts_=[], log=lambda s: None)
    st = json.load(open(tmp_path / "meetings_state.json", encoding="utf-8"))
    no_raw = [dict(mid=m["mid"], raw=None) for m in msgs()]                 # known letters come without a body
    items = ml.run(CFG, str(tmp_path), NOW, messages=no_raw, texts_=[], log=lambda s: None)
    assert st["mail"] and any(i["url"] == Z for i in items)


def test_dashboard_shows_full_link_and_attention(tmp_path):
    ml.run(CFG, str(tmp_path), NOW, messages=msgs(), texts_=[("calendar", CAL)], log=lambda s: None)
    M = ml.collect(CFG, str(tmp_path), NOW, "en")
    assert any(a.get("link") == Z and "17:00" in a["text"] for a in M["attention"])
    assert any(a["lvl"] == "bad" and "evil-test.example" in a["text"] for a in M["attention"])
    D = db.collect(CFG, str(tmp_path), NOW.replace(tzinfo=None))
    assert D["attention"][0].get("link") or D["attention"][0]["lvl"] == "bad"
    h = db.render(D)
    assert f'href="{Z}"' in h and f">{Z}</a>" in h
    assert 'rel="noopener noreferrer"' in h and 'referrerpolicy="no-referrer"' in h
    assert "evil-test.example/l" not in h and "do not open it" in h
    assert "ID 399 900 011 122 2 · passcode TsT9xY" in h


def test_changed_file_shows_nothing(tmp_path):
    json.dump({"items": [dict(title="TEST broken", day="2026-11-28", start="2026-11-28T10:00:00+02:00", url="javascript:alert(1)", svc="Zoom")]},
              open(tmp_path / "meetings.json", "w"))
    M = ml.collect(CFG, str(tmp_path), NOW, "en")
    assert M["items"] == [] and M["attention"] == []
    assert db.meet_link("javascript:alert(1)") == "" and db.meet_link("https://zoom.us.evil-test.example/j/1") == ""


def test_off_by_default(tmp_path):
    D = db.collect({"company": {"language": "en"}}, str(tmp_path), NOW.replace(tzinfo=None))
    assert D["meetings"] is None and 'id="meetings"' not in db.render(D)
