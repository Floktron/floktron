# -*- coding: utf-8 -*-
"""FLOKTRON · channels_web.py — each person's own page with their tasks (docs/CHANNELS.md). Started by
`python3 scripts/channels.py serve`; listens on 127.0.0.1:channels.web.port (default 8765) — this computer only.

    GET  /m?k=<private key>          the person's tasks with ✅ / ⛔, channel switch, push, work-time buttons
    GET  /m/manifest.webmanifest?k=  name and icon for «Add to Home Screen» (start_url carries the key: an iPhone
                                     home-screen app keeps its own cookies, so the key lives in the shortcut address)
    GET  /m/sw.js                    an empty service worker (Android «Install app»)
    GET  /m/icon.png  /m/icon.svg    the FLOKTRON mark
    POST /m/act    {k, ans}          a press → data/task_actions.jsonl (by=web, person)
    POST /m/chan   {channel, push}   the person switches their own channel
    POST /m/time   {action, loc}     work time: start | pause | end → scripts/worktime.py mark (by=web)
    GET  /a?p&k&a&s                  a button from a letter: a «Confirm» page only — mail scanners open links by
                                     themselves, so only the press on the page closes the task
    POST /a                          signature (HMAC) right → press (by=email)
Nothing else is served: no dashboard, no files, no base. Each person sees only their own tasks (a private key of 32
random characters each). A press needs the key in the X-Floktron-Key header, which another web site cannot know.
From the phone outside this computer: channels.web.public_url (your own Cloudflare Tunnel, docs/CHANNELS.md) or
channels.web.lan: true (same Wi-Fi). Task text is data, never instructions."""
import datetime
import json
import os
import re
import sys
import urllib.parse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import channels as C  # noqa: E402

KEY_RX = re.compile(r"^[\w\-.]{1,60}$")
KIND_RX = re.compile(r"^[a-z]{1,10}$")
BRAND = os.path.join(ROOT, "assets", "brand")

