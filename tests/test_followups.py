# -*- coding: utf-8 -*-
"""Reminders after an offer (scripts/followups.py): offline checks on FICTIONAL data.
Mail is a folder of .eml files, outgoing mail goes to an outbox folder — nothing is sent, no network."""
import datetime as dt
import email
import os
import sys
from email import policy
from email.message import EmailMessage

import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import followups as fu  # noqa: E402

CFG = {"company": {"name": "Demo SIA (FICTIONAL)"},
       "mail": {"user": "office@demo-sia.example.com", "manager_address": "boss@demo-sia.example.com",
                "marker": "FLOKTRON#"},
       "documents": {"email": "office@demo-sia.example.com", "phone": "+371 20000000"},
       "followups": {"days": [3, 7, 14], "hours": "08-20"}}
OWN, BOSS = "office@demo-sia.example.com", "boss@demo-sia.example.com"
OFFERS = [("DEMO-P-2026-001", "lv", "iepirkumi@klusa-buve.example.com", ""),
          ("DEMO-P-2026-002", "en", "buyer@muster-bau.example.com", ""),
          ("DEMO-P-2026-003", "lv", "info@neizsutits.example.com", "")]


@pytest.fixture
def world(tmp_path):
    base = tmp_path / "base.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Issued"
    ws.append(["Number", "Type", "Date", "Due", "Buyer", "Buyer reg. no.", "Net", "VAT", "Total", "Currency",
               "Status", "Reference", "File", "Created", "TEST", "Language", "E-mail"])
    for nr, lang, mail, status in OFFERS:
        ws.append([nr, "offer", "2026-11-23", "2026-12-31", f"TEST {nr} (FICTIONAL)", "", 100, 21, 121, "EUR",
                   status or "To be sent", "", f"TEST_2026-11-23_{nr}.pdf", "2026-11-23 09:00", "TEST", lang, mail])
    wb.save(base)
    box = tmp_path / "mail"
    box.mkdir()
    return dict(base=str(base), box=box, out=tmp_path / "out")


def eml(world, name, frm, to, subject, when, body="", files=(), headers=None):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = frm, to, subject
    m["Date"] = email.utils.format_datetime(dt.datetime.strptime(when, "%Y-%m-%d %H:%M").astimezone())
    m["Message-ID"] = f"<{name}@test.example.com>"
    for k, v in (headers or {}).items():
        m[k] = v
    m.set_content(body or "text")
    for f in files:
        m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename=f)
    (world["box"] / f"{name}.eml").write_bytes(bytes(m))


def go(world, now):
    mails = list(fu.mail_from_folder(str(world["box"])))
    return fu.run(CFG, world["base"], mails, dt.datetime.strptime(now, "%Y-%m-%d %H:%M"),
                  outbox=str(world["out"]), test=True)


def sheet(world):
    ws = openpyxl.load_workbook(world["base"])[fu.SHEET]
    head = [c.value for c in ws[1]]
    return {r[0]: dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True)}


def outbox(world, part):
    if not world["out"].exists():
        return []
    return sorted(p for p in world["out"].iterdir() if part in p.name)


def send_offers(world):
    eml(world, "o1", OWN, OFFERS[0][2], "Komercpiedāvājums DEMO-P-2026-001", "2026-11-23 10:15")
    eml(world, "o2", OWN, OFFERS[1][2], "Our offer", "2026-11-24 09:40", files=["TEST_2026-11-23_DEMO-P-2026-002.pdf"])


def test_nothing_before_day_3_and_not_sent_offer_is_ignored(world):
    send_offers(world)
    n = go(world, "2026-11-25 12:00")
    assert n["proposed"] == 0 and n["offers"] == 3
    go(world, "2026-11-26 11:00")
    rows = sheet(world)
    assert "FU-DEMO-P-2026-001-D3" in rows and not any("DEMO-P-2026-003" in k for k in rows)


def test_approval_mail_has_three_buttons_and_nothing_goes_to_buyer(world):
    send_offers(world)
    go(world, "2026-11-26 11:00")
    req = outbox(world, "FU-DEMO-P-2026-001-D3_approve")
    assert len(req) == 1 and not outbox(world, "_to_buyer")
    m = email.message_from_bytes(req[0].read_bytes(), policy=policy.default)
    assert m["To"] == BOSS
    h = m.get_body(("html",)).get_content()
    for act in ("OK", "EDIT", "NO"):
        assert f"FLOKTRON%23FU-DEMO-P-2026-001-D3%20{act}" in h
    assert "Labdien" in sheet(world)["FU-DEMO-P-2026-001-D3"]["Text"]


