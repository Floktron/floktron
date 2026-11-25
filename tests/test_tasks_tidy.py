# -*- coding: utf-8 -*-
"""Tasks tidy (scripts/tasks_tidy.py) and the friendly content letter — TEST · FICTIONAL, no network."""
import datetime
import os
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import content_check as cc  # noqa: E402
import tasks_tidy as tt  # noqa: E402

D = datetime.date(2026, 11, 25)
CFG = {"mail": {"user": "office@demo-sia.example.com", "manager_address": "boss@demo-sia.example.com"}}


def base():
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    r = wb.create_sheet("Rays")
    r.append(["ID", "Ray", "Responsible", "E-mail / messenger", "Language", "Send at", "Active", "Comment", "Team lead e-mail"])
    r.append(["L0", "Manager", "Demo Boss", "boss@demo-sia.example.com", "en", "07:40", "yes", "TEST · FICTIONAL", ""])
    r.append(["L1", "Sales", "TEST · Sales", "sales.test@demo-sia.example.com", "en", "07:40", "yes", "TEST · FICTIONAL", ""])
    t = wb.create_sheet("Tasks")
    t.append(["Task ID", "Date", "Ray", "Task", "Source / rule", "Due", "Status", "Report (from evening reply)", "Updated", "Letter", "Route"])
    for row in [
        ["A1", "2026-11-19", "L0", "Call SIA «Fiktīvs Būvnieks DEMO» about the meeting 20.11", "log", "2026-11-19", "Question"],
        ["A2", "2026-11-20", "L0", "Meeting DEMO Partner: training block", "log", "2026-11-20", "Question"],
        ["A3", "2026-11-11", "L0", "Answer after the call: info@fiktivs-demo.example.com — interest in the course", "route", "2026-11-11", "Question"],
        ["A4", "2026-11-13", "L0", "Decide: not done twice (L1) — TEST: count the stock", "route M9 → escalation", "2026-11-13", "Question"],
        ["A5", "2026-11-23", "L0", "Decide: offer for SIA «Nekad Nebijis DEMO»", "manual", "2026-11-23", "Sent"],
        ["A6", "2026-11-01", "L0", "Decide: old thing without events", "manual", "2026-11-01", "Sent"],
        ["A7", "2026-11-24", "L1", "TEST: answer a client", "test", "2026-11-24", "Not done"],
    ]:
        t.append(row + [None, None, None, None])
    m = wb.create_sheet("Mail")
    m.append(["Date", "Direction", "From / To", "Address", "Organisation", "Subject"])
    m.append(["2026-11-21 09:00", "→ sent", "office", "info@fiktivs-demo.example.com", "", "Thank you"])
    m.append(["2026-11-24 10:00", "→ sent", "office", "sales.test@demo-sia.example.com", "", "Fw: Nekad Nebijis"])   # own ray: no event
    wb.create_sheet("Run_log")
    return wb


def test_tidy_events_tests_and_archive():
    wb = base()
    tt.shown_col(wb["Tasks"])
    wb["Tasks"].cell(7, 12, "4 · 2026-11-15")   # A6 was shown 4 times (day 14 done) → archive
    res = tt.run(wb, CFG, D)
    st = {r[0]: (r[6], str(r[7] or "")) for r in wb["Tasks"].iter_rows(min_row=2, values_only=True)}
    assert st["A1"][0] == "Done" and "meeting 20.11" in st["A1"][1]
    assert st["A2"][0] == "Done" and "its day passed" in st["A2"][1]
    assert st["A3"][0] == "Done" and "a message went 21.11" in st["A3"][1]
    assert st["A4"][0] == "Cancelled" and "test" in st["A4"][1]
    assert st["A5"][0] == "Sent"                      # a mail to the own ray is not an event
    assert st["A6"][0] == "Archive"
    assert st["A7"][0] == "Not done"                  # not the manager's ray: untouched
    assert wb["Tasks"].cell(1, 12).value == "Shown" and len(res["done"]) == 3


def test_rhythm_first_day_then_3_7_14():
    start = datetime.date(2026, 11, 2)
    shown, days = "", []
    for k in range(25):
        day = start + datetime.timedelta(days=k)
        if tt.should_show(start, "Sent", shown, day):
            days.append(k)
            shown = tt.mark_shown(shown, day)
    assert days == [0, 3, 7, 14]
    assert tt.should_show(start, "Sent", "2 · 2026-11-05", datetime.date(2026, 11, 5))   # resent the same day: yes
    assert not tt.should_show(start, "Done", "", start)


def test_manager_ray_from_config_or_manager_address():
    wb = base()
    assert tt.tidy_rays(CFG, wb) == {"L0"}
    assert tt.tidy_rays({"tasks_tidy": {"rays": ["L5"]}}, wb) == {"L5"}


def test_engage_only_posts_that_are_on_and_yesterday_extra():
    def post(d, t, plat, st, hook, link=""):
        v = [None] * 15
        v[cc.DATE], v[cc.TIME], v[cc.PLAT], v[cc.ST], v[cc.HOOK], v[cc.LINK], v[cc.RUB] = d, t, plat, st, hook, link, "Tips"
        return v
    rows = [post("2026-11-25", "09:00", "Facebook", "Scheduled", "Clean water on site. More text."),
            post("2026-11-25", "12:00", "LinkedIn", "Ready", "Not confirmed yet"),
            post("2026-11-24", "18:00", "Instagram", "Published", "A spontaneous post!", "https://example.com/p/1"),
            post("2026-11-24", "09:00", "Facebook", "Published", "Told yesterday")]
    told = {"2026-11-24": [cc.post_key(rows[3])]}
    on, extra = cc.engage_posts(rows, D, told)
    assert [v[cc.PLAT] for v in on] == ["Facebook"] and [v[cc.PLAT] for v in extra] == ["Instagram"]
    subj, body = cc.engage_letter("Anna", "ru", on, extra)
    assert body.startswith("Привет, Anna! 👋") and "09:00 · Facebook · Tips — «Clean water on site.»" in body
    assert "Вчера ещё вышло:" in body and "→ https://example.com/p/1" in body
    assert not any(w in body.lower() for w in ("срок", "задача", "deadline", "must"))
    assert cc.engage_posts([rows[1]], D, {}) == ([], [])   # nothing really on → no letter