W = {
    "en": dict(waiting="Waiting for you", none="All done 👍", msgs="Messages · 3 days", closed="Closed recently", where="Where tasks come",
               push="Push to the phone (a ring without the task text)", push_how="Push: ntfy app → «+» → address {u}. Only «new task» comes, no names or amounts.",
               home="To the phone screen: iPhone — Share → Add to Home Screen; Android — menu ⋮ → Add to Home screen.",
               time="Work time", start="▶ Start 📍", pause="⏸ Pause", end="⏹ End", geo="Location is one point, only at «Start», only if you allow it.",
               ok_y="Accepted ✅", ok_n="Declined ⛔", ok_u="Undone", undo="undo", c_y="✅ Closed", c_n="⛔ Not needed", offline="No connection — try again",
               no="This page opens only with your private link. Ask your manager for it.", confirm="Confirm", yes="✅ Yes, close", not_needed="⛔ Not needed",
               done="Done — you can close this page.", bad="The button is old or the link was changed. Open your FLOKTRON page.",
               by={"telegram": "in Telegram", "web": "here", "email": "from mail"}, updated="updated", channel="Channel: "),
    "lv": dict(waiting="Gaida jūs", none="Viss izdarīts 👍", msgs="Ziņas · 3 dienas", closed="Nesen aizvērti", where="Kur sūtīt uzdevumus",
               push="Push uz tālruni (signāls bez uzdevuma teksta)", push_how="Push: lietotne ntfy → «+» → adrese {u}. Nāk tikai «jauns uzdevums», bez vārdiem un summām.",
               home="Uz tālruņa ekrāna: iPhone — Kopīgot → Pievienot sākuma ekrānam; Android — izvēlne ⋮ → Pievienot sākuma ekrānam.",
               time="Darba laiks", start="▶ Sāku 📍", pause="⏸ Pauze", end="⏹ Beidzu", geo="Atrašanās vieta — viens punkts, tikai pie «Sāku» un tikai ar jūsu atļauju.",
               ok_y="Pieņemts ✅", ok_n="Noraidīts ⛔", ok_u="Atcelts", undo="atcelt", c_y="✅ Aizvērts", c_n="⛔ Nav vajadzīgs", offline="Nav savienojuma — mēģiniet vēlreiz",
               no="Šī lapa atveras tikai ar jūsu personīgo saiti. Palūdziet to vadītājam.", confirm="Apstiprināt", yes="✅ Jā, aizvērt", not_needed="⛔ Nav vajadzīgs",
               done="Gatavs — lapu var aizvērt.", bad="Poga ir veca vai saite mainīta. Atveriet savu FLOKTRON lapu.",
               by={"telegram": "Telegram", "web": "šeit", "email": "no e-pasta"}, updated="atjaunots", channel="Kanāls: "),
    "ru": dict(waiting="Ждут ответа", none="Всё решено 👍", msgs="Сообщения за 3 дня", closed="Закрыто недавно", where="Куда присылать дела",
               push="Push на телефон (звонок без текста дела)", push_how="Push: приложение ntfy → «+» → адрес {u}. Приходит только «новое дело», без имён и сумм.",
               home="На экран телефона: iPhone — «Поделиться» → «На экран Домой»; Android — меню ⋮ → «Добавить на главный экран».",
               time="Рабочее время", start="▶ Начал 📍", pause="⏸ Пауза", end="⏹ Закончил", geo="Место берётся одной точкой, только при «Начал» и только если вы разрешите.",
               ok_y="Принято ✅", ok_n="Отклонено ⛔", ok_u="Отменено", undo="отменить", c_y="✅ Закрыто", c_n="⛔ Не нужно", offline="Нет связи — попробуйте ещё раз",
               no="Эта страница открывается только по личной ссылке. Попросите её у управляющего.", confirm="Подтвердите", yes="✅ Да, закрыть", not_needed="⛔ Не нужно",
               done="Готово — страницу можно закрыть.", bad="Кнопка устарела или ссылка изменена. Откройте свою страницу FLOKTRON.",
               by={"telegram": "в Telegram", "web": "здесь", "email": "из почты"}, updated="обновлено", channel="Канал: "),
}

# --- rich text: a plain message → readable blocks (sections, news items, short links). Text is data: everything is escaped.
_URL = re.compile(r"https?://[^\s<>\"']+")
_DOTS = {"🔴": "#d64545", "🟠": "#e8862e", "🟡": "#e0b422", "🟢": "#4A9928", "🔵": "#2563c9", "🟣": "#8B5CF6", "⚪": "#9aa6b8", "⚫": "#717171"}
_HOSTS = {"news.google.com": "Google News", "t.me": "Telegram", "youtu.be": "YouTube", "youtube.com": "YouTube"}


def _link(url):
    url = url.rstrip(".,;:!?)»”")
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if not host:
        return escape(url)
    return f'<a class="lnk" href="{escape(url, True)}" target="_blank" rel="noopener noreferrer">{escape(_HOSTS.get(host, host))} ↗</a>'


def _inline(s):
    out, pos = [], 0
    for m in _URL.finditer(s):
        out.append(escape(s[pos:m.start()])); out.append(_link(m.group(0))); pos = m.end()
    return "".join(out) + escape(s[pos:])


def _flag(code):
    return "".join(chr(0x1F1E6 + ord(ch) - 65) for ch in code) if len(code) == 2 and code.isascii() and code.isalpha() and code.isupper() else ""