def test_ok_sends_reply_in_same_thread_in_working_hours(world):
    send_offers(world)
    go(world, "2026-11-26 11:00")
    eml(world, "a1", BOSS, OWN, "FLOKTRON#FU-DEMO-P-2026-001-D3 OK", "2026-11-26 11:05")
    go(world, "2026-11-26 12:00")
    sent = outbox(world, "FU-DEMO-P-2026-001-D3_to_buyer")
    assert len(sent) == 1
    m = email.message_from_bytes(sent[0].read_bytes(), policy=policy.default)
    assert m["To"] == OFFERS[0][2] and m["In-Reply-To"] == "<o1@test.example.com>"
    assert m["Subject"].startswith("Re: Komercpiedāvājums DEMO-P-2026-001")
    assert sheet(world)["FU-DEMO-P-2026-001-D3"]["Status"] == "Sent"


def test_edit_sends_own_text_and_stranger_cannot_approve(world):
    send_offers(world)
    go(world, "2026-11-27 10:00")
    eml(world, "x", "someone@else.example.org", OWN, "FLOKTRON#FU-DEMO-P-2026-002-D3 OK", "2026-11-27 10:10")
    go(world, "2026-11-27 11:00")
    assert sheet(world)["FU-DEMO-P-2026-002-D3"]["Status"] == "Waiting for OK"
    eml(world, "a2", BOSS, OWN, "FLOKTRON#FU-DEMO-P-2026-002-D3 EDIT", "2026-11-27 11:10",
        body="Hello, may I call you on Friday about the offer?\n\nBest regards\n\n- - - - -\nold text")
    go(world, "2026-11-27 12:00")
    m = email.message_from_bytes(outbox(world, "DEMO-P-2026-002-D3_to_buyer")[0].read_bytes(), policy=policy.default)
    assert "call you on Friday" in m.get_content() and "old text" not in m.get_content()


def test_answer_from_same_company_stops_auto_reply_does_not(world):
    send_offers(world)
    eml(world, "auto", OFFERS[1][2], OWN, "Automatic reply: Our offer", "2026-11-24 09:41")
    eml(world, "ans", "petra@klusa-buve.example.com", OWN, "Re: Komercpiedāvājums", "2026-11-25 09:30")
    go(world, "2026-11-27 10:00")
    rows = sheet(world)
    assert rows["FU-DEMO-P-2026-001-D0"]["Status"].startswith("Buyer answered 25.11")
    assert "FU-DEMO-P-2026-001-D3" not in rows
    assert rows["FU-DEMO-P-2026-002-D3"]["Status"] == "Waiting for OK"


def test_weekend_waits_for_monday_and_no_stops_the_offer(world):
    eml(world, "o1", OWN, OFFERS[0][2], "Komercpiedāvājums DEMO-P-2026-001", "2026-11-25 14:00")
    go(world, "2026-11-28 15:00")                       # Saturday
    assert not outbox(world, "_approve")
    go(world, "2026-11-30 08:00")                       # Monday
    assert sheet(world)["FU-DEMO-P-2026-001-D3"]["Proposed"].startswith("2026-11-30")
    eml(world, "no", BOSS, OWN, "FLOKTRON#FU-DEMO-P-2026-001-D3 NO", "2026-11-30 09:00")
    for now in ("2026-11-30 10:00", "2026-12-03 10:00", "2026-12-10 10:00"):
        go(world, now)
    rows = sheet(world)
    assert rows["FU-DEMO-P-2026-001-D3"]["Status"] == "Not needed" and "FU-DEMO-P-2026-001-D7" not in rows


def test_unapproved_step_becomes_outdated_and_closed_status_stops(world):
    send_offers(world)
    go(world, "2026-11-26 11:00")
    go(world, "2026-11-30 11:00")
    rows = sheet(world)
    assert rows["FU-DEMO-P-2026-001-D3"]["Status"] == "Outdated"
    assert rows["FU-DEMO-P-2026-001-D7"]["Status"] == "Waiting for OK"
    wb = openpyxl.load_workbook(world["base"])
    wb["Issued"]["K2"] = "Declined"
    wb.save(world["base"])
    go(world, "2026-12-07 11:00")
    rows = sheet(world)
    assert rows["FU-DEMO-P-2026-001-D7"]["Status"] == "Stopped: status Declined"
    assert "FU-DEMO-P-2026-001-D14" not in rows


def test_dry_run_writes_nothing(world):
    send_offers(world)
    before = os.path.getmtime(world["base"])
    mails = list(fu.mail_from_folder(str(world["box"])))
    n = fu.run(CFG, world["base"], mails, dt.datetime(2026, 11, 26, 11, 0), outbox=str(world["out"]), dry=True,
               test=True, log=lambda *_: None)
    assert n["proposed"] == 1 and os.path.getmtime(world["base"]) == before and not world["out"].exists()


def test_texts_are_short_and_polite():
    off = {"Number": "DEMO-P-2026-001", "Date": "2026-11-23", "Due": "2026-12-31"}
    for lang in ("lv", "en"):
        for day in (3, 7, 14):
            t = fu.draft(off, day, lang, "Demo SIA", dt.datetime(2026, 11, 26))
            assert "DEMO-P-2026-001" in t and len(t.split()) < 80
