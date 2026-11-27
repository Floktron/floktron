# -*- coding: utf-8 -*-
"""0.38 «Bot security» — strangers get nothing, invites work once, tokens never reach a log, tasks carry minimum data.
All names, chats and numbers are TEST · FICTIONAL."""
import datetime
import io
import json
import os
import subprocess
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bot"))
import secret_store  # noqa: E402
import task_notice  # noqa: E402
import telegram_bot as tb  # noqa: E402
import worktime as wt  # noqa: E402

FLOW = yaml.safe_load(open(os.path.join(ROOT, "config", "bot_flow.example.yaml"), encoding="utf-8"))
FAKE_TG = "123456789:" + "AA" + "FakeTokenForTestsOnly" + "_" * 14   # TEST · FICTIONAL, built here so no scanner sees one
W = {"enabled": True, "geo": False, "invites": {"wt-anna0test": "Anna (TEST)"}}


class FakeApi:
    def __init__(self):
        self.sent, self.token = [], FAKE_TG

    def call(self, method, **p):
        self.sent.append((method, p))
        return {"message_id": len(self.sent)}

    def to(self, chat):
        return [p for m, p in self.sent if m == "sendMessage" and str(p.get("chat_id")) == str(chat)]


def make(tmp_path, **cfg):
    api = FakeApi()
    c = {"manager_chat_ids": [999], "_worktime": dict(W), "_company": {"language": "en"}, **cfg}
    return tb.Bot(api, FLOW, c, tb.Store(data_dir=str(tmp_path))), api


def msg(chat, text="", **extra):
    m = {"chat": {"id": chat, "type": "private"}, "from": {"id": chat, "username": "tester"}, "text": text}
    m.update(extra)
    return {"update_id": 1, "message": m}


def press(chat, data, frm=None, **msg_extra):
    return {"update_id": 2, "callback_query": {"id": "q", "data": data, "from": {"id": frm or chat},
                                               "message": {"chat": {"id": chat}, "message_id": 5, "text": "task", **msg_extra}}}


# ---------------------------------------------------------------- strangers
def test_strangers_get_nothing_and_nothing_is_kept(tmp_path):
    b, api = make(tmp_path)
    for text in ("/start", "hello", "/start qr_bucket", "/menu", "/privacy", "/leads", "/remove 1"):
        b.handle(msg(555, text))
    b.handle(msg(555, "", voice={"file_id": "x", "duration": 3}))
    b.handle(press(555, "s:lang:0"))
    b.handle(press(555, "fk:mail:abc:y"))
    assert not api.to(555)                                         # not a single answer
    assert all(m == "answerCallbackQuery" for m, _ in api.sent)   # only the spinner is stopped
    assert not b.store.state["sessions"] and not os.path.exists(tmp_path / "floktron_leads.xlsx")
    assert not os.path.exists(tmp_path / "task_actions.jsonl") and not os.path.exists(tmp_path / "voice")


def test_id_only_for_the_first_setup(tmp_path):
    b, api = make(tmp_path, manager_chat_ids=[])
    b.handle(msg(555, "/id"))
    assert "555" in api.to(555)[-1]["text"]
    b, api = make(tmp_path)
    b.handle(msg(555, "/id"))
    assert not api.to(555)


def test_dialog_mode_keeps_the_funnel(tmp_path):
    b, api = make(tmp_path, strangers="dialog")
    b.handle(msg(555, "/start"))
    assert "555" in b.store.state["sessions"] and api.to(555)


def test_press_from_another_person_or_without_message_does_nothing(tmp_path):
    b, api = make(tmp_path)
    b.handle(press(999, "fk:mail:abc:y", frm=777))                 # someone else pressed in the manager's chat (group)
    assert not os.path.exists(tmp_path / "task_actions.jsonl")
    b.handle({"update_id": 3, "callback_query": {"id": "q", "data": "fk:mail:abc:y", "from": {"id": 999}}})   # inline: no message
    b.handle(press(999, "fk:mail:abc:y"))
    assert json.loads(open(tmp_path / "task_actions.jsonl", encoding="utf-8").readline())["key"] == "abc"