def rich(text):
    lines = [x.strip() for x in str(text or "").replace("\r", "").split("\n")]
    out, item, first = [], None, True

    def close():
        nonlocal item
        if item:
            links = f'<div class="lk">{"".join(item["links"])}</div>' if item["links"] else ""
            out.append(f'<div class="it"{item["style"]}>{item["mark"]}<div class="ib">{item["head"]}<div class="tt">{item["body"]}</div>{links}</div></div>')
            item = None
    for ln in lines:
        if not ln:
            continue
        if _URL.fullmatch(ln):                                   # a link on its own line belongs to the item above
            if item:
                item["links"].append(_link(ln))
            else:
                out.append(f'<div class="lk">{_link(ln)}</div>')
            continue
        m = re.match(r"^(\d{1,2})[.)]\s+(.*)$", ln)
        b = re.match(r"^[•·\-–—*]\s+(.*)$", ln)
        if m or b:
            close()
            rest, mark, style, head, src = (m.group(2) if m else b.group(1)), "", "", "", ""
            if m:
                mark = f'<span class="n">{m.group(1)}</span>'
                t = re.match(r"^\[([A-Za-z]{2,3})\]\s*(.*)$", rest)
                tag = ""
                if t:
                    tag, rest = f'<span class="tag">{_flag(t.group(1).upper())} {escape(t.group(1).upper())}</span>', t.group(2)
                src, sep, title = rest.partition(" · ")
                if sep and len(src) <= 40 and title:
                    head, rest = f'<div class="src">{tag}{escape(src)}</div>', title
                elif tag:
                    head = f'<div class="src">{tag}</div>'
            else:
                if rest[:1] in _DOTS:
                    style, rest = f' style="border-left-color:{_DOTS[rest[0]]}"', rest[1:].lstrip("️ ").strip()
                mark = '<span class="n d"></span>'
                topic, sep, title = rest.partition(": ")
                if sep and len(topic) <= 60 and title and "http" not in topic:
                    head, rest = f'<div class="src"><span class="tag">{escape(topic)}</span></div>', title
            src2 = ""
            k = rest.rfind(" - ")
            if k > 8 and 0 < len(rest) - k - 3 <= 40 and "http" not in rest[k:]:
                tail, rest = rest[k + 3:], rest[:k]
                known = (m and src.lower().startswith(tail.lower().rstrip("…. "))) if m else False   # «Title - Sourc» cut by the feed
                src2 = "" if known else f' <span class="by">{escape(tail)}</span>'
            item = {"mark": mark, "style": style, "head": head, "body": _inline(rest) + src2, "links": []}
            continue
        close()
        if first:
            out.append(f'<div class="ttl">{_inline(ln)}</div>')
        elif ln.endswith(":") and len(ln) <= 60:
            out.append(f'<div class="sec">{escape(ln[:-1])}</div>')
        else:
            out.append(f'<p>{_inline(ln)}</p>')
        first = False
    close()
    return "".join(out)


RICH_CSS = """.t{word-wrap:break-word;overflow-wrap:anywhere}.t p{margin:6px 0}.ttl{font-weight:700;font-size:17px;margin:0 0 6px}
.sec{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--acc);border-top:1px solid var(--line);margin:14px 0 8px;padding-top:12px}
.it{display:flex;gap:10px;align-items:flex-start;border-left:3px solid var(--line);background:rgba(128,140,170,.09);border-radius:0 10px 10px 0;padding:9px 10px;margin:0 0 8px}
.it .n{flex:none;width:24px;height:24px;border-radius:50%;background:var(--acc);color:#fff;font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center}
.it .n.d{display:none}.ib{min-width:0;flex:1}.src{font-size:12px;color:var(--mut);margin:0 0 3px}.tag{display:inline-block;font-weight:700;color:var(--ink);background:rgba(128,140,170,.2);border-radius:6px;padding:1px 7px;margin-right:6px}
.tt{font-weight:600;line-height:1.35}.by{font-weight:400;color:var(--mut);font-size:13px;white-space:nowrap}.by:before{content:"· "}
.lk{margin-top:7px;display:flex;gap:6px;flex-wrap:wrap}.lnk{display:inline-block;font-size:13px;font-weight:600;color:var(--acc);text-decoration:none;border:1px solid var(--acc);border-radius:999px;padding:3px 11px}"""

