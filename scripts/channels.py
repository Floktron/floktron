# -*- coding: utf-8 -*-
"""FLOKTRON · channels.py — each person chooses where tasks come: Telegram, their own page, or e-mail (+ push).

Off by default (config.yaml → channels.enabled). Without it, tasks go to Telegram exactly as before.
With it, every task from scripts/task_notice.py (mail, prospects, gateways…) goes to each person in channels.people
through the channel that person chose:
    telegram  the bot, as before (✅ / ⛔ buttons)
    web       the person's own page (/m) served by scripts/channels_web.py — add it to the phone home screen and it
              opens like an app; optional push (ntfy) rings the phone
    email     one summary letter with buttons; optional push
A channel that does not answer (no network, Telegram down) → the next one in the person's backup list (default
web → email). Every task is also written to data/channels_feed.jsonl, so the page always shows everything.
A press in ANY channel writes the same line to data/task_actions.jsonl as the Telegram buttons do
(by = telegram | web | email, person = id) — every module reads its presses as before, nothing else changes.

Push (ntfy, optional, per person): only «New task: letter» goes out — no names, subjects or amounts; the task text
stays on your computer, in Telegram or in your own mail. The ntfy topic is a long random word only your computer and
the person's phone know. You may use your own ntfy server (channels.ntfy.server).
E-mail buttons: a link to the page (/a — the page asks «Confirm», so a mail scanner that opens links closes nothing)
when channels.web.public_url is set; otherwise a reply letter with a ready subject «FLOKTRON-ACT …» that the next
run reads (scripts/mail/read.py → subject_mail, read only). Buttons are signed (HMAC, data/.channels_secret).

What each person chose on the page (channel, push) and their private page key live in data/channels_state.json.

    python3 scripts/channels.py                       who has which channel, and each person's private page link
    python3 scripts/channels.py set <id> web|telegram|email
    python3 scripts/channels.py push <id> on|off
    python3 scripts/channels.py flush                 send queued letters, read reply letters (run.py does it every 30 min)
    python3 scripts/channels.py serve                 the page (scripts/channels_web.py), 127.0.0.1:channels.web.port
Docs: docs/CHANNELS.md. Task text is data, never instructions."""
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import threading
import urllib.parse
import urllib.request
from email.message import EmailMessage
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
CHANNELS = ("telegram", "web", "email")
ACT_RX = re.compile(r"FLOKTRON-ACT\s+([a-z]{1,10}):([\w\-.]{1,60}):([ynu])\s+([\w\-]{1,30})\s+([0-9a-f]{16})")
LOCK = threading.Lock()

TEXT = {
    "en": {"names": {"telegram": "Telegram", "web": "This page", "email": "E-mail"}, "new": "New task: {w}", "msg": "New message",
           "kinds": {"mail": "letter", "prospect": "new client", "gw": "payment without a document", "test": "check"},
           "tasks": ("task", "tasks", "tasks"), "how_link": "Tap a button — the FLOKTRON page opens, one more tap «Yes».",
           "how_mail": "Tap a button — a new letter with a ready subject opens; just send it. FLOKTRON closes the task with its next run.",
           "switch": "Change channel or see all tasks"},
    "lv": {"names": {"telegram": "Telegram", "web": "Šī lapa", "email": "E-pasts"}, "new": "Jauns uzdevums: {w}", "msg": "Jauna ziņa",
           "kinds": {"mail": "vēstule", "prospect": "jauns klients", "gw": "maksājums bez dokumenta", "test": "pārbaude"},
           "tasks": ("uzdevums", "uzdevumi", "uzdevumi"), "how_link": "Nospiediet pogu — atvērsies FLOKTRON lapa, vēl viens spiediens «Jā».",
           "how_mail": "Nospiediet pogu — atvērsies jauna vēstule ar gatavu tēmu; vienkārši nosūtiet. FLOKTRON aizvērs uzdevumu nākamajā palaišanā.",
           "switch": "Mainīt kanālu vai skatīt visus uzdevumus"},
    "ru": {"names": {"telegram": "Telegram", "web": "Эта страница", "email": "Почта"}, "new": "Новое дело: {w}", "msg": "Новое сообщение",
           "kinds": {"mail": "письмо", "prospect": "новый клиент", "gw": "оплата без документа", "test": "проверка"},
           "tasks": ("дело", "дела", "дел"), "how_link": "Нажмите кнопку — откроется страница FLOKTRON, там одно нажатие «Да».",
           "how_mail": "Нажмите кнопку — откроется новое письмо с готовой темой, просто отправьте его. FLOKTRON закроет дело при следующем запуске.",
           "switch": "Сменить канал или открыть все дела"},
}


