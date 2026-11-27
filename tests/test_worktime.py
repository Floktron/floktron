# -*- coding: utf-8 -*-
"""Work time (TEST · FICTIONAL): marks → shifts and hours, location check, no invented hours, manager fixes,
reminders, the bot's buttons, the dashboard block and the month table. No network."""
import datetime
import json
import os
import subprocess
import sys

import openpyxl
import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bot"))

import dashboard as db  # noqa: E402
import telegram_bot as tb  # noqa: E402
import worktime as wt  # noqa: E402

SITE = {"name": "Site A (TEST)", "lat": 56.95, "lon": 24.10, "radius_m": 250}
CFG = {"company": {"language": "en"}, "worktime": {"enabled": True, "geo": True, "sites": [SITE], "people": {"1": "Anna (TEST)", "2": "Ivo (TEST)"},
                                                     "holidays": ["2026-11-18"]}}
T = datetime.datetime


def put(path, who, ev, ts, **x):
    wt.add(str(path), who, CFG["worktime"]["people"].get(who, who), ev, ts, **x)


def test_plain_day_with_pause(tmp_path):
    p = tmp_path / "w.jsonl"
    put(p, "1", "start", "2026-11-26 08:00")
    put(p, "1", "pause", "2026-11-26 12:00")
    put(p, "1", "back", "2026-11-26 12:30")
    put(p, "1", "end", "2026-11-26 17:30")
    r = wt.days(wt.read(str(p)), T(2026, 11, 27, 10))[0]
    assert (r["worked"], r["pause"], r["over"], r["state"]) == (540, 30, 60, "done")


def test_night_shift_is_one_shift_with_night_minutes(tmp_path):
    p = tmp_path / "w.jsonl"
    put(p, "2", "start", "2026-11-26 22:00")
    put(p, "2", "end", "2026-11-27 06:30")
    rows = wt.days(wt.read(str(p)), T(2026, 11, 27, 10))
    assert len(rows) == 1 and rows[0]["date"] == "2026-11-26"
    assert rows[0]["worked"] == 510 and rows[0]["night"] == 480


def test_no_end_mark_is_never_counted(tmp_path):
    p = tmp_path / "w.jsonl"
    put(p, "1", "start", "2026-11-25 08:00")
    put(p, "1", "start", "2026-11-26 08:00")       # forgot to end yesterday, started again
    put(p, "1", "end", "2026-11-26 16:00")
    rows = wt.days(wt.read(str(p)), T(2026, 11, 27, 10))
    assert rows[0]["state"] == "noend" and rows[0]["worked"] == 0 and ("noend", {}) in rows[0]["flags"]
    assert rows[1]["worked"] == 480


def test_open_today_counts_until_now_and_old_open_does_not(tmp_path):
    p = tmp_path / "w.jsonl"
    put(p, "1", "start", "2026-11-27 08:00")
    r = wt.days(wt.read(str(p)), T(2026, 11, 27, 10, 30))[0]
    assert r["state"] == "work" and r["worked"] == 150
    r = wt.days(wt.read(str(p)), T(2026, 11, 28, 9, 0))[0]     # 25 h later: no end mark
    assert r["state"] == "noend" and r["worked"] == 0


def test_manager_fix_sets_the_end_and_is_shown(tmp_path):
    p = tmp_path / "w.jsonl"
    put(p, "1", "start", "2026-11-25 08:00")
    wt.add(str(p), "1", "Anna (TEST)", "fix", "2026-11-26 09:00", by="manager", date="2026-11-25", end="16:30", why="forgot (TEST)")
    r = wt.days(wt.read(str(p)), T(2026, 11, 27))[0]
    assert r["state"] == "done" and r["worked"] == 510 and r["flags"][0][0] == "fix"
    lines = open(p, encoding="utf-8").read().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["ev"] == "start"   # append-only: the original mark is kept