def test_team_and_lead_messages_are_protected(tmp_path):
    b, api = make(tmp_path, strangers="dialog")
    sess = {"id": "abcd1234", "fields": {"name": "Anna (TEST)", "phone": "+371 20000000"}, "source": "", "lang": "en", "user": ""}
    b.finish(555, sess)
    assert api.to(999)[-1].get("protect_content") is True
    b2, api2 = make(tmp_path, strangers="dialog", protect_content=False)
    b2.finish(555, dict(sess, fields=dict(sess["fields"])))
    assert "protect_content" not in api2.to(999)[-1]


# ---------------------------------------------------------------- invites
def test_invite_works_once_for_one_person(tmp_path):
    b, api = make(tmp_path)
    b.handle(msg(4242, "/start wt-anna0test"))
    assert "4242" in b.team
    b.handle(msg(5353, "/start wt-anna0test"))                     # the link was forwarded
    assert "5353" not in b.team and "no longer works" in api.to(5353)[-1]["text"]
    assert any("Someone else" in p["text"] and "5353" in p["text"] for p in api.to(999))
    n = len(api.to(999))
    b.handle(msg(4242, "/start wt-anna0test"))                     # the owner again: fine, no new notices
    assert "4242" in b.team and len(api.to(999)) == n
    used = json.load(open(tmp_path / "worktime_invites_used.json", encoding="utf-8"))
    assert used["wt-anna0test"]["chat"] == "4242"


def test_expired_invite_is_refused(tmp_path):
    w = dict(W, invites={"wt-old0test": {"name": "Old (TEST)", "until": "2026-01-01"}})
    b, api = make(tmp_path, _worktime=w)
    b.handle(msg(4242, "/start wt-old0test"))
    assert "4242" not in b.team and "no longer works" in api.to(4242)[-1]["text"]
    name, st = wt.join_check(str(tmp_path / "worktime.jsonl"), w, "wt-old0test", 1,
                             now=datetime.datetime(2025, 12, 31, 12, 0))
    assert st == "ok"


def test_invite_used_before_038_belongs_to_whoever_joined(tmp_path):
    json.dump({"4242": "Anna (TEST)"}, open(tmp_path / "worktime_people.json", "w", encoding="utf-8"))
    b, api = make(tmp_path)
    b.handle(msg(5353, "/start wt-anna0test"))
    assert "5353" not in b.team and "4242" in b.team


def test_remove_by_manager_only(tmp_path):
    b, api = make(tmp_path)
    b.handle(msg(4242, "/start wt-anna0test"))
    b.handle(msg(4242, "/remove 4242"))                            # a team member cannot remove anyone
    assert "4242" in b.team
    b.handle(msg(999, "/remove 4242"))
    assert "4242" not in b.team and "removed" in api.to(999)[-1]["text"]
    n = len(api.to(4242))
    b.handle(msg(4242, "▶ Start"))                                  # now a stranger: ignored
    assert len(api.to(4242)) == n and not os.path.exists(tmp_path / "worktime.jsonl")