def T(lang):
    return TEXT.get(lang) or TEXT["en"]


def lang_of(cfg):
    return (cfg.get("company") or {}).get("language") or "en"


def plural(n, lang):
    one, few, many = T(lang)["tasks"]
    if lang == "ru":
        return one if n % 10 == 1 and n % 100 != 11 else few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many
    return one if n == 1 else few


def ccfg(cfg):
    c = dict(cfg.get("channels") or {})
    c.setdefault("people", {})
    c["web"] = {"port": 8765, "public_url": "", "lan": False, **(c.get("web") or {})}
    c["ntfy"] = {"server": "https://ntfy.sh", **(c.get("ntfy") or {})}
    return c


def enabled(cfg):
    return bool((cfg.get("channels") or {}).get("enabled"))


def data_dir(cfg):
    import task_notice
    return task_notice.data_dir(cfg)


def paths(cfg):
    import task_notice
    d = data_dir(cfg)
    return {"feed": os.path.join(d, "channels_feed.jsonl"), "queue": os.path.join(d, "channels_mail_queue.jsonl"),
            "state": os.path.join(d, "channels_state.json"), "secret": os.path.join(d, ".channels_secret"),
            "actions": task_notice.actions_path(cfg), "out": os.path.join(d, "channels_out"),
            "brief": os.path.join(d, "channels_brief.json")}


# ---------------------------------------------------------------- people = config + what they chose on the page
def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write_json(path, d):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def people(cfg):
    """{id: person} — config.yaml channels.people, plus the choice and page key from data/channels_state.json."""
    c = ccfg(cfg)
    p = paths(cfg)
    with LOCK:
        st = _read_json(p["state"])
        changed = False
        out = {}
        for pid, base in (c["people"] or {}).items():
            pid = str(pid)
            b = dict(base or {})
            s = st.setdefault(pid, {})
            if not s.get("key"):
                s["key"] = secrets.token_urlsafe(24)
                changed = True
            if not s.get("topic"):
                s["topic"] = "floktron-" + secrets.token_hex(12)
                changed = True
            ch = s.get("channel") or b.get("channel") or "telegram"
            out[pid] = {"id": pid, "name": b.get("name") or pid, "channel": ch if ch in CHANNELS else "telegram",
                        "backup": [x for x in (b.get("backup") or ["web", "email"]) if x in CHANNELS],
                        "email": b.get("email") or "", "push": bool(s.get("push", b.get("push", False))),
                        "tasks": b.get("tasks", True) is not False, "time": bool(b.get("time")), "manager": b.get("manager") is True,
                        "worktime_who": str(b.get("worktime_who") or pid), "key": s["key"], "topic": s["topic"]}
        if changed:
            _write_json(p["state"], st)
    return out


def by_key(cfg, key):
    for pid, u in people(cfg).items():
        if key and hmac.compare_digest(str(key), u["key"]):
            return u
    return None


def choose(cfg, pid, channel=None, push=None):
    """Switch a person's channel / push (from the page or the command line). → "" or an error."""
    u = people(cfg).get(pid)
    if not u:
        return f"no person «{pid}» in channels.people"
    if channel is not None:
        if channel not in CHANNELS:
            return "channel: telegram | web | email"
        if channel == "email" and not u["email"]:
            return "write this person's e-mail in channels.people first"
    p = paths(cfg)
    with LOCK:
        st = _read_json(p["state"])
        s = st.setdefault(pid, {})
        if channel is not None:
            s["channel"] = channel
        if push is not None:
            s["push"] = bool(push)
        _write_json(p["state"], st)
    return ""


