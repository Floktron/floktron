# -*- coding: utf-8 -*-
"""Telegram bot checks — no network: a fake API records what the bot would send."""
import os
import sys

import openpyxl
import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bot"))

import telegram_bot as tb  # noqa: E402

FLOW = os.path.join(ROOT, "config", "bot_flow.example.yaml")


class FakeApi:
    def __init__(self):
        self.sent = []

    def call(self, method, **p):
        self.sent.append((method, p))
        return {"message_id": len(self.sent)}

    def texts(self, chat):
        return [p["text"] for m, p in self.sent if m == "sendMessage" and p["chat_id"] == chat]


@pytest.fixture
def bot(tmp_path):
    flow = yaml.safe_load(open(FLOW, encoding="utf-8"))
    api = FakeApi()
    b = tb.Bot(api, flow, {"manager_chat_ids": [999], "strangers": "dialog"}, tb.Store(data_dir=str(tmp_path)))
    return b, api, tmp_path


def msg(chat, text="", **extra):
    m = {"chat": {"id": chat, "type": "private"}, "from": {"username": "tester"}, "text": text}
    m.update(extra)
    return {"update_id": 1, "message": m}


def tap(bot, chat, idx):
    sess = bot.store.state["sessions"][str(chat)]
    bot.handle({"update_id": 2, "callback_query": {"id": "q", "message": {"chat": {"id": chat}},
                                                   "data": f"s:{sess['step']}:{idx}", "from": {}}})


def test_example_flow_is_valid():
    assert tb.check_flow(yaml.safe_load(open(FLOW, encoding="utf-8"))) == []


def test_flow_check_finds_problems():
    bad = {"start": "a", "steps": {"a": {"text": "x", "buttons": [{"label": "go", "next": "nowhere"}]}}}
    probs = " ".join(tb.check_flow(bad))
    assert "nowhere" in probs and "final" in probs


def test_full_company_lead_with_source(bot):
    b, api, tmp = bot
    b.handle(msg(1, "/start qr_bucket"))
    tap(b, 1, 0)                     # quote
    tap(b, 1, 0)                     # company
    b.handle(msg(1, "Test SIA"))
    b.handle(msg(1, "Anna"))
    b.handle(msg(1, "", contact={"phone_number": "+447700900000"}))
    b.handle(msg(1, "anna@test.lv"))
    wb = openpyxl.load_workbook(tmp / "floktron_leads.xlsx")
    head = [c.value for c in wb["Leads"][1]]
    row = dict(zip(head, [c.value for c in wb["Leads"][2]]))
    assert row["Source"] == "qr_bucket" and row["Company"] == "Test SIA" and row["Phone"] == "+447700900000"
    assert row["Stage"] == "New" and "interest: quote" in row["Answers"]
    assert any("Test SIA" in t for t in api.texts(999))        # manager told
    assert "Thank you, Anna!" in api.texts(1)[-1]


def test_bad_email_asks_again_and_skip_works(bot):
    b, api, tmp = bot
    b.handle(msg(2, "/start"))
    tap(b, 2, 1)                     # question → name
    b.handle(msg(2, "Jānis"))
    b.handle(msg(2, "+44 7700 900001"))
    b.handle(msg(2, "not-an-email"))
    assert b.store.state["sessions"]["2"]["step"] == "email"
    b.handle(msg(2, "-"))
    assert b.store.state["sessions"]["2"].get("done")


def test_old_button_and_bad_source_ignored(bot):
    b, api, tmp = bot
    b.handle(msg(3, "/start <script>"))
    assert b.store.state["sessions"]["3"]["source"] == ""
    b.handle({"update_id": 5, "callback_query": {"id": "q", "message": {"chat": {"id": 3}},
                                                 "data": "s:done:0", "from": {}}})
    assert b.store.state["sessions"]["3"]["step"] == "interest"