CSS = """:root{--bg:#f3f3f3;--card:#fff;--ink:#1A365D;--mut:#717171;--ok:#4A9928;--no:#717171;--acc:#8B5CF6;--line:#e3e3e3}
@media (prefers-color-scheme:dark){:root{--bg:#0f1724;--card:#17223a;--ink:#e8eef8;--mut:#9aa6b8;--line:#2a3756}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,system-ui,Segoe UI,Arial,sans-serif;padding:0 16px 40px}
header{display:flex;align-items:center;gap:10px;padding:16px 0 8px}header img{width:34px;height:34px;border-radius:8px}h1{font-size:20px;margin:0}
h2{font-size:15px;margin:22px 0 8px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:0 0 10px}
.muted{color:var(--mut);font-size:13px}.big{font-size:22px}.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.b{flex:1;min-width:120px;border:0;border-radius:10px;padding:12px 10px;font-size:16px;font-weight:600;color:#fff;cursor:pointer}
.b.y{background:var(--ok)}.b.n{background:var(--no)}.b.w{background:#1A365D}.b.p{background:#2563c9}
.seg{display:flex;border:1px solid var(--line);border-radius:10px;overflow:hidden}.seg button{flex:1;border:0;background:var(--card);color:var(--ink);padding:11px 4px;font-size:15px}
.seg button.on{background:#1A365D;color:#fff;font-weight:600}.closed{opacity:.6}.undo{background:none;border:0;color:var(--acc);font-size:14px;padding:0;margin-top:6px}
details summary{cursor:pointer;color:var(--mut);margin:18px 0 8px}code{font-size:13px;word-break:break-all}label{display:flex;gap:10px;align-items:center;margin-top:12px}
#msg{position:fixed;left:16px;right:16px;bottom:16px;background:#1A365D;color:#fff;border-radius:10px;padding:12px 14px;display:none}""" + RICH_CSS


def L(cfg):
    return W.get(C.lang_of(cfg)) or W["en"]


def shell(cfg, title, inner, head=""):
    return (f'<!DOCTYPE html><html lang="{escape(C.lang_of(cfg))}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">'
            f'<title>FLOKTRON · {escape(title)}</title><link rel="icon" href="/m/icon.svg"><link rel="apple-touch-icon" href="/m/icon.png">'
            f'{head}<style>{CSS}</style></head><body><header><img src="/m/icon.png" alt=""><h1>FLOKTRON</h1></header>{inner}'
            '<div id="msg"></div></body></html>')


def card(cfg, it):
    t = L(cfg)
    b = it.get("buttons") or []
    ts = str(it.get("ts", ""))
    txt = f'<div class="t">{rich(it["text"])}</div><div class="muted">{escape(ts[8:10])}.{escape(ts[5:7])} {escape(ts[11:16])}</div>'
    p0 = C.parse(b[0][1]) if b else None
    if not p0:
        return f'<div class="card">{txt}</div>'
    k = escape(f"{p0[0]}:{p0[1]}", True)
    cl = it.get("closed")
    if cl:
        return (f'<div class="card closed" data-k="{k}">{txt}<div class="muted">{t["c_y"] if cl["ans"] == "y" else t["c_n"]} · '
                f'{escape(str(cl.get("ts", ""))[11:16])} {escape(t["by"].get(cl.get("by"), ""))}</div><button class="undo" data-a="u">{t["undo"]}</button></div>')
    btns = "".join(f'<button class="b {C.parse(d)[2]}" data-a="{C.parse(d)[2]}">{escape(lab)}</button>' for lab, d in b if C.parse(d))
    return f'<div class="card" data-k="{k}">{txt}<div class="row">{btns}</div></div>'


