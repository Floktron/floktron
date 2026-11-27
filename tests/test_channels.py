# -*- coding: utf-8 -*-
"""Channels (0.40): each person chooses Telegram, their own page or e-mail (+ push); a press anywhere lands in
data/task_actions.jsonl (scripts/channels.py, scripts/channels_web.py, scripts/task_notice.py).
TEST · FICTIONAL — fictional people and companies; no network (push and mail go to an outbox folder)."""
import http.client
import json
import os
import re
import sys
import threading
import urllib.parse

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import channels as C  # noqa: E402
import channels_web as CW  # noqa: E402
import task_notice as tn  # noqa: E402


def make_cfg(tmp_path, **web):
    return {"_path": str(tmp_path / "config.yaml"), "company": {"language": "en"},
            "telegram": {"data_dir": str(tmp_path / "data")},
            "mail": {"user": "office@fictional.example", "reply_to": "office@fictional.example"},
            "worktime": {"enabled": True, "file": str(tmp_path / "data" / "worktime.jsonl"), "people": {"777": "Jānis TEST"}},
            "channels": {"enabled": True, "web": {"port": 0, **web},
                         "people": {"manager": {"name": "Anna TEST (fictional)", "channel": "telegram", "email": "anna@fictional.example"},
                                    "site1": {"name": "Jānis TEST (fictional)", "channel": "web", "time": True, "worktime_who": "777", "tasks": False}}}}


def lines(path):
    try:
        return [json.loads(x) for x in open(path, encoding="utf-8")]
    except OSError:
        return []


@pytest.fixture
def cfg(tmp_path):
    return make_cfg(tmp_path)


def test_people_keys_and_switch(cfg):
    p = C.people(cfg)
    assert p["manager"]["channel"] == "telegram" and len(p["manager"]["key"]) >= 30 and p["manager"]["key"] != p["site1"]["key"]
    assert C.people(cfg)["manager"]["key"] == p["manager"]["key"]          # kept in data/channels_state.json
    assert C.choose(cfg, "manager", "web") == "" and C.people(cfg)["manager"]["channel"] == "web"
    assert C.choose(cfg, "manager", "pigeon") != ""
    assert "e-mail" in C.choose(cfg, "site1", "email")                     # no address → refused
    assert C.choose(cfg, "nobody", "web") != ""


def test_telegram_ok_then_backup(cfg, tmp_path):
    sent = []
    assert C.deliver(cfg, "📬 TEST Ozols SIA · offer", tn.buttons("mail", "a1"), lambda t, m: sent.append(t) or "") == ""
    assert len(sent) == 1
    feed = C.feed(cfg, "manager")
    assert feed and feed[0]["text"].startswith("📬 TEST") and not C.feed(cfg, "site1")       # tasks: false → nothing
    C.choose(cfg, "manager", push=True)
    out = str(tmp_path / "out")
    assert C.deliver(cfg, "🧾 TEST Cloud Ltd 29 €", tn.buttons("gw", "g1"), lambda t, m: "Telegram: timed out", outbox=out) == ""
    push = lines(os.path.join(out, "channels_push.jsonl"))
    assert push and push[0]["body"] == "New task: payment without a document" and "TEST" not in json.dumps(push)
    assert push[0]["url"].endswith(C.people(cfg)["manager"]["topic"])


def test_email_summary_and_reply(cfg, tmp_path):
    out = str(tmp_path / "out")
    C.choose(cfg, "manager", "email")
    C.deliver(cfg, "📬 TEST Kalns SIA · contract", tn.buttons("mail", "b1"), lambda t, m: "")
    C.deliver(cfg, "🆕 TEST Būve SIA 12 000 €", tn.buttons("prospect", "b2"), lambda t, m: "")
    assert C.flush_mail(cfg, out) == 1
    m = lines(os.path.join(out, "channels_mail.jsonl"))[0]
    assert m["to"] == "anna@fictional.example" and m["subject"].startswith("FLOKTRON · 2 tasks")
    mt = [urllib.parse.unquote(x) for x in re.findall(r'mailto:[^"]+', m["html"])]
    assert len(mt) == 4 and all("FLOKTRON-ACT" in x for x in mt)
    subj = mt[0].split("subject=")[1]
    bad = subj[:-4] + "0000"
    n = C.read_replies(cfg, [dict(mid="<1@t>", subject="Re: " + subj, **{"from": "Anna <anna@fictional.example>"}),
                             dict(mid="<2@t>", subject=bad, **{"from": "anna@fictional.example"}),
                             dict(mid="<3@t>", subject=subj, **{"from": "stranger@evil.example"})])
    acts = lines(C.paths(cfg)["actions"])
    assert n == 1 and acts[-1]["by"] == "email" and acts[-1]["key"] == "b1" and acts[-1]["ans"] == "y"
    assert C.read_replies(cfg, [dict(mid="<1@t>", subject=subj, **{"from": "anna@fictional.example"})]) == 0   # once
    assert tn.read_actions(C.paths(cfg)["actions"], 0, "mail")[0][-1]["key"] == "b1"        # modules read it as before


def test_task_notice_routes_through_channels(cfg, tmp_path):
    C.choose(cfg, "manager", "web")
    assert tn.send(cfg, "📬 TEST letter from a…@fictional.example +371 20000000", "mail", "c1", "en") == ""
    it = C.feed(cfg, "manager")[0]
    assert "+371 20000000" not in it["text"] and "a…@fictional.example" in it["text"]           # minimum data stays