def test_location_inside_and_far(tmp_path):
    p = str(tmp_path / "w.jsonl")
    now = T(2026, 11, 27, 8, 0)
    txt, st = wt.mark(CFG, p, "1", "Anna (TEST)", "start", now, {"latitude": 56.9501, "longitude": 24.1001}, "en")
    assert st == "work" and "Site A (TEST) ✓" in txt
    txt, _ = wt.mark(CFG, p, "2", "Ivo (TEST)", "start", now, {"latitude": 56.955, "longitude": 24.10}, "en")
    assert "555 m from Site A (TEST)" in txt
    flags = [f for r in wt.days(wt.read(p), now) for f in r["flags"]]
    assert ("far", {"dist": 555, "site": "Site A (TEST)"}) in flags
    rec = json.loads(open(p, encoding="utf-8").readline())
    assert set(rec) <= {"ts", "who", "name", "ev", "by", "lat", "lon", "site", "dist", "inside", "acc"}   # nothing more is kept


def test_buttons_state_machine(tmp_path):
    p = str(tmp_path / "w.jsonl")
    t = T(2026, 11, 27, 8, 0)
    assert "No start mark" in wt.mark(CFG, p, "1", "A", "end", t)[0]
    wt.mark(CFG, p, "1", "A", "start", t)
    assert "Already at work since 08:00" in wt.mark(CFG, p, "1", "A", "start", t)[0]
    assert wt.mark(CFG, p, "1", "A", "pause", t.replace(hour=12))[1] == "pause"
    assert wt.mark(CFG, p, "1", "A", "pause", t.replace(hour=12, minute=30))[1] == "work"   # Pause twice = Back
    txt, st = wt.mark(CFG, p, "1", "A", "end", t.replace(hour=16, minute=30))
    assert st == "done" and "8 h 00 min" in txt
    assert wt.which_button("▶ Начал работу") == "start" and wt.which_button("⏹ Beidzu") == "end" and wt.which_button("hi") == ""


def test_reminder_once_per_day(tmp_path):
    p = str(tmp_path / "w.jsonl")
    put(p, "1", "start", "2026-11-27 08:00")
    assert wt.due_reminders(CFG, p, T(2026, 11, 27, 19, 0)) == []
    due = wt.due_reminders(CFG, p, T(2026, 11, 27, 20, 1))
    assert len(due) == 1 and due[0][0] == "1" and "Still at work" in due[0][1]
    assert wt.due_reminders(CFG, p, T(2026, 11, 27, 21, 0)) == []


def test_weekend_holiday_and_month_xlsx(tmp_path):
    p = tmp_path / "worktime.jsonl"
    put(p, "1", "start", "2026-11-18 08:00")     # holiday from config
    put(p, "1", "end", "2026-11-18 12:00")
    put(p, "1", "start", "2026-11-21 08:00")     # Saturday
    put(p, "1", "end", "2026-11-21 10:00")
    out = tmp_path / "m.xlsx"
    assert wt.month_xlsx(CFG, str(out), "2026-11", str(tmp_path), T(2026, 11, 27)) == 2
    ws = openpyxl.load_workbook(out)["Month"]
    assert [c.value for c in ws[2]][:6] == ["Anna (TEST)", 2, 6, 0, 0, 6]


def test_dashboard_block_and_attention(tmp_path):
    put(tmp_path / "worktime.jsonl", "1", "start", datetime.datetime.now().strftime("%Y-%m-%d 00:01"))
    put(tmp_path / "worktime.jsonl", "2", "start", "2026-01-05 08:00")     # long ago, no end
    cfg = dict(CFG, company={"language": "ru", "name": "TEST · FICTIONAL"})
    D = db.collect(cfg, str(tmp_path))
    assert D["worktime"]["now"] == 1 and D["worktime"]["team"] == 2
    page = db.render(D)
    assert "Учёт рабочего времени" in page and "Anna (TEST)" in page and "сейчас на работе" in page


def test_dashboard_without_worktime_has_no_block(tmp_path):
    D = db.collect({}, str(tmp_path))
    assert D["worktime"] is None and "⏱" not in db.render(D)


class FakeApi:
    def __init__(self):
        self.sent = []

    def call(self, method, **p):
        self.sent.append((method, p))
        return {"message_id": len(self.sent)}