def page(cfg, u):
    t = L(cfg)
    items = C.feed(cfg, u["id"])
    since3 = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    open_ = [i for i in items if i.get("buttons") and not i.get("closed")]
    info = [i for i in items if not i.get("buttons") and str(i.get("ts", "")) >= since3]
    done = [i for i in items if i.get("closed")][:15]
    names = C.T(C.lang_of(cfg))["names"]
    seg = "".join(f'<button data-ch="{ch}" class="{"on" if u["channel"] == ch else ""}">{escape(names[ch])}</button>' for ch in C.CHANNELS)
    ntfy = C.ccfg(cfg)["ntfy"]["server"].rstrip("/") + "/" + u["topic"]
    tm = ""
    if u["time"] and (cfg.get("worktime") or {}).get("enabled"):
        tm = (f'<h2>{t["time"]}</h2><div class="card"><div class="row" style="margin-top:0"><button class="b y" data-t="start">{t["start"]}</button>'
              f'<button class="b p" data-t="pause">{t["pause"]}</button><button class="b w" data-t="end">{t["end"]}</button></div>'
              f'<div class="muted" id="tmsg" style="margin-top:8px">{t["geo"]}</div></div>')
    inner = (f'<div class="muted">{escape(u["name"])} · {t["updated"]} {datetime.datetime.now():%H:%M}</div>' + tm
             + f'<h2>{t["waiting"]} · {len(open_)}</h2>' + ("".join(card(cfg, i) for i in open_) or f'<div class="card muted">{t["none"]}</div>')
             + (f'<h2>{t["msgs"]}</h2>' + "".join(card(cfg, i) for i in info[:10]) if info else "")
             + (f'<details><summary>{t["closed"]} · {len(done)}</summary>' + "".join(card(cfg, i) for i in done) + "</details>" if done else "")
             + f'<h2>{t["where"]}</h2><div class="card"><div class="seg" id="seg">{seg}</div>'
             f'<label><input type="checkbox" id="push" {"checked" if u["push"] else ""}> {t["push"]}</label>'
             f'<div class="muted" style="margin-top:8px">{t["push_how"].format(u="<code>" + escape(ntfy) + "</code>")}</div>'
             f'<div class="muted" style="margin-top:8px">{t["home"]}</div></div>')
    js = ("<script>(function(){var K=%s,T=%s;function msg(s){var m=document.getElementById('msg');m.textContent=s;m.style.display='block';setTimeout(function(){m.style.display='none'},2500)}"
          "function post(p,d){return fetch(p,{method:'POST',headers:{'Content-Type':'application/json','X-Floktron-Key':K},body:JSON.stringify(d)}).then(function(r){return r.json()})}"
          "document.querySelectorAll('.card[data-k] button[data-a]').forEach(function(b){b.onclick=function(){var c=b.closest('.card'),a=b.getAttribute('data-a');b.disabled=true;"
          "post('/m/act',{k:c.getAttribute('data-k'),ans:a}).then(function(){msg(a==='y'?T.ok_y:a==='n'?T.ok_n:T.ok_u);setTimeout(function(){location.reload()},700)}).catch(function(){b.disabled=false;msg(T.offline)})}});"
          "document.querySelectorAll('#seg button').forEach(function(b){b.onclick=function(){post('/m/chan',{channel:b.getAttribute('data-ch')}).then(function(r){if(r.ok){msg(T.channel+b.textContent);setTimeout(function(){location.reload()},700)}else msg(r.err)})}});"
          "var p=document.getElementById('push');p.onchange=function(){post('/m/chan',{push:p.checked}).then(function(){msg(p.checked?'Push ✓':'Push ✗')})};"
          "document.querySelectorAll('button[data-t]').forEach(function(b){b.onclick=function(){var a=b.getAttribute('data-t');b.disabled=true;"
          "function go(l){post('/m/time',{action:a,loc:l}).then(function(r){document.getElementById('tmsg').textContent=r.msg;msg(r.msg);b.disabled=false}).catch(function(){b.disabled=false;msg(T.offline)})}"
          "if(a==='start'&&navigator.geolocation){navigator.geolocation.getCurrentPosition(function(q){go({lat:q.coords.latitude,lon:q.coords.longitude,acc:q.coords.accuracy})},function(){go(null)},{timeout:8000,maximumAge:60000})}else go(null)}});"
          "if('serviceWorker' in navigator){navigator.serviceWorker.register('/m/sw.js',{scope:'/m'}).catch(function(){})}"
          "setInterval(function(){if(!document.hidden)location.reload()},90000)})();</script>") % (
        json.dumps(u["key"]), json.dumps({k: t[k] for k in ("ok_y", "ok_n", "ok_u", "offline", "channel")}, ensure_ascii=False).replace("<", "\\u003c"))
    head = (f'<link rel="manifest" href="/m/manifest.webmanifest?k={escape(u["key"], True)}"><meta name="theme-color" content="#1A365D">'
            '<meta name="apple-mobile-web-app-capable" content="yes">')
    return shell(cfg, t["waiting"], inner + js, head)