def test_cli_invite_is_long_and_expires(tmp_path):
    cfgp = tmp_path / "config.yaml"
    yaml.safe_dump({"worktime": {"enabled": True}, "telegram": {"bot_username": "demo_test_bot"}}, open(cfgp, "w"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "worktime.py"), "invite", "--name", "Ben (TEST)", "--days", "3",
                        "--config", str(cfgp), "--data", str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    inv = json.load(open(tmp_path / "worktime_invites.json", encoding="utf-8"))
    (code, v), = inv.items()
    assert len(code) == 19 and v["name"] == "Ben (TEST)" and f"t.me/demo_test_bot?start={code}" in r.stdout
    assert v["until"] == (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    b, api = make(tmp_path, _worktime={"enabled": True})          # the bot reads CLI invites without a restart
    b.handle(msg(6464, f"/start {code}"))
    assert "6464" in b.team


# ---------------------------------------------------------------- token
def test_token_is_hidden_everywhere():
    s = secret_store.redact(f"getUpdates: <urlopen https://api.telegram.org/bot{FAKE_TG}/getUpdates>")
    assert FAKE_TG not in s and "123456789:<hidden>" in s
    buf = io.StringIO()
    out = secret_store.RedactingStream(buf, "MyOtherSecret42")
    out.write(f"x {FAKE_TG} MyOtherSecret42 y\n")
    assert FAKE_TG not in buf.getvalue() and "MyOtherSecret42" not in buf.getvalue()


def test_token_from_env_first_and_a_clear_error(monkeypatch):
    monkeypatch.setenv("FLOKTRON_TG_TOKEN", FAKE_TG)
    assert tb.token_from({}) == FAKE_TG
    monkeypatch.delenv("FLOKTRON_TG_TOKEN")
    monkeypatch.setattr(secret_store, "get", lambda *a, **k: "")
    with pytest.raises(tb.BotError) as e:
        tb.token_from({"keychain_service": "TEST_FICTIONAL_BOT"})
    assert "--set-token" in str(e.value)


def test_set_token_refuses_garbage_and_never_prints_it(monkeypatch, capsys):
    monkeypatch.setattr(secret_store, "ask_hidden", lambda *a: "not a token")
    with pytest.raises(tb.BotError):
        tb.set_token({})
    saved = {}
    monkeypatch.setattr(secret_store, "ask_hidden", lambda *a: FAKE_TG)
    monkeypatch.setattr(tb.Api, "call", lambda self, m, **p: {"username": "demo_test_bot"})
    monkeypatch.setattr(secret_store, "put", lambda svc, v, *a: saved.setdefault(svc, v) and "")
    monkeypatch.setattr(secret_store, "where", lambda *a, **k: "TEST store")
    tb.set_token({"keychain_service": "TEST_FICTIONAL_BOT"})
    assert saved == {"TEST_FICTIONAL_BOT": FAKE_TG} and FAKE_TG not in capsys.readouterr().out


# ---------------------------------------------------------------- minimum data
def test_task_text_hides_contacts_and_payment_details(tmp_path):
    cfg = {"telegram": {"enabled": True, "data_dir": str(tmp_path)}}
    task_notice.send(cfg, "📬 Mail · Anna (TEST) <anna.test@demo-sia.lv> · +371 2000 0000\n"
                          "IBAN LV80BANK0000435195001 · card 4111 1111 1111 1111 · code 010190-12345 · 1 234,56 €",
                     "mail", "k1", outbox=str(tmp_path))
    t = json.loads(open(tmp_path / "telegram_tasks.jsonl", encoding="utf-8").readline())["text"]
    for secret in ("anna.test@", "2000 0000", "LV80BANK0000435195001", "4111 1111 1111 1111", "010190-12345"):
        assert secret not in t
    assert "Anna (TEST)" in t and "a…@demo-sia.lv" in t and "LV…5001" in t and "1 234,56 €" in t
    cfg["telegram"]["mask_personal"] = False
    task_notice.send(cfg, "anna.test@demo-sia.lv", "mail", "k2", outbox=str(tmp_path))
    assert "anna.test@demo-sia.lv" in open(tmp_path / "telegram_tasks.jsonl", encoding="utf-8").read()


def test_task_message_is_protected(tmp_path, monkeypatch):
    sent = []

    class Api:
        def __init__(self, *a, **k):
            pass

        def call(self, m, **p):
            sent.append(p)
            return {"message_id": 1}

    import bot.telegram_bot as tbm                  # task_notice imports it under this name
    monkeypatch.setattr(tbm, "Api", Api)
    monkeypatch.setattr(tbm, "token_from", lambda c: FAKE_TG)
    cfg = {"telegram": {"enabled": True, "data_dir": str(tmp_path), "manager_chat_ids": [999]}}
    assert task_notice.send(cfg, "task (TEST)", "mail", "k1") == ""
    assert sent[-1]["protect_content"] is True
