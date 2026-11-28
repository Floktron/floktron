# -*- coding: utf-8 -*-
"""The page from outside (0.43): the guard (scripts/page_guard.py) and sign-in by Face ID / fingerprint / phone code
(scripts/passkey.py). TEST · FICTIONAL — fictional people; no network: Telegram is a list in memory, the «phone» is this
test with its own P-256 key, ECDSA signatures and CBOR like a real WebAuthn authenticator."""
import hashlib
import http.client
import json
import os
import secrets
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import channels as C  # noqa: E402
import channels_web as CW  # noqa: E402
import page_guard as PG  # noqa: E402
import passkey as PK  # noqa: E402

HOST = "tasks.fictional.example"
ORIGIN = "https://" + HOST
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36"


def make_cfg(tmp_path, **guard):
    return {"_path": str(tmp_path / "config.yaml"), "company": {"language": "en"},
            "telegram": {"data_dir": str(tmp_path / "data"), "manager_chat_ids": ["111"]},
            "mail": {"user": "office@fictional.example"},
            "channels": {"enabled": True, "web": {"port": 0, "public_url": ORIGIN, "guard": guard},
                         "people": {"manager": {"name": "Anna TEST (fictional)", "channel": "web", "manager": True},
                                    "site1": {"name": "Jānis TEST (fictional)", "channel": "web"}}}}