def time_mark(cfg, u, action, loc):
    import worktime
    location = None
    if action == "start" and isinstance(loc, dict):
        try:
            location = {"latitude": float(loc["lat"]), "longitude": float(loc["lon"]), "horizontal_accuracy": float(loc.get("acc") or 0)}
        except (KeyError, TypeError, ValueError):
            location = None
    text, _ = worktime.mark(cfg, worktime.events_path(cfg), u["worktime_who"], u["name"], action, location=location,
                            lang=C.lang_of(cfg), by="web")
    return text


def host_ok(cfg, host):
    host = (host or "").split(":")[0].lower()
    if host in ("127.0.0.1", "localhost"):
        return True
    pub = urllib.parse.urlsplit(C.ccfg(cfg)["web"].get("public_url") or "").hostname
    if pub and host == pub.lower():
        return True
    return bool(C.ccfg(cfg)["web"].get("lan")) and re.match(r"^(192\.168|10|172\.(1[6-9]|2\d|3[01]))\.\d+\.\d+$", host) is not None


def make_handler(cfg):
    class H(BaseHTTPRequestHandler):
        server_version = "FLOKTRON-channels"

        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
            b = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            for k, v in [("Content-Type", ctype), ("Content-Length", str(len(b))), ("Cache-Control", "no-store"),
                         ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"), ("X-Frame-Options", "DENY")] + list((extra or {}).items()):
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(b)

        def _q(self):
            return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).items()}

        def _body(self, limit=4000):
            n = min(int(self.headers.get("Content-Length") or 0), limit)
            return self.rfile.read(n).decode("utf-8", "replace")

        def _who(self):
            key = self.headers.get("X-Floktron-Key") or self._q().get("k") or ""
            if not key:
                m = re.search(r"(?:^|;\s*)fk_k=([\w\-]+)", self.headers.get("Cookie") or "")
                key = m.group(1) if m else ""
            return C.by_key(cfg, key)

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

        def _route(self, method):
            path = urllib.parse.urlsplit(self.path).path
            if not host_ok(cfg, self.headers.get("Host")):
                return self._send(403, "forbidden", "text/plain")
            t = L(cfg)
            if path == "/m/sw.js":
                return self._send(200, "self.addEventListener('fetch',function(){});", "application/javascript")
            if path in ("/m/icon.png", "/m/icon.svg"):
                f = os.path.join(BRAND, "floktron-512.png" if path.endswith(".png") else "favicon.svg")
                if os.path.isfile(f):
                    with open(f, "rb") as fh:
                        return self._send(200, fh.read(), "image/png" if path.endswith(".png") else "image/svg+xml")
                return self._send(404, "not found", "text/plain")
            if path == "/a":
                return self._a(method, t)
            if not (path == "/m" or path.startswith("/m/")):
                return self._send(404, "not found", "text/plain")
            u = self._who()
            if not u:
                return self._send(403, shell(cfg, "—", f"<p>{t['no']}</p>"))
            if method == "GET" and path == "/m/manifest.webmanifest":
                return self._send(200, json.dumps({"name": "FLOKTRON", "short_name": "FLOKTRON", "start_url": f"/m?k={u['key']}", "scope": "/m",
                                                   "display": "standalone", "background_color": "#f3f3f3", "theme_color": "#1A365D",
                                                   "icons": [{"src": "/m/icon.png", "sizes": "512x512", "type": "image/png"}]}), "application/manifest+json")
            if method == "GET" and path == "/m":
                sec = "; Secure" if (C.ccfg(cfg)["web"].get("public_url") or "").startswith("https") else ""
                return self._send(200, page(cfg, u), extra={"Set-Cookie": f"fk_k={u['key']}; Path=/m; Max-Age=31536000; HttpOnly; SameSite=Strict{sec}"})
            if method != "POST" or not self.headers.get("X-Floktron-Key"):
                return self._send(403, "forbidden", "text/plain")
            try:
                d = json.loads(self._body() or "{}")
            except ValueError:
                return self._send(400, "bad request", "text/plain")
            if path == "/m/act":
                kind, _, key = str(d.get("k", "")).partition(":")
                ans = str(d.get("ans", ""))
                if not KIND_RX.match(kind) or not KEY_RX.match(key) or ans not in ("y", "n", "u"):
                    return self._send(400, "bad request", "text/plain")
                C.record(cfg, kind, key, ans, "web", u["id"])
                return self._send(200, json.dumps({"ok": True}), "application/json")
            if path == "/m/chan":
                ch = d.get("channel")
                err = C.choose(cfg, u["id"], ch if ch in C.CHANNELS else None, None if d.get("push") is None else bool(d.get("push")))
                return self._send(200 if not err else 400, json.dumps({"ok": not err, "err": err}, ensure_ascii=False), "application/json")
            if path == "/m/time":
                act = d.get("action")
                if act not in ("start", "pause", "end") or not u["time"] or not (cfg.get("worktime") or {}).get("enabled"):
                    return self._send(400, "bad request", "text/plain")
                return self._send(200, json.dumps({"ok": True, "msg": time_mark(cfg, u, act, d.get("loc"))}, ensure_ascii=False), "application/json")
            return self._send(404, "not found", "text/plain")

        def _a(self, method, t):
            f = self._q() if method == "GET" else {k: v[0] for k, v in urllib.parse.parse_qs(self._body(2000)).items()}
            pid, ks, ans, sig = f.get("p", ""), f.get("k", ""), f.get("a", ""), f.get("s", "")
            kind, _, key = ks.partition(":")
            ok = (KIND_RX.match(kind) and KEY_RX.match(key or "-") and ans in ("y", "n") and pid in C.people(cfg)
                  and C.check_sig(cfg, pid, kind, key, ans, sig))
            if not ok:
                return self._send(403, shell(cfg, "—", f"<p>{t['bad']}</p>"))
            if method == "GET":
                it = next((x for x in C.feed(cfg, pid) if x.get("buttons") and (C.parse(x["buttons"][0][1]) or ())[:2] == (kind, key)), None)
                txt = f'<div class="card"><div class="t">{rich(it["text"])}</div></div>' if it else ""
                hidden = "".join(f'<input type="hidden" name="{n}" value="{escape(v, True)}">' for n, v in (("p", pid), ("k", ks), ("a", ans), ("s", sig)))
                form = f'<form method="post" action="/a">{hidden}<button class="b {ans}" type="submit">{t["yes"] if ans == "y" else t["not_needed"]}</button></form>'
                return self._send(200, shell(cfg, t["confirm"], txt + form))
            C.record(cfg, kind, key, ans, "email", pid)
            return self._send(200, shell(cfg, t["done"], f'<p class="big">{t["c_y"] if ans == "y" else t["c_n"]}</p><p class="muted">{t["done"]}</p>'))
    return H


def server(cfg, port=None):
    w = C.ccfg(cfg)["web"]
    return ThreadingHTTPServer(("0.0.0.0" if w.get("lan") else "127.0.0.1", int(port if port is not None else w["port"])), make_handler(cfg))  # nosec B104 — only with channels.web.lan


def serve(cfg):
    srv = server(cfg)
    print(f"FLOKTRON channels page: http://127.0.0.1:{srv.server_address[1]}/m  (each person — their own link: python3 scripts/channels.py)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