# ---------------------------------------------------------------- signed buttons and presses
def _secret(cfg):
    path = paths(cfg)["secret"]
    try:
        with open(path, encoding="utf-8") as f:
            s = f.read().strip()
        if len(s) >= 32:
            return s.encode()
    except OSError:
        pass
    s = secrets.token_hex(32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return s.encode()


def sign(cfg, pid, kind, key, ans):
    return hmac.new(_secret(cfg), f"{pid}|{kind}|{key}|{ans}".encode(), hashlib.sha256).hexdigest()[:16]


def check_sig(cfg, pid, kind, key, ans, sig):
    return bool(sig) and hmac.compare_digest(sign(cfg, pid, kind, key, ans), str(sig))


def parse(data):
    """«fk:<kind>:<key>:<y|n>» → (kind, key, ans) or None."""
    p = str(data).split(":")
    if len(p) == 4 and p[0] == "fk" and p[3] in ("y", "n"):
        return p[1], p[2], p[3]
    return None


def flat(markup):
    """Telegram inline_keyboard → [(label, callback_data)]."""
    return [(b.get("text", ""), b.get("callback_data", "")) for row in (markup or []) for b in row]


def record(cfg, kind, key, ans, by, pid, comment="", **extra):
    a = {"ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "chat": by, "by": by, "person": pid,
         "kind": kind, "key": key, "ans": ans, "comment": str(comment)[:500]}
    a.update(extra)
    path = paths(cfg)["actions"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with LOCK, open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
    return a


def answered(cfg):
    """{(kind, key): last press} — the last press wins, «u» = undone."""
    out = {}
    try:
        with open(paths(cfg)["actions"], encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    a = json.loads(line)
                except ValueError:
                    continue
                if isinstance(a, dict) and a.get("kind") and a.get("key"):
                    k = (a["kind"], str(a["key"]))
                    if a.get("ans") == "u":
                        out.pop(k, None)
                    elif a.get("ans") in ("y", "n"):
                        out[k] = a
    except OSError:
        pass
    return out


def _append(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with LOCK, open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def feed(cfg, pid, days=14):
    """The person's messages of the last N days, newest first; each with closed = last press or None."""
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    ans = answered(cfg)
    items = []
    try:
        with open(paths(cfg)["feed"], encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    it = json.loads(line)
                except ValueError:
                    continue
                if it.get("person") != pid or str(it.get("ts", "")) < since:
                    continue
                b = [parse(d) for _, d in it.get("buttons") or []]
                b = [x for x in b if x]
                it["closed"] = ans.get((b[0][0], b[0][1])) if b else None
                items.append(it)
    except OSError:
        pass
    seen, out = set(), []
    for it in reversed(items):               # the same task sent twice → once
        k = tuple(it["buttons"][0]) if it.get("buttons") else it.get("id")
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


# ---------------------------------------------------------------- push (ntfy)
def push(cfg, u, word, outbox=None):
    if not u["push"]:
        return ""
    c = ccfg(cfg)
    url = c["ntfy"]["server"].rstrip("/") + "/" + u["topic"]
    L = T(lang_of(cfg))
    body = L["new"].format(w=word) if word else L["msg"]
    hdr = {"Title": "FLOKTRON", "Tags": "bell"}
    if c["web"].get("public_url"):
        hdr["Click"] = c["web"]["public_url"].rstrip("/") + "/m"
    if outbox:
        _append(os.path.join(outbox, "channels_push.jsonl"), {"url": url, "headers": hdr, "body": body})
        return ""
    try:
        req = urllib.request.Request(url, data=body.encode("utf-8"), headers=hdr, method="POST")
        urllib.request.urlopen(req, timeout=10).read()   # nosec B310 — https ntfy server from config
        return ""
    except Exception as e:  # noqa: BLE001
        return f"push: {str(e)[:60]}"


# ---------------------------------------------------------------- e-mail
def _btn(cfg, pid, label, data):
    b = parse(data)
    if not b:
        return ""
    kind, key, ans = b
    sig = sign(cfg, pid, kind, key, ans)
    pub = (ccfg(cfg)["web"].get("public_url") or "").rstrip("/")
    if pub:
        href = pub + "/a?" + urllib.parse.urlencode({"p": pid, "k": f"{kind}:{key}", "a": ans, "s": sig})
    else:
        to = (cfg.get("mail") or {}).get("reply_to") or (cfg.get("mail") or {}).get("user") or ""
        href = "mailto:%s?subject=%s" % (to, urllib.parse.quote(f"FLOKTRON-ACT {kind}:{key}:{ans} {pid} {sig}"))
    col = "#4A9928" if ans == "y" else "#717171"
    return (f'<a href="{escape(href, True)}" style="display:inline-block;padding:10px 16px;margin:4px 6px 4px 0;background:{col};'
            f'color:#fff;text-decoration:none;border-radius:6px;font-weight:bold;font-family:Arial">{escape(label)}</a>')


def letter_html(cfg, pid, items):
    L = T(lang_of(cfg))
    pub = (ccfg(cfg)["web"].get("public_url") or "").rstrip("/")
    rows = []
    for it in items:
        txt = escape(it["text"]).replace("\n", "<br>")
        btns = "".join(_btn(cfg, pid, lab, d) for lab, d in it.get("buttons") or [])
        rows.append('<div style="border:1px solid #e2e2e2;border-radius:8px;padding:12px 14px;margin:0 0 12px;background:#fff">'
                    f'<div style="font:15px/1.45 Arial;color:#1A365D">{txt}</div>'
                    + (f'<div style="margin-top:8px">{btns}</div>' if btns else "") + "</div>")
    foot = L["how_link"] if pub else L["how_mail"]
    if pub:
        foot += f' · <a href="{escape(pub)}/m" style="color:#8B5CF6">{L["switch"]}</a>'
    n = len(items)
    return ('<!DOCTYPE html><html><body style="margin:0;background:#f3f3f3"><div style="max-width:600px;margin:0 auto;padding:16px">'
            f'<div style="font:bold 18px Arial;color:#1A365D;margin:0 0 10px">FLOKTRON · {n} {plural(n, lang_of(cfg))}</div>'
            + "".join(rows) + f'<div style="font:12px/1.5 Arial;color:#717171;margin-top:10px">{foot}</div></div></body></html>')


def flush_mail(cfg, outbox=None):
    """Queued tasks → one summary letter per person. → letters sent."""
    p = paths(cfg)
    with LOCK:
        try:
            with open(p["queue"], encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            return 0
        open(p["queue"], "w").close()
    by = {}
    for line in lines:
        try:
            it = json.loads(line)
        except ValueError:
            continue
        by.setdefault(it.get("person"), []).append(it)
    ppl, mail, sent = people(cfg), cfg.get("mail") or {}, 0
    for pid, items in by.items():
        u = ppl.get(pid)
        if not u or not u["email"]:
            continue
        first = items[0]["text"].split("\n")[0][:70]
        n = len(items)
        msg = EmailMessage()
        msg["From"] = mail.get("from") or mail.get("user") or ""
        msg["To"] = u["email"]
        msg["Subject"] = f"FLOKTRON · {first}" if n == 1 else f"FLOKTRON · {n} {plural(n, lang_of(cfg))}: {first}"
        if mail.get("reply_to"):
            msg["Reply-To"] = mail["reply_to"]
        msg.set_content("\n\n".join(i["text"] for i in items))
        msg.add_alternative(letter_html(cfg, pid, items), subtype="html")
        if outbox:
            _append(os.path.join(outbox, "channels_mail.jsonl"), {"to": u["email"], "subject": msg["Subject"],
                                                                  "html": letter_html(cfg, pid, items)})
            sent += 1
            continue
        try:
            from mail.send import Sender
            with Sender(mail) as s:
                s.send(msg)
            sent += 1
        except Exception as e:  # noqa: BLE001 — not sent → back to the queue, next run tries again
            for it in items:
                _append(p["queue"], it)
            print(f"channels: letter to {pid} not sent ({str(e)[:80]})")
    return sent


def read_replies(cfg, letters=None):
    """Reply letters «FLOKTRON-ACT kind:key:ans person sig» → presses (by=email). letters = [dict(mid, subject, from)]
    for tests; otherwise scripts/mail/read.py → subject_mail (read only). Each letter counts once."""
    p = paths(cfg)
    st = _read_json(p["state"])
    done = set(st.get("_mail_done", []))
    if letters is None:
        if not any(u["channel"] == "email" for u in people(cfg).values()):
            return 0
        try:
            from mail.read import subject_mail
            letters = list(subject_mail(cfg.get("mail") or {}, "FLOKTRON-ACT", days=3))
        except Exception as e:  # noqa: BLE001
            print(f"channels: reply letters not read ({str(e)[:80]})")
            return 0
    ppl, n = people(cfg), 0
    for m in letters:
        mid = m.get("mid") or m.get("subject")
        if mid in done:
            continue
        done.add(mid)
        r = ACT_RX.search(m.get("subject") or "")
        if not r:
            continue
        kind, key, ans, pid, sig = r.groups()
        u = ppl.get(pid)
        if not u or not check_sig(cfg, pid, kind, key, ans, sig):
            continue
        if u["email"] and u["email"].lower() not in str(m.get("from") or "").lower():
            continue
        record(cfg, kind, key, ans, "email", pid)
        n += 1
    with LOCK:
        st = _read_json(p["state"])
        st["_mail_done"] = sorted(done)[-500:]
        _write_json(p["state"], st)
    return n


# ---------------------------------------------------------------- the one entry point
def deliver(cfg, text, markup, tg_send, outbox=None):
    """One task (text + Telegram inline_keyboard or None) to every person with tasks, each in their channel.
    tg_send(text, markup) → "" or error (task_notice sends to telegram.manager_chat_ids). → "" or the errors."""
    btns = [list(b) for b in flat(markup)]
    b0 = parse(btns[0][1]) if btns else None
    L = T(lang_of(cfg))
    word = L["kinds"].get(b0[0], b0[0]) if b0 else ""
    ppl = [u for u in people(cfg).values() if u["tasks"]]
    if not ppl:
        return tg_send(text, markup)
    tg_done, errs = None, []
    p = paths(cfg)
    for u in ppl:
        _append(p["feed"], {"id": secrets.token_hex(5), "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "person": u["id"], "text": text[:3900], "buttons": btns})
        order = [u["channel"]] + [x for x in u["backup"] if x != u["channel"]]
        ok = False
        for ch in order:
            if ch == "telegram":
                if tg_done is None:
                    tg_done = tg_send(text, markup)
                if not tg_done:
                    ok = True
                    break
                errs.append(f"{u['id']}: {tg_done}")
            elif ch == "web":
                push(cfg, u, word, outbox)
                ok = True
                break
            elif ch == "email" and u["email"]:
                _append(p["queue"], {"person": u["id"], "text": text[:3900], "buttons": btns})
                push(cfg, u, word, outbox)
                ok = True
                break
        if not ok:
            errs.append(f"{u['id']}: no channel answered")
    if outbox:
        flush_mail(cfg, outbox)
    return "; ".join(e for e in errs if "no channel" in e)


def page_link(cfg, u):
    base = (ccfg(cfg)["web"].get("public_url") or f"http://127.0.0.1:{ccfg(cfg)['web']['port']}").rstrip("/")
    return f"{base}/m?k={u['key']}"


def load_cfg(path=None):
    import yaml
    path = path or os.path.join(ROOT, "config", "config.yaml")
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg["_path"] = path
    return cfg


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    cfgp = None
    if "--config" in a:
        i = a.index("--config")
        cfgp = a[i + 1]
        del a[i:i + 2]
    cfg = load_cfg(cfgp)
    if not enabled(cfg):
        print("channels: off (config.yaml → channels.enabled: false) — tasks go to Telegram as before")
        return 0
    cmd = a[0] if a else ""
    if cmd == "set":
        print(choose(cfg, a[1], channel=a[2]) or "✅ done")
    elif cmd == "push":
        print(choose(cfg, a[1], push=a[2] == "on") or "✅ done")
    elif cmd == "flush":
        print(f"channels: letters {flush_mail(cfg)}, reply presses {read_replies(cfg)}")
        return 0
    elif cmd == "serve":
        import channels_web
        return channels_web.serve(cfg)
    names = T(lang_of(cfg))["names"]
    for pid, u in people(cfg).items():
        print(f"{pid:10} {u['name']:22} {names[u['channel']]:10} push: {'on' if u['push'] else 'off'}  e-mail: {u['email'] or '—'}")
        print(f"{'':10} page: {page_link(cfg, u)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