@pytest.fixture
def web(tmp_path):
    cfg = make_cfg(tmp_path, public_url="https://tasks.fictional.example")
    srv = CW.server(cfg, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]

    def req(method, path, body=None, headers=None):
        cn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        h = {"Host": "127.0.0.1"}
        h.update(headers or {})
        if isinstance(body, dict):
            body = json.dumps(body)
            h["Content-Type"] = "application/json"
        cn.request(method, path, body=body, headers=h)
        r = cn.getresponse()
        return r.status, r.read().decode("utf-8", "replace"), dict(r.getheaders())
    yield cfg, req
    srv.shutdown()


def test_page(web):
    cfg, req = web
    C.deliver(cfg, "📬 TEST <script>alert(1)</script> SIA", tn.buttons("mail", "d1"), lambda t, m: "")
    k, k2 = C.people(cfg)["manager"]["key"], C.people(cfg)["site1"]["key"]
    assert req("GET", "/m")[0] == 403
    st, body, hd = req("GET", "/m?k=" + k)
    assert st == 200 and "&lt;script&gt;" in body and "<script>alert" not in body
    assert "HttpOnly" in hd["Set-Cookie"] and "Secure" in hd["Set-Cookie"]
    assert 'data-t="start"' not in body and 'data-ch="email"' in body
    st, b2, _ = req("GET", "/m?k=" + k2)
    assert "d1" not in b2 and 'data-t="start"' in b2                                       # own tasks only, time buttons
    st, man, _ = req("GET", "/m/manifest.webmanifest?k=" + k)
    assert json.loads(man)["start_url"] == "/m?k=" + k
    assert req("POST", "/m/act", {"k": "mail:d1", "ans": "y"})[0] == 403                    # no key header
    assert req("POST", "/m/act", {"k": "mail:../x", "ans": "y"}, {"X-Floktron-Key": k})[0] == 400
    assert req("POST", "/m/act", {"k": "mail:d1", "ans": "y"}, {"X-Floktron-Key": k})[0] == 200
    a = lines(C.paths(cfg)["actions"])[-1]
    assert a["by"] == "web" and a["person"] == "manager" and a["kind"] == "mail" and a["ans"] == "y"
    assert C.feed(cfg, "manager")[0]["closed"]["ans"] == "y"
    assert req("POST", "/m/chan", {"channel": "web", "push": True}, {"X-Floktron-Key": k})[0] == 200
    assert C.people(cfg)["manager"]["channel"] == "web" and C.people(cfg)["manager"]["push"]


def test_worktime_from_page(web):
    cfg, req = web
    k2 = C.people(cfg)["site1"]["key"]
    st, body, _ = req("POST", "/m/time", {"action": "start", "loc": {"lat": 56.95, "lon": 24.1, "acc": 9}}, {"X-Floktron-Key": k2})
    assert st == 200 and "✅" in json.loads(body)["msg"]
    import worktime
    ev = worktime.read(worktime.events_path(cfg))
    assert ev and ev[-1].get("who") == "777" and ev[-1].get("by") == "web"
    k = C.people(cfg)["manager"]["key"]
    assert req("POST", "/m/time", {"action": "start"}, {"X-Floktron-Key": k})[0] == 400        # time: false


def test_mail_button_confirm_and_hosts(web):
    cfg, req = web
    C.choose(cfg, "manager", "email")
    C.deliver(cfg, "📬 TEST Liepa SIA", tn.buttons("mail", "e1"), lambda t, m: "")
    out = os.path.join(os.path.dirname(C.paths(cfg)["feed"]), "out")
    C.flush_mail(cfg, out)
    href = re.findall(r'href="(https://tasks\.fictional\.example/a\?[^"]+)"', lines(os.path.join(out, "channels_mail.jsonl"))[-1]["html"])
    assert len(href) == 2
    path = href[0].replace("https://tasks.fictional.example", "").replace("&amp;", "&")
    n0 = len(lines(C.paths(cfg)["actions"]))
    st, b, _ = req("GET", path, headers={"Host": "tasks.fictional.example"})
    assert st == 200 and "<form" in b and len(lines(C.paths(cfg)["actions"])) == n0           # opening closes nothing
    q = dict(urllib.parse.parse_qsl(path.split("?", 1)[1]))
    form = {"Host": "tasks.fictional.example", "Content-Type": "application/x-www-form-urlencoded"}
    assert req("POST", "/a", urllib.parse.urlencode(q), form)[0] == 200
    assert lines(C.paths(cfg)["actions"])[-1]["by"] == "email"
    assert req("POST", "/a", urllib.parse.urlencode(dict(q, a="n")), form)[0] == 403         # changed answer → bad signature
    k = C.people(cfg)["manager"]["key"]
    assert req("GET", "/m?k=" + k, headers={"Host": "evil.example"})[0] == 403
    assert req("GET", "/", headers={"Host": "tasks.fictional.example"})[0] == 404             # nothing else is served
    assert req("GET", "/data/task_actions.jsonl")[0] == 404


def test_off_by_default(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["channels"]["enabled"] = False
    out = str(tmp_path / "o")
    assert tn.send(cfg, "TEST", "mail", "z1", "en", outbox=out) == ""
    assert not os.path.exists(C.paths(cfg)["feed"])