@pytest.fixture
def web(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(PG, "notify", lambda cfg, text, buttons=None: sent.append({"text": text, "buttons": buttons or []}) or "")
    cfg = make_cfg(tmp_path, per_ip_min=100000)
    C.deliver(cfg, "📬 TEST task FICTIONAL SIA", [[{"text": "✅", "callback_data": "fk:mail:T1:y"}, {"text": "⛔", "callback_data": "fk:mail:T1:n"}]],
              lambda t, m: "")
    srv = CW.server(cfg, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]

    def req(method, path, body=None, outside=True, ua=IPHONE, ip="203.0.113.20", cookie="", key=None, cc="LV"):
        cn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        h = {"Host": HOST if outside else "127.0.0.1", "User-Agent": ua}
        if outside:
            h.update({"Cf-Ray": "test", "Cf-Connecting-Ip": ip, "Cf-Ipcountry": cc})
        if cookie:
            h["Cookie"] = cookie
        if method == "POST":
            h.update({"Content-Type": "application/json", "X-Floktron-Key": key or C.people(cfg)["manager"]["key"]})
        cn.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
        r = cn.getresponse()
        return r.status, r.read().decode("utf-8", "replace"), r.getheader("Set-Cookie") or ""

    def press(data, chat="111"):
        _, kind, key, ans = data.split(":")
        path = C.paths(cfg)["actions"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": "TEST", "chat": chat, "by": "TEST", "kind": kind, "key": key, "ans": ans}) + "\n")
    req("GET", "/m?k=" + C.people(cfg)["manager"]["key"])       # the guard starts reading presses from here
    sent.clear()
    yield cfg, req, press, sent, srv
    srv.shutdown()


def k(cfg, pid="manager"):
    return C.people(cfg)[pid]["key"]


def test_new_device_and_close(web):
    cfg, req, press, sent, _ = web
    old = k(cfg)
    assert req("GET", "/m?k=" + old)[0] == 200 and not sent                      # the first device: remembered silently
    assert req("GET", "/m?k=" + old, ua=ANDROID, cc="EE")[0] == 200
    assert len(sent) == 1 and "new device" in sent[0]["text"] and "Android · Chrome" in sent[0]["text"] and "EE" in sent[0]["text"]
    assert "203.0.113" not in sent[0]["text"] and old not in sent[0]["text"]       # no address, no key
    yes, no = (b[1] for b in sent[0]["buttons"])
    assert yes.startswith("fk:guard:dev-") and yes.endswith(":y") and no.endswith(":n")
    req("GET", "/m?k=" + old, ua=ANDROID, cc="EE")
    assert len(sent) == 1                                                            # not again within 6 h
    press(yes, chat="web")                                                           # a press from the page or a letter — never acts
    assert req("GET", "/m?k=" + old)[0] == 200 and k(cfg) == old
    press(yes)
    assert req("GET", "/m?k=" + old)[0] == 403                                       # closed from outside
    assert k(cfg) != old and "closed from outside" in sent[-1]["text"] and sent[-1]["buttons"][0][1] == "fk:guard:open:y"
    assert req("GET", "/m?k=" + k(cfg), outside=False)[0] == 200                      # this computer keeps working
    press("fk:guard:open:y")
    st, body, _ = req("GET", "/m?k=" + k(cfg))
    assert st == 200 and "TEST task" in body
    assert any(k(cfg) in m["text"] and "open again" in m["text"] for m in sent)      # the new link came to Telegram
    assert req("GET", "/m?k=" + old)[0] == 403                                       # the old one is dead


def test_its_me_and_service_buttons(web):
    cfg, req, press, sent, _ = web
    req("GET", "/m?k=" + k(cfg), ua=ANDROID)
    press(sent[-1]["buttons"][1][1])                                                 # ✅ It's me
    req("GET", "/m?k=" + k(cfg), ua=ANDROID)
    req("GET", "/m?k=" + k(cfg), ua=ANDROID)
    assert len(sent) == 1
    press("fk:guard:close:y")
    assert req("GET", "/m?k=" + k(cfg))[0] == 403 and "closed from outside" in sent[-1]["text"]
    press("fk:guard:open:y")
    assert req("GET", "/m?k=" + k(cfg))[0] == 200
    assert "Pin this message" in sent[-1]["text"]                                     # the service buttons come back
    old = {p: k(cfg, p) for p in ("manager", "site1")}
    press("fk:guard:out:y")                                                          # sign out everywhere
    req("GET", "/m?k=" + old["manager"])
    assert all(k(cfg, p) != old[p] for p in old)
    assert req("GET", "/m?k=" + k(cfg, "site1"))[0] == 200


def test_limits_and_wrong_keys(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(PG, "notify", lambda cfg, text, buttons=None: sent.append(text) or "")
    cfg = make_cfg(tmp_path, per_ip_min=5, flood_alert=4)
    srv = CW.server(cfg, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def get(path, ip, outside=True):
        cn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
        h = {"Host": HOST if outside else "127.0.0.1"}
        if outside:
            h.update({"Cf-Ray": "t", "Cf-Connecting-Ip": ip})
        cn.request("GET", path, headers=h)
        return cn.getresponse().status
    try:
        assert [get("/m?k=" + k(cfg), "198.51.100.1") for _ in range(6)] == [200] * 5 + [429]
        assert get("/m?k=" + k(cfg), "198.51.100.2") == 200                          # another address is not touched
        assert all(get("/m?k=" + k(cfg), "x", outside=False) == 200 for _ in range(10))   # this computer: no limits
        assert sum(get("/m?k=" + k(cfg), "198.51.100.1") == 429 for _ in range(4)) == 4
        assert any("stream of requests" in s for s in sent)
        assert [get("/m?k=wrong", "198.51.100.3") for _ in range(4)] == [403] * 4
        g = srv.RequestHandlerClass.guard
        g.g["bad_key_max"] = 3
        assert get("/m?k=wrong", "198.51.100.4") == 403 and get("/m?k=wrong", "198.51.100.4") == 403
        assert get("/m?k=wrong", "198.51.100.4") == 403
        assert get("/m?k=" + k(cfg), "198.51.100.4") == 429                           # waits an hour, even with the right key
    finally:
        srv.shutdown()


def test_key_age(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(PG, "notify", lambda cfg, text, buttons=None: sent.append((text, buttons)) or "")
    cfg = make_cfg(tmp_path)
    g = PG.Guard(cfg)
    t0 = time.time()
    g.check_keys(t0)
    assert not g.load()["key_at"]                                                     # never opened from outside → no clock
    g.load()["devices"]["manager"] = {"LV · iPhone · Safari": {}}
    g.check_keys(t0)
    old, topic = k(cfg), C.people(cfg)["manager"]["topic"]
    g.check_keys(t0 + 84 * 86400)
    assert "in 6 days" in sent[-1][0] and sent[-1][1][0][1] == "fk:guard:key-manager:y"
    n = len(sent)
    g.check_keys(t0 + 85 * 86400)
    assert len(sent) == n                                                             # warned once
    g.check_keys(t0 + 90 * 86400)
    assert k(cfg) != old and C.people(cfg)["manager"]["topic"] == topic               # the page key only; push stays
    assert k(cfg) in sent[-1][0]
    C.new_key(cfg, "manager")                                                          # a new key by hand → the clock starts again
    g.check_keys(t0 + 200 * 86400)
    assert g.load()["key_at"]["manager"][1] == t0 + 200 * 86400


# ---------------------------------------------------------------- the «phone»: a P-256 key, signatures, CBOR
D = secrets.randbelow(PK._N - 1) + 1
Q = PK._mul(D, PK._G)
CID = secrets.token_bytes(16)
RPH = hashlib.sha256(HOST.encode()).digest()


def sign(data):
    z = int.from_bytes(hashlib.sha256(data).digest(), "big")
    while True:
        kk = secrets.randbelow(PK._N - 1) + 1
        r = PK._mul(kk, PK._G)[0] % PK._N
        s = pow(kk, -1, PK._N) * (z + r * D) % PK._N
        if r and s:
            break

    def i2(x):
        b = x.to_bytes((x.bit_length() + 8) // 8, "big")
        return b"\x02" + bytes([len(b)]) + b
    body = i2(r) + i2(s)
    return b"\x30" + bytes([len(body)]) + body


def ce(x):
    def hd(mt, n):
        if n < 24:
            return bytes([mt << 5 | n])
        for ai, ln in ((24, 1), (25, 2), (26, 4)):
            if n < 1 << (8 * ln):
                return bytes([mt << 5 | ai]) + n.to_bytes(ln, "big")
    if isinstance(x, int):
        return hd(0, x) if x >= 0 else hd(1, -1 - x)
    if isinstance(x, bytes):
        return hd(2, len(x)) + x
    if isinstance(x, str):
        return hd(3, len(x.encode())) + x.encode()
    return hd(5, len(x)) + b"".join(ce(a) + ce(b) for a, b in x.items())


def cdata(typ, ch, origin=ORIGIN):
    return json.dumps({"type": typ, "challenge": ch, "origin": origin}).encode()


def test_ecdsa_and_cbor():
    data = b"TEST FICTIONAL"
    assert PK.ecdsa_ok(Q, data, sign(data)) and not PK.ecdsa_ok(Q, data + b"x", sign(data)) and not PK.ecdsa_ok(Q, data, b"\x30\x00")
    assert PK.cbor(ce({"a": 1, -2: b"\x01\x02", "n": -7}))[0] == {"a": 1, -2: b"\x01\x02", "n": -7}


def test_passkey_sign_in(web):
    cfg, req, press, sent, _ = web
    js = lambda r: json.loads(r[1]) if r[1].startswith("{") else {}   # noqa: E731

    def allowed():
        a = js(req("POST", "/m/pk/ask"))
        press(f"fk:pk:ask-{a['id']}:y")
        assert js(req("POST", "/m/pk/status", {"id": a["id"]}))["state"] == "ok"
        return a["id"]

    def register(aid, origin=ORIGIN):
        o = js(req("POST", "/m/pk/reg-opts", {"id": aid}))
        if not o.get("ok"):
            return 0, ""
        cose = ce({1: 2, 3: -7, -1: 1, -2: Q[0].to_bytes(32, "big"), -3: Q[1].to_bytes(32, "big")})
        ad = RPH + bytes([0x45]) + (0).to_bytes(4, "big") + b"\0" * 16 + len(CID).to_bytes(2, "big") + CID + cose
        r = req("POST", "/m/pk/reg", {"ask": aid, "id": PK.b64u(CID), "clientDataJSON": PK.b64u(cdata("webauthn.create", o["challenge"], origin)),
                                      "attestationObject": PK.b64u(ce({"fmt": "none", "attStmt": {}, "authData": ad}))})
        return r[0], r[2]
    cnt = [0]

    def login(origin=ORIGIN, bad=False, count=None, uv=True):
        o = js(req("POST", "/m/pk/opts"))
        cnt[0] += 1
        ad = RPH + bytes([0x05 if uv else 0x01]) + (cnt[0] if count is None else count).to_bytes(4, "big")
        cd = cdata("webauthn.get", o["challenge"], origin)
        sig = sign(ad + (b"x" if bad else hashlib.sha256(cd).digest()))
        r = req("POST", "/m/pk/check", {"id": PK.b64u(CID), "clientDataJSON": PK.b64u(cd), "authenticatorData": PK.b64u(ad), "signature": PK.b64u(sig)})
        return r[0], r[2]

    page = "/m?k=" + k(cfg)
    st, body, _ = req("GET", page)
    assert st == 200 and "Turn on sign-in protection" in body and "TEST task" in body
    assert "Turn on sign-in protection" not in req("GET", page, outside=False)[1]     # only through the https address
    assert register("nope")[0] == 0                                                   # no «Allow» in Telegram → nothing
    a1 = js(req("POST", "/m/pk/ask"))
    assert sent[-1]["buttons"][0][1] == f"fk:pk:ask-{a1['id']}:y" and "iPhone" in sent[-1]["text"] and k(cfg) not in sent[-1]["text"]
    assert js(req("POST", "/m/pk/status", {"id": a1["id"]}))["state"] == "wait"
    press(f"fk:pk:ask-{a1['id']}:y", chat="web")                                      # not from the manager's Telegram → nothing
    assert js(req("POST", "/m/pk/status", {"id": a1["id"]}))["state"] == "wait"
    press(f"fk:pk:ask-{a1['id']}:n")
    assert js(req("POST", "/m/pk/status", {"id": a1["id"]}))["state"] == "no" and register(a1["id"])[0] == 0
    assert register(allowed(), origin="https://evil.example")[0] == 400               # another web site
    aid = allowed()
    st, setc = register(aid)
    assert st == 200 and "fk_s=" in setc and "HttpOnly" in setc and "Secure" in setc
    assert "fk:pk:off-manager:y" in json.dumps(sent[-1]["buttons"]) and "fk:pk:now-manager:y" in json.dumps(sent[-1]["buttons"])
    assert register(aid)[0] in (0, 403)                                               # one «Allow» — one device
    s0 = setc.split(";")[0]
    st, body, _ = req("GET", page)
    assert st == 200 and "Open" in body and "TEST task" not in body and "Add this device" in body
    assert req("POST", "/m/act", {"k": "mail:T1", "ans": "y"})[0] == 403             # no press without the check
    assert req("GET", "/m/audio/pulse_2026-11-28.m4a?k=" + k(cfg))[0] == 403
    st, body, setc2 = req("GET", page, cookie=s0)
    assert st == 200 and "TEST task" in body and "Another device? Add" in body and "fk_s=" in setc2   # the session goes on
    assert "TEST task" in req("GET", page, outside=False)[1]                         # this computer never asks
    st, sc = login()
    assert st == 200 and "fk_s=" in sc
    assert login(bad=True)[0] == 403 and login(origin="https://evil.example")[0] == 403 and login(uv=False)[0] == 403
    assert login(count=1)[0] == 403                                                   # a copied key: the counter did not grow
    assert req("POST", "/m/pk/check", {"id": PK.b64u(CID), "clientDataJSON": "", "authenticatorData": "", "signature": ""})[0] == 403
    assert "TEST task" not in req("GET", page, cookie="fk_s=manager.1700000000.9999999999." + "0" * 32)[1]   # a forged session
    pks = web[4].RequestHandlerClass.passkeys
    u = C.people(cfg)["manager"]
    exp_old = pks.cookie(u, start=int(time.time()) - 13 * 3600)
    assert "Max-Age=1;" in exp_old                                                   # never longer than 12 h after the check
    press("fk:pk:now-manager:y")                                                      # «Close sign-ins now»
    assert "TEST task" not in req("GET", page, cookie=sc.split(";")[0])[1] and "closed" in sent[-1]["text"]
    st, sc = login()
    assert "TEST task" in req("GET", page, cookie=sc.split(";")[0])[1]
    press("fk:guard:out:y")                                                           # sign out everywhere → sessions too
    assert "TEST task" not in req("GET", "/m?k=" + k(cfg), cookie=sc.split(";")[0])[1]
    press("fk:pk:off-manager:y")
    assert "TEST task" in req("GET", "/m?k=" + k(cfg))[1] and "is off" in sent[-1]["text"]


def test_idle_session(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["channels"]["web"]["passkey"] = {"idle_min": 10, "hours": 12}
    p = PK.Passkeys(cfg)
    u = C.people(cfg)["manager"]
    c = p.cookie(u)
    assert "Max-Age=600;" in c or "Max-Age=599;" in c                                # 10 minutes without use → asks again
    assert PK.Passkeys(make_cfg(tmp_path)).page_block(u).count("visibilitychange") == 0   # not on yet → no reload script