def test_formula_text_stays_text(bot):
    b, api, tmp = bot
    b.handle(msg(4, "/start"))
    tap(b, 4, 1)
    b.handle(msg(4, '=HYPERLINK("http://bad","x")'))
    b.handle(msg(4, "+447700900002"))
    b.handle(msg(4, "-"))
    wb = openpyxl.load_workbook(tmp / "floktron_leads.xlsx")
    assert str(wb["Leads"]["H2"].value).startswith("'=")


def test_forget_and_groups_ignored(bot):
    b, api, tmp = bot
    b.handle(msg(5, "/start"))
    tap(b, 5, 1)
    b.handle(msg(5, "Pēteris"))
    b.handle(msg(5, "+447700900003"))
    b.handle(msg(5, "-"))
    b.handle(msg(5, "/forget"))
    wb = openpyxl.load_workbook(tmp / "floktron_leads.xlsx")
    assert wb["Leads"]["G2"].value == "Deleted" and not wb["Leads"]["H2"].value
    n = len(api.sent)
    b.handle({"update_id": 9, "message": {"chat": {"id": -100, "type": "group"}, "text": "/start"}})
    assert len(api.sent) == n


def test_manager_commands_only_for_manager(bot):
    b, api, tmp = bot
    b.handle(msg(6, "/leads"))       # not a manager → treated as normal chat (starts dialog)
    assert "Hello!" in api.texts(6)[-1]
    b.handle(msg(999, "/funnel"))
    assert "Reached each step" in api.texts(999)[-1]


def test_telegram_channel_preview_parsed():
    from news_slice import matches, parse_tg_preview
    page = ('<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message" '
            'data-post="newschan/4521"><div class="tgme_widget_message_text js-message_text" dir="auto">'
            'Kanalizācijas <b>avārija</b> Rīgā<br/>remontdarbi turpinās &amp; ūdens nav</div>'
            '<time datetime="2026-11-18T17:05:00+00:00" class="time">19:05</time></div></div>'
            '<div class="tgme_widget_message_wrap"><div data-post="newschan/4522"><time datetime="2026-11-18T18:00:00+00:00"></time></div></div>')
    items = parse_tg_preview(page.encode())
    assert len(items) == 1                      # the photo post without text is skipped
    d, title, link, summ = items[0]
    assert link == "https://t.me/newschan/4521" and d.year == 2026
    assert "avārija Rīgā remontdarbi" in title and "&" in summ
    assert matches("kanalizācija", title)


def test_forwarded_channel_post_adds_channel(tmp_path):
    flow = yaml.safe_load(open(FLOW, encoding="utf-8"))
    api = FakeApi()
    chf = tmp_path / "channels.txt"
    b = tb.Bot(api, flow, {"manager_chat_ids": [999], "channels_file": str(chf)}, tb.Store(data_dir=str(tmp_path)))
    fwd = {"forward_origin": {"type": "channel", "chat": {"username": "news_test", "title": "News"}}}
    b.handle(msg(999, "", **fwd))
    assert "news_test" in chf.read_text() and "added" in api.texts(999)[-1]
    b.handle(msg(999, "", **fwd))
    assert "already" in api.texts(999)[-1]
    b.handle(msg(5, "", **fwd))                 # not a manager → nothing added, dialog starts
    assert chf.read_text().count("news_test") == 1


def test_tg_watch_keywords_from_text(tmp_path):
    import tg_watch
    (tmp_path / "k.txt").write_text("kanalizācij\n# comment\nGrout-Click®\n", encoding="utf-8")
    kws = tg_watch.keywords({"keywords_file": "k.txt"}, str(tmp_path))
    assert kws == ["kanalizācij", "Grout-Click"]
    (tmp_path / "c.txt").write_text("@lsm_test  # LSM\nbad name!\n", encoding="utf-8")
    assert tg_watch.channels(str(tmp_path / "c.txt")) == ["lsm_test"]
