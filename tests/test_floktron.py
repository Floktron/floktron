# -*- coding: utf-8 -*-
"""FLOKTRON automatic checks. Run:  pip install pytest openpyxl pyyaml && pytest -q
No network and no real mailbox needed: messages are built with --dry, replies are read from .eml files."""
import datetime
import os
import subprocess
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
sys.path.insert(0, S)

from calendar_days import easter, is_working, next_working  # noqa: E402
from collect_replies import answer_only, parse  # noqa: E402
from news_slice import matches, parse_feed  # noqa: E402
import route  # noqa: E402

TODAY = datetime.date.today()
D = TODAY.strftime("%Y%m%d")


def run(*args, cwd=ROOT):
    r = subprocess.run([sys.executable] + list(args), cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


@pytest.fixture
def base(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text('company: {name: "Test SIA"}\nmail: {provider: smtp, user: me@t.lv, reply_to: floktron@t.lv, '
                   'manager_address: boss@t.lv}\n', encoding="utf-8")
    out = tmp_path / "base.xlsx"
    run(os.path.join(S, "base_create.py"), "--config", str(cfg), "--out", str(out))
    wb = openpyxl.load_workbook(out)
    r = wb["Rays"]
    r.cell(2, 4, "sales@t.lv")
    r.cell(2, 9, "lead@t.lv")
    wb["Tasks"].append(["T002", TODAY.isoformat(), "L1", "Call client Alfa", "test", TODAY.isoformat(),
                        "Sent", "", "", f"{D}-L1", ""])
    wb.save(out)
    return cfg, out


def eml(folder, name, subject, body, sender="sales@t.lv"):
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"], m["Message-ID"] = sender, subject, formatdate(localtime=True), make_msgid()
    m.set_content(body)
    (folder / name).write_bytes(bytes(m))


# ---------- answers ----------
@pytest.mark.parametrize("text,expected", [
    ("Task 1: x ✍️ What was done, next step: agreed a meeting\n\nBest regards\nAnna", "agreed a meeting"),
    ("Не дозвонился\n\nЗадача 1: x\n\n✍️ Что помешало: \n\nС уважением, Янис", "Не дозвонился"),
    ("Uzdevumi šajā vēstulē: 1. x\n\n✅ Pieņemu. Ar cieņu, Jānis", ""),
    ("3 left\n--\nSent from my iPhone", "3 left"),
])
def test_answer_only(text, expected):
    assert answer_only(text) == expected


def test_parse_marker():
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"] = "a@b.lv", f"FLOKTRONBOX#{D}-L2 T:T9 - · x", formatdate()
    m.set_content("Task 1: x ✍️ What got in the way: holiday")
    assert parse(bytes(m), [], "FLOKTRON#") is None          # other FLOKTRON → ignored
    r = parse(bytes(m), [], "FLOKTRONBOX#")
    assert (r["ray"], r["task"], r["sign"], r["answer"]) == ("L2", "T9", "-", "holiday")


# ---------- calendar ----------
def test_calendar():
    assert easter(2026) == datetime.date(2026, 4, 5)
    lv = {"company": {"country": "LV"}}
    assert not is_working(datetime.date(2026, 11, 18), lv)        # Proclamation Day
    assert next_working(datetime.date(2026, 11, 17), 1, lv) == datetime.date(2026, 11, 19)
    assert next_working(datetime.date(2026, 11, 20), 1, {}) == datetime.date(2026, 11, 23)  # weekend


# ---------- full cycle ----------
def test_morning_dry_and_collect(base, tmp_path):
    cfg, out = base
    run(os.path.join(S, "send_morning.py"), "--config", str(cfg), "--base", str(out), "--dry", "--force")
    rep = tmp_path / "rep"
    rep.mkdir()
    eml(rep, "1.eml", f"FLOKTRON#{D}-L1 T:T002 + · Call", "Task 1: x ✍️ What was done, next step: order confirmed, 15 pcs")
    eml(rep, "2.eml", f"FLOKTRON#{D}-L1 T:T002 - · Call", "fake", sender="stranger@spam.com")
    outp = run(os.path.join(S, "collect_replies.py"), "--config", str(cfg), "--base", str(out),
               "--from-dir", str(rep), "--no-escalation")
    assert "unknown address" in outp
    wb = openpyxl.load_workbook(out)
    t = {r[0]: r for r in wb["Tasks"].iter_rows(min_row=2, values_only=True)}
    assert t["T002"][6] == "Done" and "order confirmed" in t["T002"][7]
    new = [r for r in t.values() if str(r[4]).startswith("Route M0")]
    assert {r[2] for r in new} == {"L2", "L7"}                     # order → stock + finance
    again = run(os.path.join(S, "collect_replies.py"), "--config", str(cfg), "--base", str(out),
                "--from-dir", str(rep), "--no-escalation")
    assert "new replies: 0" in again                               # second run changes nothing


def test_route_repeat_then_manager(base):
    _, out = base
    wb = openpyxl.load_workbook(out)
    for r in wb["Tasks"].iter_rows(min_row=2):
        if r[0].value == "T002":
            r[6].value, r[7].value = "Not done", "- busy"
    c1 = route.run(wb, cfg={})
    assert c1[0][1] == "L1"                                        # repeat
    for r in wb["Tasks"].iter_rows(min_row=2):
        if r[0].value == c1[0][0]:
            r[6].value, r[7].value = "Not done", "- still busy"
    c2 = route.run(wb, cfg={})
    assert c2[0][1] == "L0"                                        # second failure → manager


# ---------- radar ----------
def test_news_matching(tmp_path):
    assert matches("kanalizācija", "aizsērējis kanalizācijas stāvvads")
    assert matches("construction wastewater", "fine for construction site wastewater")
    assert not matches("construction wastewater", "construction news")
    feed = tmp_path / "f.xml"
    feed.write_text('<rss><channel><item><title>A</title><link>https://x/1</link>'
                    f'<pubDate>{formatdate()}</pubDate></item></channel></rss>', encoding="utf-8")
    items = parse_feed(feed.read_bytes())
    assert items[0][1:3] == ("A", "https://x/1")


def test_radar_create(tmp_path):
    out = tmp_path / "radar.xlsx"
    run(os.path.join(S, "radar_create.py"), "--config", str(tmp_path / "none.yaml"), "--out", str(out))
    wb = openpyxl.load_workbook(out)
    assert {"Keywords", "Sources", "News_feeds", "Signal_feed", "Gaps"} <= set(wb.sheetnames)


# ---------- registry ----------
def test_registry_lv(tmp_path):
    radar = tmp_path / "radar.xlsx"
    run(os.path.join(S, "radar_create.py"), "--config", str(tmp_path / "none.yaml"), "--out", str(radar))
    wb = openpyxl.load_workbook(radar)
    q = wb["Registry_queries"]
    q.cell(4, 3, "būvniecība;flīzes")
    q.append(["R07", "LV", "ūdens attīrīšana", "Competitor", "", "SIA", "Yes"])
    wb.save(radar)
    d = (TODAY - datetime.timedelta(days=3)).isoformat()
    old = (TODAY - datetime.timedelta(days=400)).isoformat()
    csvf = tmp_path / "register.csv"
    csvf.write_text(
        "regcode;sepa;name;type;type_text;registered;terminated;closed;address\n"
        f"40001;;SIA \"Ātrā būvniecības grupa\";SIA;Sabiedrība;{d};;;Rīga\n"
        f"40002;;SIA \"Flīžu meistari\";SIA;Sabiedrība;{d};;;Jelgava\n"
        f"40003;;SIA \"Kafejnīca Saule\";SIA;Sabiedrība;{d};;;Rīga\n"
        f"40004;;SIA \"Būvniecība Veca\";SIA;Sabiedrība;{old};;;Rīga\n"
        f"40005;;SIA \"Ūdens attīrīšanas tehnoloģijas\";SIA;Sabiedrība;{d};;;Ogre\n"
        f"40006;;Būvniecības biedrība;BDR;Biedrība;{d};;;Rīga\n", encoding="utf-8")
    out = run(os.path.join(S, "registry_lv.py"), "--radar", str(radar), "--csv", str(csvf), "--days", "30")
    assert "matched: 3" in out
    wb = openpyxl.load_workbook(radar)
    regs = {r[2]: r[8] for r in wb["Companies"].iter_rows(min_row=4, values_only=True) if r[2]}
    assert regs == {"40001": "Client", "40002": "Client", "40005": "Competitor"}
    assert any(r[2] == "40005" for r in wb["Players"].iter_rows(min_row=4, values_only=True))
    again = run(os.path.join(S, "registry_lv.py"), "--radar", str(radar), "--csv", str(csvf), "--days", "30")
    assert "matched: 0" in again


# ---------- content ----------
def test_content_check(tmp_path):
    c = tmp_path / "content.xlsx"
    run(os.path.join(S, "content_create.py"), "--out", str(c))
    wb = openpyxl.load_workbook(c)
    p = wb["Plan"]
    y = (TODAY - datetime.timedelta(days=2)).isoformat()
    p.append([y, "09:00", "Facebook", "lv", "Tip", "h", "text A", "", "site-1.jpg", "", "", "", "Published", "https://fb/1", ""])
    p.append([TODAY.isoformat(), "10:00", "Facebook", "lv", "Tip", "h", "text B", "", "site-1.jpg", "", "", "", "Ready", "", ""])
    p.append([TODAY.isoformat(), "10:00", "LinkedIn", "en", "Tip", "h", "text C", "", "site-1.jpg", "", "", "", "Ready", "", ""])
    p.append([y, "08:30", "TikTok", "lv", "News", "h", "text D", "", "video-2.mp4", "", "", "", "Ready", "", ""])
    wb.save(c)
    out = run(os.path.join(S, "content_check.py"), "--config", str(tmp_path / "none.yaml"), "--content", str(c))
    assert "duplicates stopped: 1" in out and "missed → today: 1" in out and "posts today" in out
    wb = openpyxl.load_workbook(c)
    rows = list(wb["Plan"].iter_rows(min_row=2, values_only=True))
    assert rows[1][12] == "Duplicate" and rows[2][12] == "Ready" and rows[3][0] == TODAY.isoformat()
    assert str(wb["Media"].cell(2, 3).value).endswith("https://fb/1")


def test_post_link_time_and_platform():
    from post_link import platform_of, time_of
    assert platform_of("https://www.linkedin.com/feed/update/urn:li:activity:7417505828044800000/") == "LinkedIn"
    assert platform_of("https://x.com/someone/status/2011740138501046272") == "X"
    assert platform_of("21.11 instagram carousel") == "Instagram"
    assert time_of("https://www.linkedin.com/feed/update/urn:li:activity:7417505828044800000/") == \
        datetime.datetime(2026, 1, 15, 10, 0)
    assert time_of("https://x.com/someone/status/2011740138501046272").strftime("%Y-%m-%d %H:%M") == "2026-01-15 10:00"
    assert time_of("https://www.facebook.com/photo/?fbid=1") is None


def test_content_links_file_scheduled_and_twice(tmp_path):
    c = tmp_path / "content.xlsx"
    out = run(os.path.join(S, "content_create.py"), "--out", str(c))
    links = tmp_path / "published_links.txt"
    assert links.exists() and "## NEW" in links.read_text(encoding="utf-8")
    y = (TODAY - datetime.timedelta(days=1)).isoformat()
    wb = openpyxl.load_workbook(c)
    p = wb["Plan"]
    p.append([y, "09:00", "LinkedIn", "en", "Inside", "Personal post", "text P", "", "pic-p.png", "", "", "", "Ready", "", ""])
    p.append([y, "10:00", "X", "en", "Inside", "Podcast", "text X", "", "", "", "", "", "Scheduled", "", ""])
    p.append([y, "11:00", "Facebook", "lv", "Tip", "Bucket", "text F", "", "", "", "", "", "Ready", "", "moved from 18.11"])
    p.append([y, "12:00", "TikTok", "lv", "Tip", "Video", "text T", "", "", "", "", "", "Ready", "", ""])
    wb.save(c)
    links.write_text(links.read_text(encoding="utf-8").replace(
        "## NEW\n", f"## NEW\nhttps://www.linkedin.com/feed/update/urn:li:share:1/ personal {TODAY - datetime.timedelta(days=1):%d.%m}\n"
        "https://vimeo.com/42\n"), encoding="utf-8")
    out = run(os.path.join(S, "content_check.py"), "--config", str(tmp_path / "none.yaml"), "--content", str(c),
              "--links", str(links))
    assert "links from file: 1" in out and "waiting for a link: 1" in out and "missed twice: 1" in out
    assert "missed → today: 2" in out and "link not matched" in out
    rows = list(openpyxl.load_workbook(c)["Plan"].iter_rows(min_row=2, values_only=True))
    assert rows[0][12] == "Published" and "linkedin" in rows[0][13]            # pasted link → Published
    assert rows[1][0] == y and "waiting for a link" in rows[1][14]             # Scheduled is not moved
    assert rows[2][0] == TODAY.isoformat() and rows[2][14].startswith("MISSED TWICE (first 18.11")
    assert rows[3][0] == TODAY.isoformat() and rows[3][14].startswith("moved from")
    txt = links.read_text(encoding="utf-8")
    new, done = txt.split("\n## DONE")
    assert "urn:li:share:1" in done and "urn:li:share:1" not in new and "vimeo.com/42" in new and "no matching post" in new


def test_gaps_report_dry(tmp_path):
    radar = tmp_path / "radar.xlsx"
    run(os.path.join(S, "radar_create.py"), "--config", str(tmp_path / "none.yaml"), "--out", str(radar))
    wb = openpyxl.load_workbook(radar)
    wb["Gaps"].append([TODAY.isoformat(), "News feed P04", "err.ee", "HTTP 403", "source blocked", "use Google News", "New"])
    wb.save(radar)
    out = run(os.path.join(S, "gaps_report.py"), "--config", str(tmp_path / "none.yaml"), "--radar", str(radar), "--dry")
    assert "[source blocked] News feed P04" in out


# ---------- written report by plain «Reply» (learned in real use: a table pasted from a spreadsheet) ----------
def test_report_table_and_lines(base, tmp_path):
    cfg, out = base
    wb = openpyxl.load_workbook(out)
    for tid, txt in (("T003", "Call client Beta"), ("T004", "Call client Gamma")):
        wb["Tasks"].append([tid, TODAY.isoformat(), "L1", txt, "test", TODAY.isoformat(), "Sent", "", "", f"{D}-L1", ""])
    wb.save(out)
    rep = tmp_path / "rep"
    rep.mkdir()
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"], m["Message-ID"] = "sales@t.lv", f"Re: FLOKTRON#{D}-L1 · Calls", formatdate(), make_msgid()
    m.set_content("see table")
    m.add_alternative("<table><tr><td>1</td><td>Mon</td><td>Client Alfa</td><td>+</td><td>meeting on Tuesday</td></tr>"
                      "<tr><td>2</td><td>Mon</td><td>Client Beta</td><td>-</td><td>left a voice message</td></tr>"
                      "<tr><td>3</td><td>Mon</td><td>Client Gamma</td><td>*</td><td>already answered by e-mail</td></tr>"
                      "</table>", subtype="html")
    (rep / "t.eml").write_bytes(bytes(m))
    outp = run(os.path.join(S, "collect_replies.py"), "--config", str(cfg), "--base", str(out),
               "--from-dir", str(rep), "--no-escalation", "--no-route")
    t = {r[0]: r for r in openpyxl.load_workbook(out)["Tasks"].iter_rows(min_row=2, values_only=True)}
    assert t["T002"][6] == "Done" and "Tuesday" in t["T002"][7], outp
    assert t["T003"][6] == "Not done" and "voice" in t["T003"][7]
    assert t["T004"][6] == "Done"


def test_report_plain_lines_and_own_message():
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"] = "a@b.lv", f"Re: FLOKTRON#{D}-L2", formatdate()
    m.set_content("1 + delivered\n2 − nobody home\n\nOn Mon someone wrote:\n> 3 + quoted")
    r = parse(bytes(m), ["me@t.lv"], "FLOKTRON#")
    assert r["code"] == "R" and r["lines"] == [("1", "+", "delivered"), ("2", "-", "nobody home")]
    m.replace_header("From", "me@t.lv")
    assert parse(bytes(m), ["me@t.lv"], "FLOKTRON#") is None          # our own morning message
    m.replace_header("From", "a@b.lv"); m.set_content("Thanks, got it")
    assert parse(bytes(m), [], "FLOKTRON#")["code"] == "OK"           # plain reply without lines = accepted
