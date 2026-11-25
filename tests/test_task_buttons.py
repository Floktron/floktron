# -*- coding: utf-8 -*-
"""Telegram «yes / no»: the team is never a client, one task = one message with ✅ / ⛔, a press is written down,
a text reply closes the task (scripts/bot/telegram_bot.py, scripts/task_notice.py). TEST · FICTIONAL, no network."""
import json
import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bot"))
import task_notice as tn  # noqa: E402
import telegram_bot as tb  # noqa: E402


class FakeApi:
    def __init__(self):
        self.calls = []

    def call(self, m, **p):
        self.calls.append((m, p))
        return {"message_id": 900 + len(self.calls)}

    def last(self, *methods):
        return [p for m, p in self.calls if m in methods][-1]


@pytest.fixture
def bot(tmp_path):
    flow = yaml.safe_load(open(os.path.join(ROOT, "config", "bot_flow.example.yaml"), encoding="utf-8"))
    api = FakeApi()
    b = tb.Bot(api, flow, {"manager_chat_ids": [111], "team_chat_ids": [222]}, tb.Store(data_dir=str(tmp_path)))
    return b, api, tmp_path


def msg(chat, text, **kw):
    m = {"chat": {"id": chat, "type": "private"}, "from": {"username": "demo_test"}, "text": text}
    m.update(kw)
    return {"message": m}


def actions(tmp):
    p = tmp / "task_actions.jsonl"
    return [json.loads(x) for x in open(p, encoding="utf-8")] if p.exists() else []


def test_team_is_never_a_client(bot):
    b, api, tmp = bot
    b.store.state["sessions"]["111"] = {"id": "x", "step": "lang", "fields": {}, "source": "", "user": "", "started": 0, "lang": ""}
    b.handle(msg(111, "confirmed"))
    assert "work chat" in api.last("sendMessage")["text"] and "111" not in b.store.state["sessions"]
    b.handle(msg(222, "/start"))
    assert "work chat" in api.last("sendMessage")["text"]
    assert not (tmp / "floktron_leads.xlsx").exists()
    b.handle(msg(333, "hello"))
    assert "333" in b.store.state["sessions"]                    # a stranger still gets the dialog
    b.handle(msg(111, "/client"))
    assert b.store.state["sessions"]["111"]["source"] == "team_test"


def test_press_closes_and_edits_the_message(bot):
    b, api, tmp = bot
    task = {"message_id": 501, "chat": {"id": 111}, "text": "📬 Mail · DEMO Fiktīvs SIA\n«Offer?» · 19.11"}
    b.handle({"callback_query": {"id": "q1", "data": "fk:mail:abc123:y", "from": {"username": "boss"}, "message": task}})
    a = actions(tmp)
    assert a[-1]["kind"] == "mail" and a[-1]["key"] == "abc123" and a[-1]["ans"] == "y" and a[-1]["by"] == "@boss"
    ed = api.last("editMessageText")
    assert "✅ Closed ·" in ed["text"] and "reply_markup" not in ed
    assert api.last("answerCallbackQuery")["text"] == "Saved ✅"
    b.handle({"callback_query": {"id": "q2", "data": "fk:gw:G-1:n", "from": {}, "message": dict(task, chat={"id": 333})}})
    assert len(actions(tmp)) == 1                               # not the team: ignored


def test_text_reply_closes_with_comment(bot):
    b, api, tmp = bot
    rep = {"message_id": 7, "text": "🔎 Būve DEMO SIA",
           "reply_markup": {"inline_keyboard": tn.buttons("prospect", "P-0001", "en")}}
    b.handle(msg(111, "called them, interested", reply_to_message=rep))
    assert actions(tmp)[-1]["comment"] == "called them, interested" and actions(tmp)[-1]["key"] == "P-0001"
    closed = {"message_id": 7, "text": "🔎 Būve DEMO SIA\n\n✅ Closed · 25.11 10:31"}
    (tmp / "task_sent.jsonl").write_text(json.dumps({"chat": "111", "mid": 7, "y": "fk:prospect:P-0001:y"}) + "\n")
    b.handle(msg(111, "again", reply_to_message=closed))
    assert "already closed" in api.last("sendMessage")["text"] and len(actions(tmp)) == 1


def test_task_notice_outbox_and_actions(tmp_path):
    cfg = {"telegram": {"enabled": True, "data_dir": str(tmp_path)}}
    assert tn.via_telegram(cfg) and not tn.via_telegram(cfg, {"notify": "mail"})
    assert tn.send(cfg, "🧾 DEMO SaaS · 9 EUR", "gw", "G-0001", "ru", outbox=str(tmp_path / "out")) == ""
    m = json.loads(open(tmp_path / "out" / "telegram_tasks.jsonl", encoding="utf-8").read())
    yes, no = m["buttons"][0]
    assert yes["text"] == "✅ Нашёл" and no["text"] == "⛔ Не нужно" and len(yes["callback_data"].encode()) <= 64
    assert "sheet" not in m["text"].lower() and "column" not in m["text"].lower()
    p = tmp_path / "task_actions.jsonl"
    p.write_text('{"kind":"mail","key":"k1","ans":"y"}\n{"kind":"gw","key":"k2","ans":"n"}\n{"kind":"ma')
    got, off = tn.read_actions(str(p), 0, "gw")
    assert [x["key"] for x in got] == ["k2"] and tn.read_actions(str(p), off) == ([], off)
    assert tn.actions_path(cfg) == str(p)