@pytest.fixture
def bot(tmp_path):
    flow = yaml.safe_load(open(os.path.join(ROOT, "config", "bot_flow.example.yaml"), encoding="utf-8"))
    api = FakeApi()
    cfg = {"manager_chat_ids": [999], "_worktime": CFG["worktime"], "_company": {"language": "ru"}}
    return tb.Bot(api, flow, cfg, tb.Store(data_dir=str(tmp_path))), api, tmp_path


def msg(chat, text="", **extra):
    m = {"chat": {"id": chat, "type": "private"}, "from": {"username": "tester"}, "text": text}
    m.update(extra)
    return {"update_id": 1, "message": m}


def test_bot_start_with_location_pause_end(bot):
    b, api, tmp = bot
    b.handle(msg(1, "/start"))
    kb = api.sent[-1][1]["reply_markup"]["keyboard"]
    assert kb[0][0]["request_location"] is True and kb[0][0]["text"] == "▶ Начал работу"
    b.handle(msg(1, "", location={"latitude": 56.9501, "longitude": 24.1001}))
    assert "Начало работы" in api.sent[-1][1]["text"] and "Site A (TEST) ✓" in api.sent[-1][1]["text"]
    b.handle(msg(1, "⏸ Пауза"))
    assert api.sent[-1][1]["reply_markup"]["keyboard"][1][0]["text"] == "▶ Продолжил"
    b.handle(msg(1, "⏹ Закончил"))
    assert "День закончен" in api.sent[-1][1]["text"]
    evs = [json.loads(x)["ev"] for x in open(tmp / "worktime.jsonl", encoding="utf-8")]
    assert evs == ["start", "pause", "back", "end"]


def test_bot_ignores_forwarded_location_and_strangers(bot):
    b, api, tmp = bot
    b.handle(msg(1, "", location={"latitude": 1, "longitude": 1}, forward_date=1))
    assert "Пересланное место" in api.sent[-1][1]["text"]
    b.handle(msg(555, "▶ Начал работу"))          # not in the team → the client dialog, no mark
    assert not os.path.exists(tmp / "worktime.jsonl")


def test_bot_reminder_buttons_and_who(bot):
    b, api, tmp = bot
    b.handle(msg(1, "▶ Начал работу"))
    b.handle({"update_id": 3, "callback_query": {"id": "q", "data": "wt:end", "from": {},
                                                 "message": {"chat": {"id": 1}, "message_id": 7, "text": "⏰ Ты ещё на работе?"}}})
    assert any(m == "editMessageText" and "День закончен" in p["text"] for m, p in api.sent)
    b.handle(msg(999, "/who"))
    assert "Сейчас на работе никого" in api.sent[-1][1]["text"]


def test_cli_fix_and_month(tmp_path):
    cfgp = tmp_path / "config.yaml"
    yaml.safe_dump(CFG, open(cfgp, "w", encoding="utf-8"), allow_unicode=True)
    put(tmp_path / "worktime.jsonl", "1", "start", "2026-11-25 08:00")
    run = lambda *a: subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "worktime.py"), *a, "--config", str(cfgp),  # noqa: E731
                                     "--data", str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert run("fix", "--who", "Anna (TEST)", "--date", "2026-11-25").returncode != 0      # a reason is required
    r = run("fix", "--who", "Anna (TEST)", "--date", "2026-11-25", "--end", "16:00", "--why", "forgot (TEST)")
    assert r.returncode == 0, r.stderr
    r = run("month", "--month", "2026-11")
    assert r.returncode == 0 and (tmp_path / "worktime_2026-11.xlsx").exists()


def test_mark_without_telegram_is_shown_with_its_channel(tmp_path):
    cfgp = tmp_path / "config.yaml"
    yaml.safe_dump(CFG, open(cfgp, "w", encoding="utf-8"), allow_unicode=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "worktime.py"), "mark", "--who", "Anna (TEST)", "--action", "start",
                        "--by", "dashboard", "--config", str(cfgp), "--data", str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "Work started" in r.stdout
    rows = wt.days(wt.read(str(tmp_path / "worktime.jsonl")))
    assert rows[0]["who"] == "1" and ("via", {"via": "dashboard"}) in rows[0]["flags"]
