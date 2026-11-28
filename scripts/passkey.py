# -*- coding: utf-8 -*-
"""FLOKTRON · passkey.py — sign-in protection of a person's page (/m): Face ID, a fingerprint or the phone's screen-lock
code (a passkey, WebAuthn). Even with the person's link, nobody opens the page from outside without that person's phone.

  • turn on — on the page «🔐 Turn on sign-in protection» → the manager gets «Allow?» in Telegram (a stranger with a
    leaked link cannot add their own face) → «Continue» → the phone asks Face ID / fingerprint / code → saved;
  • from outside (through the tunnel) the page first shows only «Open»; after the check it works like a banking app:
    while it is in use — no questions; the phone put away for channels.web.passkey.idle_min (10) minutes or more —
    it asks again; never longer than passkey.hours (12) after the last check;
  • «➕ Add this device» — a second phone or a computer is added the same way, with «Allow» in Telegram;
  • Telegram: «🔐 Close sign-ins now» (every open session stops at once — a phone handed to someone) and
    «🔓 Turn off protection» (the phone was replaced and the page does not open);
  • on this computer (127.0.0.1) and in the office network it never asks.
The secret of the face / finger stays in the phone (iCloud Keychain / Google Password Manager); only the public P-256 key
comes here. The signature is checked in pure Python (no extra libraries). State: data/passkeys.json (0600).
Docs: docs/CHANNELS.md «Protection from outside»."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import urllib.parse
from html import escape

import channels as C
from page_guard import safe_id, tunnel

# ---------------------------------------------------------------- P-256 / ECDSA (signature check)
_P = 2**256 - 2**224 + 2**192 + 2**96 - 1
_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
_G = (0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
      0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5)


def on_curve(q):
    x, y = q
    return 0 <= x < _P and 0 <= y < _P and (y * y - (x * x * x - 3 * x + _B)) % _P == 0


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    (x1, y1), (x2, y2) = a, b
    if x1 == x2 and (y1 + y2) % _P == 0:
        return None
    lam = (3 * x1 * x1 - 3) * pow(2 * y1, -1, _P) % _P if a == b else (y2 - y1) * pow(x2 - x1, -1, _P) % _P
    x3 = (lam * lam - x1 - x2) % _P
    return x3, (lam * (x1 - x3) - y1) % _P


def _mul(k, q):
    r = None
    while k:
        if k & 1:
            r = _add(r, q)
        q = _add(q, q)
        k >>= 1
    return r


def _der(sig):
    """ECDSA signature in DER → (r, s)."""
    if len(sig) < 8 or sig[0] != 0x30 or sig[2] != 2:
        raise ValueError("der")
    lr = sig[3]
    r = int.from_bytes(sig[4:4 + lr], "big")
    i = 4 + lr
    if sig[i] != 2:
        raise ValueError("der s")
    return r, int.from_bytes(sig[i + 2:i + 2 + sig[i + 1]], "big")


def ecdsa_ok(q, data, sig):
    try:
        r, s = _der(sig)
    except (ValueError, IndexError):
        return False
    if not (0 < r < _N and 0 < s < _N) or not on_curve(q):
        return False
    z = int.from_bytes(hashlib.sha256(data).digest(), "big")
    w = pow(s, -1, _N)
    x = _add(_mul(z * w % _N, _G), _mul(r * w % _N, q))
    return x is not None and x[0] % _N == r


# ---------------------------------------------------------------- CBOR (only what WebAuthn needs)
def cbor(b, i=0):
    ib = b[i]
    mt, ai = ib >> 5, ib & 31
    i += 1
    if ai < 24:
        v = ai
    elif ai in (24, 25, 26, 27):
        n = 1 << (ai - 24)
        v = int.from_bytes(b[i:i + n], "big")
        i += n
    else:
        raise ValueError("cbor: indefinite length")
    if mt == 0:
        return v, i
    if mt == 1:
        return -1 - v, i
    if mt == 2:
        return bytes(b[i:i + v]), i + v
    if mt == 3:
        return bytes(b[i:i + v]).decode("utf-8"), i + v
    if mt == 4:
        out = []
        for _ in range(v):
            x, i = cbor(b, i)
            out.append(x)
        return out, i
    if mt == 5:
        out = {}
        for _ in range(v):
            k, i = cbor(b, i)
            x, i = cbor(b, i)
            out[k] = x
        return out, i
    if mt == 7:
        return {20: False, 21: True, 22: None}.get(v), i
    raise ValueError("cbor: type")


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def ub64u(s):
    return base64.urlsafe_b64decode(str(s) + "=" * (-len(str(s)) % 4))


# ---------------------------------------------------------------- texts
TEXT = {
    "en": {"h": "Sign-in protection",
           "off": "Even with your link, nobody opens this page without your face, finger or phone code. The phone picks the way: "
                  "Face ID, a fingerprint or the screen-lock code. Turning it on is confirmed in Telegram.",
           "turn_on": "🔐 Turn on sign-in protection",
           "on": "🔐 On: {devs}. From the internet the page opens only after Face ID, a fingerprint or the phone code. While you use it — "
                 "no questions; the phone put away for {m} min or more — it asks again. Close all sign-ins at once or turn it off — buttons in Telegram.",
           "other": "➕ Another device? Add", "lock": "The page is closed. Open it the same way as the phone: Face ID, fingerprint or code.",
           "open": "Open", "help": "Does not work? The manager has «Turn off protection» in Telegram.",
           "new": "A new device (another phone, a computer)? Add it — the confirmation comes to Telegram.", "add": "➕ Add this device",
           "no_api": "This browser cannot sign in by face, fingerprint or phone code", "allowed": "Allowed ✅ Tap «Continue».",
           "cont": "Continue", "said_no": "«No» was tapped in Telegram.", "late": "Time is up — start again.",
           "wait": "Confirm in Telegram (a message from FLOKTRON)…", "done": "Done 🔐",
           "cancel": "Cancelled, or this device is already added — tap again", "fail": "Did not work. A new device? Tap «Add this device» below.",
           "https": "Sign-in by face, fingerprint or code works only through your https address (channels.web.public_url)",
           "need_ok": "Permission in Telegram is needed", "retry": "Did not work — try again", "not_on": "Sign-in protection is not on",
           "no_match": "Did not match — try again", "device": "device",
           "tg_ask": "🔐 FLOKTRON: on the page of «{name}» someone wants to turn on sign-in protection (Face ID, fingerprint or phone code).\n"
                     "Device: {dev}.\nYou or your person — «Allow» (valid {m} min). If not — «No».",
           "allow": "✅ Allow", "no": "⛔ No",
           "tg_on": "🔐 FLOKTRON: sign-in protection is on for «{name}» ({dev}). The page opens by Face ID, fingerprint or phone code.\n"
                    "If the page stops opening — «Turn off protection».",
           "close_now": "🔐 Close sign-ins now", "turn_off": "🔓 Turn off protection",
           "tg_now": "🔐 FLOKTRON: all open sign-ins to the page of «{name}» are closed. The next one — only by Face ID, fingerprint or phone code.",
           "tg_off": "🔓 FLOKTRON: sign-in protection of «{name}» is off. Turn it on again — on the page."},
    "lv": {"h": "Ieejas aizsardzība",
           "off": "Pat ar jūsu saiti neviens neatvērs šo lapu bez jūsu sejas, pirksta vai tālruņa koda. Tālrunis pats izvēlas veidu: "
                  "Face ID, pirkstu nospiedumu vai ekrāna bloķēšanas kodu. Ieslēgšanu apstiprina Telegram.",
           "turn_on": "🔐 Ieslēgt ieejas aizsardzību",
           "on": "🔐 Ieslēgta: {devs}. No interneta lapa atveras tikai pēc Face ID, pirksta nospieduma vai tālruņa koda. Kamēr lietojat — "
                 "bez jautājumiem; tālrunis nolikts uz {m} min vai ilgāk — jautās atkal. Aizvērt visas ieejas uzreiz vai izslēgt — ar pogām Telegram.",
           "other": "➕ Cita ierīce? Pievienot", "lock": "Lapa ir aizvērta. Atveriet to tāpat kā tālruni: Face ID, nospiedums vai kods.",
           "open": "Atvērt", "help": "Nesanāk? Vadītājam Telegram ir poga «Izslēgt aizsardzību».",
           "new": "Jauna ierīce (cits tālrunis, dators)? Pievienojiet to — apstiprinājums atnāks Telegram.", "add": "➕ Pievienot šo ierīci",
           "no_api": "Šis pārlūks neprot ieeju ar seju, nospiedumu vai tālruņa kodu", "allowed": "Atļauts ✅ Nospiediet «Turpināt».",
           "cont": "Turpināt", "said_no": "Telegram nospieda «Nē».", "late": "Laiks beidzies — sāciet no jauna.",
           "wait": "Apstipriniet Telegram (ziņa no FLOKTRON)…", "done": "Gatavs 🔐",
           "cancel": "Atcelts vai šī ierīce jau pievienota — nospiediet vēlreiz", "fail": "Nesanāca. Jauna ierīce? Nospiediet «Pievienot šo ierīci» zemāk.",
           "https": "Ieeja ar seju, nospiedumu vai kodu darbojas tikai caur jūsu https adresi (channels.web.public_url)",
           "need_ok": "Vajadzīga atļauja Telegram", "retry": "Nesanāca — mēģiniet vēlreiz", "not_on": "Ieejas aizsardzība nav ieslēgta",
           "no_match": "Neder — mēģiniet vēlreiz", "device": "ierīce",
           "tg_ask": "🔐 FLOKTRON: lapā «{name}» grib ieslēgt ieejas aizsardzību (Face ID, nospiedums vai tālruņa kods).\n"
                     "Ierīce: {dev}.\nJūs vai jūsu cilvēks — «Atļaut» (derīgs {m} min). Ja nē — «Nē».",
           "allow": "✅ Atļaut", "no": "⛔ Nē",
           "tg_on": "🔐 FLOKTRON: «{name}» ieejas aizsardzība ieslēgta ({dev}). Lapa atveras ar Face ID, nospiedumu vai tālruņa kodu.\n"
                    "Ja lapa vairs neatveras — «Izslēgt aizsardzību».",
           "close_now": "🔐 Aizvērt ieejas tagad", "turn_off": "🔓 Izslēgt aizsardzību",
           "tg_now": "🔐 FLOKTRON: visas atvērtās ieejas «{name}» lapā aizvērtas. Nākamā — tikai ar Face ID, nospiedumu vai tālruņa kodu.",
           "tg_off": "🔓 FLOKTRON: «{name}» ieejas aizsardzība izslēgta. Ieslēgt atkal — lapā."},
    "ru": {"h": "Защита входа",
           "off": "Даже с вашей ссылкой никто не откроет эту страницу без вашего лица, пальца или кода телефона. Телефон сам выберет способ: "
                  "Face ID, отпечаток или код блокировки экрана. Включение подтверждается в Telegram.",
           "turn_on": "🔐 Включить защиту входа",
           "on": "🔐 Включена: {devs}. Через интернет страница открывается только после Face ID, отпечатка или кода телефона. Пока пользуетесь — "
                 "без вопросов; отложили телефон на {m} мин и дольше — спросит снова. Закрыть все входы сразу или отключить — кнопками в Telegram.",
           "other": "➕ Другое устройство? Добавить", "lock": "Страница закрыта. Откройте так же, как телефон: Face ID, отпечаток или код.",
           "open": "Открыть", "help": "Не получается? У управляющего в Telegram есть кнопка «Отключить защиту».",
           "new": "Это новое устройство (другой телефон, компьютер)? Добавьте его — подтверждение придёт в Telegram.", "add": "➕ Добавить это устройство",
           "no_api": "Этот браузер не умеет вход по лицу, отпечатку или коду телефона", "allowed": "Разрешено ✅ Нажмите «Продолжить».",
           "cont": "Продолжить", "said_no": "В Telegram нажали «Нет».", "late": "Время вышло — начните заново.",
           "wait": "Подтвердите в Telegram (сообщение от FLOKTRON)…", "done": "Готово 🔐",
           "cancel": "Отменено или это устройство уже добавлено — нажмите ещё раз", "fail": "Не вышло. Новое устройство? Нажмите «Добавить это устройство» ниже.",
           "https": "Вход по лицу, отпечатку или коду работает только через ваш https-адрес (channels.web.public_url)",
           "need_ok": "Нужно разрешение в Telegram", "retry": "Не получилось — попробуйте ещё раз", "not_on": "Защита входа не включена",
           "no_match": "Не подошло — попробуйте ещё раз", "device": "устройство",
           "tg_ask": "🔐 FLOKTRON: на странице «{name}» хотят включить защиту входа (Face ID, отпечаток или код телефона).\n"
                     "Устройство: {dev}.\nВы или ваш человек — «Разрешить» (действует {m} мин). Если нет — «Нет».",
           "allow": "✅ Разрешить", "no": "⛔ Нет",
           "tg_on": "🔐 FLOKTRON: защита входа «{name}» включена ({dev}). Страница открывается по Face ID, отпечатку или коду телефона.\n"
                    "Если страница перестанет открываться — «Отключить защиту».",
           "close_now": "🔐 Закрыть входы сейчас", "turn_off": "🔓 Отключить защиту",
           "tg_now": "🔐 FLOKTRON: все открытые входы на страницу «{name}» закрыты. Следующий — только по Face ID, отпечатку или коду телефона.",
           "tg_off": "🔓 FLOKTRON: защита входа «{name}» отключена. Включить снова — на странице."},
}
ASK_MIN = 10       # «Allow» in Telegram is valid 10 minutes

JS_B64 = ("function b2u(b){b=new Uint8Array(b);var s='';for(var i=0;i<b.length;i++)s+=String.fromCharCode(b[i]);"
          "return btoa(s).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'')}"
          "function u2b(s){s=s.replace(/-/g,'+').replace(/_/g,'/');while(s.length%4)s+='=';var b=atob(s),a=new Uint8Array(b.length);"
          "for(var i=0;i<b.length;i++)a[i]=b.charCodeAt(i);return a.buffer}"
          "function fp(p,d){return fetch(p,{method:'POST',headers:{'Content-Type':'application/json','X-Floktron-Key':K},body:JSON.stringify(d||{})}).then(function(r){return r.json()})}")


def _js(v):
    return json.dumps(v, ensure_ascii=False).replace("<", "\\u003c")


class Passkeys:
    def __init__(self, cfg, guard=None):
        self.cfg = cfg
        self.guard = guard
        pk = ((cfg.get("channels") or {}).get("web") or {}).get("passkey") or {}
        self.idle = float(pk.get("idle_min") or 10)
        self.hours = float(pk.get("hours") or 12)
        self.path = os.path.join(C.data_dir(cfg), "passkeys.json")
        self.lock = threading.RLock()
        self.ch = {}             # pid → (challenge, until, "create" | "get")

    def t(self):
        return TEXT.get(C.lang_of(self.cfg)) or TEXT["en"]

    def load(self):
        st = C._read_json(self.path)
        for k in ("creds", "asks", "epoch"):
            st.setdefault(k, {})
        return st

    def save(self, st):
        C._write_json(self.path, st)

    def enabled(self, pid):
        with self.lock:
            return bool(self.load()["creds"].get(pid))

    def rp(self):
        url = C.ccfg(self.cfg)["web"].get("public_url") or ""
        host = (urllib.parse.urlsplit(url).hostname or "") if url.startswith("https://") else ""
        return host, f"https://{host}"

    def say(self, text, buttons=None):
        if self.guard:
            return self.guard.say(text, buttons)
        import page_guard
        return page_guard.notify(self.cfg, text, buttons)

    # ------------------------------------------------------------ session (a signed cookie)
    def _sig(self, u, start, exp):
        with self.lock:
            ep = int(self.load()["epoch"].get(u["id"], 0))
        msg = f"pk1|{u['id']}|{start}|{exp}|{u['key']}|{ep}".encode()
        return hmac.new(C._secret(self.cfg), msg, hashlib.sha256).hexdigest()[:32]

    def cookie(self, u, start=None):
        """start — the time of the face / finger / code check; exp — idle_min after the last request, never later than
        start + hours."""
        now = int(time.time())
        start = int(start or now)
        exp = int(min(now + self.idle * 60, start + self.hours * 3600))
        return (f"fk_s={safe_id(u['id'])}.{start}.{exp}.{self._sig(u, start, exp)}; Path=/m; Max-Age={max(1, exp - now)}; "
                "HttpOnly; SameSite=Strict; Secure")

    def _session(self, h, u):
        m = re.search(r"(?:^|;\s*)fk_s=(\w+)\.(\d{9,12})\.(\d{9,12})\.([0-9a-f]{32})", h.headers.get("Cookie") or "")
        if not m or m.group(1) != safe_id(u["id"]) or int(m.group(3)) < time.time():
            return None
        start, exp = int(m.group(2)), int(m.group(3))
        return start if hmac.compare_digest(self._sig(u, start, exp), m.group(4)) else None

    def locked(self, h, u):
        """From outside, protection on, no fresh check → only the «Open» page."""
        return tunnel(h) and self.enabled(u["id"]) and self._session(h, u) is None

    def refresh(self, h, u):
        """A live session from outside → the cookie for idle_min more ('' — nothing to extend)."""
        if not u or not tunnel(h) or not self.enabled(u["id"]):
            return ""
        start = self._session(h, u)
        return self.cookie(u, start) if start else ""

    # ------------------------------------------------------------ presses from Telegram (via page_guard)
    def on_press(self, key, yes):
        """ask-<id> — allow turning on; now-<pid> — close every open sign-in; off-<pid> — turn protection off.
        → [(text, buttons)] for Telegram."""
        t = self.t()
        people = C.people(self.cfg)
        with self.lock:
            st = self.load()
            if key.startswith(("now-", "off-")):
                pid = next((p for p in people if safe_id(p) == key[4:]), None)
                if not yes or not pid or not st["creds"].get(pid):
                    return []
                if key.startswith("now-"):
                    st["epoch"][pid] = int(st["epoch"].get(pid, 0)) + 1
                    self.save(st)
                    return [(t["tg_now"].format(name=people[pid]["name"]), [(t["close_now"], f"fk:pk:now-{safe_id(pid)}:y")])]
                st["creds"].pop(pid, None)
                self.save(st)
                return [(t["tg_off"].format(name=people[pid]["name"]), None)]
            a = st["asks"].get(key[4:] if key.startswith("ask-") else key)
            if not a or a.get("state") != "wait":
                return []
            a["state"] = "ok" if yes else "no"
            a["until"] = time.time() + ASK_MIN * 60
            self.save(st)
        return []

    # ------------------------------------------------------------ the page API: POST /m/pk/<op>
    def _client_data(self, d, typ, pid, origin):
        cd = ub64u(d.get("clientDataJSON", ""))
        j = json.loads(cd)
        ch, until, kind = self.ch.pop(pid, (b"", 0, ""))
        ok = (j.get("type") == typ and until > time.time() and kind == typ.split(".")[1] and bool(ch)
              and hmac.compare_digest(ub64u(j.get("challenge", "")), ch) and j.get("origin") == origin)
        return cd, ok

    def api(self, h, op, d, u, device=""):
        """→ (code, dict, extra headers)."""
        t = self.t()
        pid = u["id"]
        rp, origin = self.rp()
        if not rp:
            return 400, {"ok": False, "err": t["https"]}, None
        if op == "ask":
            aid = secrets.token_hex(4)
            with self.lock:
                st = self.load()
                st["asks"] = {k: v for k, v in st["asks"].items() if v.get("at", 0) > time.time() - 86400}
                st["asks"][aid] = {"pid": pid, "state": "wait", "at": time.time(), "dev": device[:60]}
                self.save(st)
            self.say(t["tg_ask"].format(name=u["name"], dev=device or t["device"], m=ASK_MIN),
                     [(t["allow"], f"fk:pk:ask-{aid}:y"), (t["no"], f"fk:pk:ask-{aid}:n")])
            return 200, {"ok": True, "id": aid}, None
        with self.lock:
            st = self.load()
        a = st["asks"].get(str(d.get("id") or d.get("ask") or ""))
        a = a if a and a.get("pid") == pid else None
        if op == "status":
            s = (a or {}).get("state", "none")
            if s == "ok" and a.get("until", 0) < time.time():
                s = "late"
            return 200, {"ok": True, "state": s}, None
        if op == "reg-opts":
            if not a or a.get("state") != "ok" or a.get("until", 0) < time.time():
                return 403, {"ok": False, "err": t["need_ok"]}, None
            ch = secrets.token_bytes(32)
            self.ch[pid] = (ch, time.time() + 300, "create")
            return 200, {"ok": True, "challenge": b64u(ch), "rp": {"id": rp, "name": "FLOKTRON"},
                         "user": {"id": b64u(hashlib.sha256(("floktron|" + pid).encode()).digest()[:16]), "name": f"floktron-{safe_id(pid)}",
                                  "displayName": u["name"]}, "exclude": [x["id"] for x in st["creds"].get(pid, [])]}, None
        if op == "reg":
            try:
                cd, ok = self._client_data(d, "webauthn.create", pid, origin)
                att, _ = cbor(ub64u(d.get("attestationObject", "")))
                ad = att["authData"]
                if not ok:
                    raise ValueError("challenge / origin")
                if ad[:32] != hashlib.sha256(rp.encode()).digest():
                    raise ValueError("rpId")
                fl = ad[32]
                if not (fl & 0x01 and fl & 0x04 and fl & 0x40):
                    raise ValueError("flags")
                cnt = int.from_bytes(ad[33:37], "big")
                ln = int.from_bytes(ad[53:55], "big")
                cid = ad[55:55 + ln]
                key, _ = cbor(ad, 55 + ln)
                if key.get(1) != 2 or key.get(3) != -7 or key.get(-1) != 1:
                    raise ValueError("ES256 / P-256 only")
                q = (int.from_bytes(key[-2], "big"), int.from_bytes(key[-3], "big"))
                if not on_curve(q) or b64u(cid) != d.get("id"):
                    raise ValueError("key")
            except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
                print(f"passkey: {pid} — refused ({str(e)[:50]})")
                return 400, {"ok": False, "err": t["retry"]}, None
            with self.lock:
                st = self.load()
                a = st["asks"].get(str(d.get("ask", "")))
                if not a or a.get("pid") != pid or a.get("state") != "ok":
                    return 403, {"ok": False, "err": t["need_ok"]}, None
                a["state"] = "used"
                lst = st["creds"].setdefault(pid, [])
                lst.append({"id": b64u(cid), "x": hex(q[0]), "y": hex(q[1]), "count": cnt, "at": time.strftime("%d.%m.%Y %H:%M"), "dev": device[:60]})
                st["creds"][pid] = lst[-5:]
                self.save(st)
            self.say(t["tg_on"].format(name=u["name"], dev=device or t["device"]),
                     [(t["close_now"], f"fk:pk:now-{safe_id(pid)}:y"), (t["turn_off"], f"fk:pk:off-{safe_id(pid)}:y")])
            return 200, {"ok": True}, {"Set-Cookie": self.cookie(u)}
        if op == "opts":
            creds = st["creds"].get(pid, [])
            if not creds:
                return 400, {"ok": False, "err": t["not_on"]}, None
            ch = secrets.token_bytes(32)
            self.ch[pid] = (ch, time.time() + 300, "get")
            return 200, {"ok": True, "challenge": b64u(ch), "rpId": rp, "allow": [x["id"] for x in creds]}, None
        if op == "check":
            good = False
            try:
                cd, ok = self._client_data(d, "webauthn.get", pid, origin)
                ad, sig = ub64u(d.get("authenticatorData", "")), ub64u(d.get("signature", ""))
                cr = next((x for x in st["creds"].get(pid, []) if x["id"] == d.get("id")), None)
                good = bool(ok and cr and ad[:32] == hashlib.sha256(rp.encode()).digest() and ad[32] & 0x01 and ad[32] & 0x04
                            and ecdsa_ok((int(cr["x"], 16), int(cr["y"], 16)), ad + hashlib.sha256(cd).digest(), sig))
                if good:
                    cnt = int.from_bytes(ad[33:37], "big")
                    if cnt and cr["count"] and cnt <= cr["count"]:
                        good = False                  # a copied key: the counter did not grow
                    else:
                        with self.lock:
                            st = self.load()
                            for x in st["creds"].get(pid, []):
                                if x["id"] == cr["id"]:
                                    x["count"], x["last"] = cnt, time.strftime("%d.%m %H:%M")
                            self.save(st)
            except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                good = False
            if not good:
                if self.guard:
                    self.guard.bad_key(h)
                return 403, {"ok": False, "err": t["no_match"]}, None
            return 200, {"ok": True}, {"Set-Cookie": self.cookie(u)}
        return 404, {"ok": False}, None

    # ------------------------------------------------------------ HTML
    def _reg_js(self, key, bid, mid, label):
        t = self.t()
        return ('<script>(function(){var K=' + _js(key) + ',T=' + _js({k: t[k] for k in ("no_api", "allowed", "cont", "said_no", "late", "wait", "done", "cancel")})
                + ';' + JS_B64 +
                "var m=document.getElementById('" + mid + "'),b=document.getElementById('" + bid + "'),A='',L=" + _js(label) + ";"
                "if(!window.PublicKeyCredential){b.disabled=true;m.textContent=T.no_api;return}"
                "function wait(){fp('/m/pk/status',{id:A}).then(function(s){if(s.state==='ok'){m.textContent=T.allowed;"
                "b.disabled=false;b.textContent=T.cont;b.onclick=reg}else if(s.state==='wait'){setTimeout(wait,3000)}"
                "else{m.textContent=s.state==='no'?T.said_no:T.late;b.disabled=false;b.textContent=L;b.onclick=ask}})}"
                "function ask(){b.disabled=true;fp('/m/pk/ask').then(function(r){if(!r.ok){m.textContent=r.err;b.disabled=false;return}"
                "A=r.id;m.textContent=T.wait;wait()})}"
                "function reg(){b.disabled=true;fp('/m/pk/reg-opts',{id:A}).then(function(o){if(!o.ok){m.textContent=o.err;return}"
                "return navigator.credentials.create({publicKey:{challenge:u2b(o.challenge),rp:o.rp,user:{id:u2b(o.user.id),name:o.user.name,displayName:o.user.displayName},"
                "pubKeyCredParams:[{type:'public-key',alg:-7}],authenticatorSelection:{userVerification:'required',residentKey:'preferred'},attestation:'none',timeout:60000,"
                "excludeCredentials:o.exclude.map(function(i){return{type:'public-key',id:u2b(i)}})}}).then(function(c){var r=c.response;"
                "return fp('/m/pk/reg',{ask:A,id:c.id,clientDataJSON:b2u(r.clientDataJSON),attestationObject:b2u(r.attestationObject)})})"
                ".then(function(x){if(x&&x.ok){m.textContent=T.done;setTimeout(function(){location.reload()},900)}else if(x){m.textContent=x.err;b.disabled=false}})})"
                ".catch(function(){m.textContent=T.cancel;b.disabled=false})}"
                "b.onclick=ask;})();</script>")

    def lock_inner(self, u):
        """The page before the check: not a single task. «Open» — for a device already added; «Add this device» — a new one."""
        t = self.t()
        return ('<div class="card" style="text-align:center;padding:28px 16px"><div style="font-size:42px">🔐</div>'
                f'<p style="margin:10px 0 18px">{escape(t["lock"])}</p>'
                f'<button class="b y" id="pko" style="width:100%">{escape(t["open"])}</button>'
                f'<p class="muted" id="pkm" style="margin-top:12px">{escape(t["help"])}</p></div>'
                f'<div class="card"><div class="muted" style="margin-bottom:10px">{escape(t["new"])}</div>'
                f'<button class="b p" id="pka" style="width:100%">{escape(t["add"])}</button><div class="muted" id="pkam" style="margin-top:8px"></div></div>'
                '<script>(function(){var K=' + _js(u["key"]) + ',F=' + _js(t["fail"]) + ';' + JS_B64 +
                "function go(){var m=document.getElementById('pkm');fp('/m/pk/opts').then(function(o){if(!o.ok){m.textContent=o.err;return}"
                "return navigator.credentials.get({publicKey:{challenge:u2b(o.challenge),rpId:o.rpId,userVerification:'required',timeout:60000,"
                "allowCredentials:o.allow.map(function(i){return{type:'public-key',id:u2b(i)}})}}).then(function(c){var r=c.response;"
                "return fp('/m/pk/check',{id:c.id,clientDataJSON:b2u(r.clientDataJSON),authenticatorData:b2u(r.authenticatorData),signature:b2u(r.signature)})})"
                ".then(function(x){if(x&&x.ok)location.reload();else if(x)m.textContent=x.err})}).catch(function(){m.textContent=F})}"
                "document.getElementById('pko').onclick=go;})();</script>" + self._reg_js(u["key"], "pka", "pkam", t["add"]))

    def page_block(self, u):
        """The card on the page: turn on / on + add another device. Only when the page has an https address."""
        if not self.rp()[0]:
            return ""
        t = self.t()
        with self.lock:
            creds = self.load()["creds"].get(u["id"], [])
        if creds:
            devs = ", ".join(escape(x.get("dev") or t["device"]) for x in creds)
            return (f'<h2>{escape(t["h"])}</h2><div class="card"><div class="muted" style="margin-bottom:10px">'
                    + escape(t["on"]).replace("{devs}", devs).replace("{m}", f"{self.idle:g}") + '</div>'
                    f'<button class="b p" id="pkon" style="width:100%">{escape(t["other"])}</button><div class="muted" id="pkonm" style="margin-top:8px"></div></div>'
                    + self._reg_js(u["key"], "pkon", "pkonm", t["other"]) +
                    "<script>(function(){var t=0;document.addEventListener('visibilitychange',function(){if(document.hidden)t=Date.now();"
                    "else if(t&&Date.now()-t>" + str(int(self.idle * 60000)) + ")location.reload()})})();</script>")   # back from the background after a pause → the lock
        return (f'<h2>{escape(t["h"])}</h2><div class="card"><div class="muted" style="margin-bottom:10px">{escape(t["off"])}</div>'
                f'<button class="b y" id="pkon" style="width:100%">{escape(t["turn_on"])}</button><div class="muted" id="pkonm" style="margin-top:8px"></div></div>'
                + self._reg_js(u["key"], "pkon", "pkonm", t["turn_on"]))
