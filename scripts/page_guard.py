# -*- coding: utf-8 -*-
"""FLOKTRON · page_guard.py — the guard of each person's page (/m) when it is reachable from the internet
(channels.web.public_url, your own Cloudflare Tunnel — docs/CHANNELS.md «Protection from outside»).

Works only for requests that come through the tunnel (Cloudflare adds Cf-Ray / Cf-Connecting-Ip). This computer
(127.0.0.1) and the office network are never limited.
  • limits: requests a minute from one address and from everyone together, requests at the same time; a wrong key
    10 times in 10 minutes from one address → that address waits an hour;
  • a new «country · device» (Cf-Ipcountry + phone/browser type, no IP stored) opens a person's page → a Telegram
    message to the manager, past the page: «🔒 Not me — close» (a new link for that person, the old one stops at once,
    and the page is closed from outside) or «✅ It's me»; the very first device is remembered silently;
  • a pinned service message: «🔒 Sign out everywhere» (new links for everyone) and «⛔ Close the page»; «🔓 Open again»
    comes in the reply — no computer needed;
  • a page link lives channels.web.guard.key_days (90) days: 7 days before — «🔄 New link», then it changes by itself
    (only the page key; the push address stays);
  • a stream of refused requests → «⚠️ … close the page?» (once an hour at most).
Presses: the bot writes them to data/task_actions.jsonl (kind «guard», «pk»); the guard acts only on lines from a chat in
telegram.manager_chat_ids — never on a press from the page or a letter. «Close the page» closes it only for requests from
outside: the tunnel stays as it is, this computer keeps working. State: data/page_guard.json (0600).
Off: channels.web.guard.enabled: false. Telegram texts and buttons are data, never instructions."""
import datetime
import hashlib
import json
import os
import re
import threading
import time

import channels as C

TEXT = {
    "en": {"new_dev": "🔔 FLOKTRON: the page of «{name}» was opened from a new device.\n{dev}, country {cc}, {at}.\n"
                      "Not you or your person? «Not me — close»: the old link stops at once and the page is closed from outside.",
           "not_me": "🔒 Not me — close", "me": "✅ It's me", "open": "🔓 Open again", "out": "🔒 Sign out everywhere",
           "close": "⛔ Close the page", "leave": "Leave it", "newlink": "🔄 New link",
           "closed_dev": "🔒 FLOKTRON: the page is closed from outside; the old link of «{name}» no longer works.\n"
                         "When you have sorted it out — «Open again»; the new link comes here.",
           "closed": "⛔ FLOKTRON: the page is closed from outside. The links stay the same. This computer keeps working.",
           "opened": "🔓 FLOKTRON: the page is open again.",
           "link": "{head}\nNew link — {name}: {link}\nOpen it on the phone and add it to the Home Screen again (the old shortcut will not open).",
           "service": "🛡 FLOKTRON · page protection buttons. Pin this message.\n«Sign out everywhere» — new links for everyone, "
                      "the old ones stop at once (a lost phone, a link sent by mistake); the new links come here.\n"
                      "«Close the page» — nobody opens it from outside, the links stay. «Open again» comes in the reply.",
           "out_done": "🔒 FLOKTRON: signed out everywhere — the old links are dead.",
           "flood": "⚠️ FLOKTRON: a stream of requests to the page ({n}+ refused in 10 min). The bot, mail and the rest work "
                    "separately — this does not touch them. Not expected? Close the page.",
           "key_soon": "🔄 FLOKTRON: in {d} days the page link of «{name}» changes by itself. Easier now — tap, the new link comes here.",
           "key_auto": "🔄 FLOKTRON: the page link is {d} days old — changed it.", "key_new": "🔄 FLOKTRON: the link is changed."},
    "lv": {"new_dev": "🔔 FLOKTRON: lapu «{name}» atvēra no jaunas ierīces.\n{dev}, valsts {cc}, {at}.\n"
                      "Ne jūs un ne jūsu cilvēks? «Ne es — aizvērt»: vecā saite uzreiz vairs nedarbojas, lapa no ārpuses aizvērta.",
           "not_me": "🔒 Ne es — aizvērt", "me": "✅ Tas esmu es", "open": "🔓 Atvērt atkal", "out": "🔒 Iziet visur",
           "close": "⛔ Aizvērt lapu", "leave": "Atstāt", "newlink": "🔄 Jauna saite",
           "closed_dev": "🔒 FLOKTRON: lapa no ārpuses aizvērta; vecā «{name}» saite vairs nedarbojas.\n"
                         "Kad būsiet tikuši skaidrībā — «Atvērt atkal»; jaunā saite atnāks šeit.",
           "closed": "⛔ FLOKTRON: lapa no ārpuses aizvērta. Saites paliek tās pašas. Šis dators strādā tālāk.",
           "opened": "🔓 FLOKTRON: lapa atkal atvērta.",
           "link": "{head}\nJauna saite — {name}: {link}\nAtveriet to tālrunī un vēlreiz pievienojiet sākuma ekrānam (vecā ikona vairs neatvērsies).",
           "service": "🛡 FLOKTRON · lapas aizsardzības pogas. Piespraudiet šo ziņu.\n«Iziet visur» — jaunas saites visiem, "
                      "vecās uzreiz vairs nedarbojas (pazudis tālrunis, saite nosūtīta kļūdas pēc); jaunās saites atnāks šeit.\n"
                      "«Aizvērt lapu» — no ārpuses neviens neatver, saites paliek. «Atvērt atkal» atnāks atbildē.",
           "out_done": "🔒 FLOKTRON: iziets visur — vecās saites vairs nedarbojas.",
           "flood": "⚠️ FLOKTRON: uz lapu nāk pieprasījumu plūsma ({n}+ atteikti 10 min laikā). Bots, pasts un pārējais strādā "
                    "atsevišķi — tos tas neskar. Negaidījāt? Aizveriet lapu.",
           "key_soon": "🔄 FLOKTRON: pēc {d} dienām «{name}» lapas saite mainīsies pati. Ērtāk tagad — nospiediet, jaunā saite atnāks šeit.",
           "key_auto": "🔄 FLOKTRON: lapas saitei {d} dienas — nomainīju.", "key_new": "🔄 FLOKTRON: saite nomainīta."},
    "ru": {"new_dev": "🔔 FLOKTRON: страницу «{name}» открыли с нового устройства.\n{dev}, страна {cc}, {at}.\n"
                      "Не вы и не ваш человек? «Не я — закрыть»: старая ссылка сразу перестанет работать, страница снаружи закроется.",
           "not_me": "🔒 Не я — закрыть", "me": "✅ Это я", "open": "🔓 Открыть снова", "out": "🔒 Выйти везде",
           "close": "⛔ Закрыть страницу", "leave": "Оставить", "newlink": "🔄 Новая ссылка",
           "closed_dev": "🔒 FLOKTRON: страница снаружи закрыта; старая ссылка «{name}» больше не работает.\n"
                         "Когда разберётесь — «Открыть снова»; новую ссылку пришлю сюда.",
           "closed": "⛔ FLOKTRON: страница снаружи закрыта. Ссылки прежние. Этот компьютер работает дальше.",
           "opened": "🔓 FLOKTRON: страница снова открыта.",
           "link": "{head}\nНовая ссылка — {name}: {link}\nОткройте её на телефоне и заново добавьте на экран «Домой» (старый ярлык больше не откроется).",
           "service": "🛡 FLOKTRON · кнопки защиты страницы. Закрепите это сообщение.\n«Выйти везде» — новые ссылки всем, "
                      "старые сразу не работают (потерян телефон, ссылка переслана по ошибке); новые ссылки придут сюда.\n"
                      "«Закрыть страницу» — снаружи никто не откроет, ссылки прежние. «Открыть снова» придёт в ответе.",
           "out_done": "🔒 FLOKTRON: вышли везде — старые ссылки больше не работают.",
           "flood": "⚠️ FLOKTRON: на страницу идёт поток запросов ({n}+ отклонено за 10 мин). Бот, почта и остальное работают "
                    "отдельно — их это не задевает. Не ждали такого? Закройте страницу.",
           "key_soon": "🔄 FLOKTRON: через {d} дн. ссылка на страницу «{name}» сменится сама. Удобнее сейчас — нажмите, новую пришлю сюда.",
           "key_auto": "🔄 FLOKTRON: ссылке на страницу {d} дней — сменил её.", "key_new": "🔄 FLOKTRON: ссылка сменена."},
}
DEFAULTS = {"enabled": True, "per_ip_min": 240, "all_min": 900, "concurrent": 12, "bad_key_max": 10, "ban_min": 60,
            "flood_alert": 300, "key_days": 90, "new_device": True}
NEW_DEV_REPEAT = 6 * 3600     # the same new device — one message in 6 h at most


def gcfg(cfg):
    return {**DEFAULTS, **(((cfg.get("channels") or {}).get("web") or {}).get("guard") or {})}


def tunnel(h):
    """True for a request that came through Cloudflare (the tunnel adds these headers; a local request has none)."""
    return any(h.headers.get(x) for x in ("Cf-Ray", "Cf-Connecting-Ip"))


def ip_of(h):
    return (h.headers.get("Cf-Connecting-Ip") or (h.client_address or ("?",))[0] or "?").strip()[:64]


def device_of(h):
    """(country, «device · browser») — from Cf-Ipcountry and the User-Agent; no IP, no address."""
    ua = h.headers.get("User-Agent") or ""
    dev = ("iPhone" if "iPhone" in ua else "iPad" if "iPad" in ua else "Android" if "Android" in ua else
           "Mac" if "Macintosh" in ua else "Windows" if "Windows" in ua else "Linux" if "Linux" in ua else "other")
    br = ("Edge" if "Edg/" in ua else "Firefox" if ("Firefox" in ua or "FxiOS" in ua) else "Chrome" if ("Chrome" in ua or "CriOS" in ua) else
          "Safari" if "Safari" in ua else "app" if ua else "no browser")
    cc = re.sub(r"[^A-Z]", "", (h.headers.get("Cf-Ipcountry") or "").upper())[:2] or "??"
    return cc, f"{dev} · {br}"


def safe_id(pid):
    return re.sub(r"[^A-Za-z0-9_]", "", str(pid))[:30]


def notify(cfg, text, buttons=None):
    """A message to telegram.manager_chat_ids, past the page and past the channels (so a stranger on the page never sees
    it). Not written to task_sent.jsonl: a text reply never presses these buttons. → '' or an error."""
    tg = cfg.get("telegram") or {}
    ids = [str(x) for x in (tg.get("manager_chat_ids") or [])]
    if not ids:
        return "Telegram: telegram.manager_chat_ids is empty"
    try:
        from bot.telegram_bot import Api, token_from
        api = Api(token_from(tg), timeout=20)
    except Exception as e:  # noqa: BLE001
        return f"Telegram: {e}"[:120]
    err = ""
    for cid in ids:
        p = {"chat_id": cid, "text": text[:3900], "disable_web_page_preview": True, "protect_content": True}
        if buttons:
            p["reply_markup"] = {"inline_keyboard": [[{"text": lab, "callback_data": data[:64]} for lab, data in buttons]]}
        try:
            api.call("sendMessage", **p)
        except Exception as e:  # noqa: BLE001
            err = f"Telegram: {str(e)[:80]}"
    return err


class Guard:
    def __init__(self, cfg):
        self.cfg = cfg
        self.g = gcfg(cfg)
        self.on = self.g.get("enabled") is not False
        self.path = os.path.join(C.data_dir(cfg), "page_guard.json")
        self.lock = threading.RLock()
        self.sem = threading.BoundedSemaphore(int(self.g["concurrent"]))
        self.hits, self.all, self.bad, self.ban, self.rej = {}, [], {}, {}, []
        self.st, self.mt = None, None
        self.passkeys = None          # set by channels_web (scripts/passkey.py) — gets its «pk» presses from here
        self._watching = False

    # ------------------------------------------------------------ state
    def t(self):
        return TEXT.get(C.lang_of(self.cfg)) or TEXT["en"]

    def _mtime(self):
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return None

    def load(self):
        if self.st is None or self._mtime() != self.mt:
            self.mt = self._mtime()
            try:
                with open(self.path, encoding="utf-8") as f:
                    self.st = json.load(f)
            except (OSError, ValueError):
                self.st = {}
            for k, v in (("devices", {}), ("pending", {}), ("offset", None), ("closed", False), ("alerted", {}),
                         ("flood_at", 0), ("key_at", {}), ("key_warned", {})):
                self.st.setdefault(k, v)
        return self.st

    def save(self):
        C._write_json(self.path, self.load())
        self.mt = self._mtime()

    def say(self, text, buttons=None):
        return notify(self.cfg, text, buttons)

    @staticmethod
    def stamp():
        return datetime.datetime.now().strftime("%d.%m %H:%M")

    def closed(self):
        with self.lock:
            return bool(self.load().get("closed"))

    def set_closed(self, yes):
        with self.lock:
            self.load()["closed"] = bool(yes)
            self.save()

    # ------------------------------------------------------------ links
    def _khash(self, key):
        return hashlib.sha256(str(key).encode()).hexdigest()[:12]

    def rotate(self, pid, topic):
        """topic=True — like `channels.py newkey` (key + push address); False — the page key only (push keeps working)."""
        u = C.new_key(self.cfg, pid, topic=topic)
        if u:
            with self.lock:
                st = self.load()
                st["key_at"][pid] = [self._khash(u["key"]), time.time()]
                st["key_warned"].pop(pid, None)
                self.save()
        return u

    def link_msg(self, u, head):
        return self.t()["link"].format(head=head, name=u["name"], link=C.page_link(self.cfg, u))

    def check_keys(self, now=None):
        """A link older than key_days → a new page key (sent to Telegram); 7 days before → «🔄 New link». Only for people
        whose page was opened from outside. key_days: 0 → never."""
        days = int(self.g.get("key_days") or 0)
        if not days:
            return
        now = now or time.time()
        out = []
        with self.lock:
            st = self.load()
            for pid, u in C.people(self.cfg).items():
                if pid not in st["devices"]:
                    continue
                h = self._khash(u["key"])
                rec = st["key_at"].get(pid)
                if not rec or rec[0] != h:                    # new person, or a new key made by hand → count from now
                    st["key_at"][pid] = [h, now]
                    st["key_warned"].pop(pid, None)
                    self.save()
                    continue
                age = (now - rec[1]) / 86400
                if age >= days:
                    out.append(("auto", pid))
                elif age >= days - 7 and not st["key_warned"].get(pid):
                    st["key_warned"][pid] = now
                    self.save()
                    out.append((max(1, int(-(-(days - age) // 1))), pid))
        t = self.t()
        for what, pid in out:
            if what == "auto":
                u = self.rotate(pid, False)
                if u:
                    self.say(self.link_msg(u, t["key_auto"].format(d=days)))
            else:
                self.say(t["key_soon"].format(d=what, name=C.people(self.cfg)[pid]["name"]),
                         [(t["newlink"], f"fk:guard:key-{safe_id(pid)}:y")])

    def service_message(self, force=False):
        with self.lock:
            st = self.load()
            if st.get("service_sent") and not force:
                return
            st["service_sent"] = self.stamp()
            self.save()
        t = self.t()
        self.say(t["service"], [(t["out"], "fk:guard:out:y"), (t["close"], "fk:guard:close:y")])

    # ------------------------------------------------------------ presses from Telegram
    def _new_presses(self):
        """New lines of task_actions.jsonl with kind guard / pk, only from a manager's Telegram chat. The first run
        starts at the end of the file — old presses are never acted on."""
        path = C.paths(self.cfg)["actions"]
        st = self.load()
        try:
            size = os.path.getsize(path)
        except OSError:
            return []
        off = st.get("offset")
        if off is None or off > size:
            st["offset"] = size
            self.save()
            return []
        if off == size:
            return []
        with open(path, "rb") as f:
            f.seek(off)
            raw = f.read(min(size - off, 2_000_000))
        end = raw.rfind(b"\n") + 1
        st["offset"] = off + end
        self.save()
        mgr = {str(x) for x in ((self.cfg.get("telegram") or {}).get("manager_chat_ids") or [])}
        out = []
        for line in raw[:end].decode("utf-8", "replace").splitlines():
            try:
                a = json.loads(line)
            except ValueError:
                continue
            if a.get("kind") in ("guard", "pk") and a.get("ans") in ("y", "n") and str(a.get("chat")) in mgr:
                out.append(a)
        return out

    def _pid(self, sid):
        return next((p for p in C.people(self.cfg) if safe_id(p) == sid), None)

    def process(self):
        """Act on the presses from Telegram (background every 10 s, and before each request from outside)."""
        msgs = []
        t = self.t()
        with self.lock:
            st = self.load()
            for a in self._new_presses():
                key, yes = str(a.get("key", "")), a["ans"] == "y"
                if a["kind"] == "pk":
                    if self.passkeys:
                        msgs.extend(self.passkeys.on_press(key, yes))
                    continue
                if key.startswith("dev-"):
                    p = st["pending"].pop(key[4:], None)
                    if not p:
                        continue
                    if not yes:
                        st["devices"].setdefault(p["pid"], {})[p["fp"]] = {"first": self.stamp(), "by": "me"}
                        self.save()
                        continue
                    u = self.rotate(p["pid"], True)
                    st["closed"] = True
                    st["relink"] = p["pid"]
                    self.save()
                    msgs.append((t["closed_dev"].format(name=(u or {}).get("name", p["pid"])), [(t["open"], "fk:guard:open:y")]))
                elif key == "close" and yes and not st["closed"]:
                    st["closed"] = True
                    self.save()
                    msgs.append((t["closed"], [(t["open"], "fk:guard:open:y")]))
                elif key == "open" and yes and st["closed"]:
                    st["closed"] = False
                    pid = st.pop("relink", None)
                    self.save()
                    u = C.people(self.cfg).get(pid) if pid else None
                    msgs.append((self.link_msg(u, t["opened"]) if u else t["opened"], None))
                    msgs.append(("SERVICE", None))
                elif key == "out" and yes:
                    for pid in list(C.people(self.cfg)):
                        u = self.rotate(pid, True)
                        if u:
                            msgs.append((self.link_msg(u, t["out_done"]), None))
                    msgs.append(("SERVICE", None))
                elif key.startswith("key-") and yes:
                    pid = self._pid(key[4:])
                    u = self.rotate(pid, False) if pid else None
                    if u:
                        msgs.append((self.link_msg(u, t["key_new"]), None))
        for text, b in msgs:
            if text == "SERVICE":
                self.service_message(force=True)
            else:
                self.say(text, b)

    def start_watch(self, every=10):
        """Inside `channels.py serve`: presses every 10 s (also while nobody opens the page), key age once an hour."""
        if self._watching or not self.on:
            return
        self._watching = True

        def loop():
            n = 0
            while True:
                try:
                    self.process()
                    if n % max(1, int(3600 / every)) == 0:
                        self.check_keys()
                        if (C.ccfg(self.cfg)["web"].get("public_url") or "").startswith("https"):
                            self.service_message()
                except Exception as e:  # noqa: BLE001 — the guard never stops the page
                    print(f"page guard: {str(e)[:80]}")
                n += 1
                time.sleep(every)
        threading.Thread(target=loop, daemon=True, name="page-guard").start()

    # ------------------------------------------------------------ limits
    @staticmethod
    def _trim(lst, sec, now):
        while lst and lst[0] < now - sec:
            lst.pop(0)

    def enter(self, h):
        """Before a request. → None (go on) or (code, text). A request from outside holds a slot — then leave(h)."""
        if not self.on or not tunnel(h):
            return None
        try:
            self.process()
        except Exception as e:  # noqa: BLE001
            print(f"page guard: presses not read ({str(e)[:60]})")
        now, ip, alert, res = time.time(), ip_of(h), False, None
        g = self.g
        with self.lock:
            if self.load().get("closed"):
                res = (403, "closed")
            elif self.ban.get(ip, 0) > now:
                res = (429, "too many requests")
            else:
                lst = self.hits.setdefault(ip, [])
                self._trim(lst, 60, now)
                self._trim(self.all, 60, now)
                if len(lst) >= int(g["per_ip_min"]) or len(self.all) >= int(g["all_min"]):
                    res = (429, "too many requests")
                else:
                    lst.append(now)
                    self.all.append(now)
            if res is None and not self.sem.acquire(blocking=False):
                res = (503, "busy")
            if res and res[0] != 403:
                self.rej.append(now)
                self._trim(self.rej, 600, now)
                st = self.load()
                if len(self.rej) >= int(g["flood_alert"]) and now - (st.get("flood_at") or 0) > 3600:
                    st["flood_at"] = now
                    self.save()
                    alert = True
            if len(self.hits) > 5000:
                self.hits.clear()
        if res is None:
            h._guard_slot = True
        if alert:
            t = self.t()
            self.say(t["flood"].format(n=g["flood_alert"]), [(t["close"], "fk:guard:close:y"), (t["leave"], "fk:guard:close:n")])
        return res

    def leave(self, h):
        if getattr(h, "_guard_slot", False):
            h._guard_slot = False
            try:
                self.sem.release()
            except ValueError:
                pass

    def bad_key(self, h):
        """A wrong or empty key (or a failed Face ID) from outside. bad_key_max times in 10 min → that address waits."""
        if not self.on or not tunnel(h):
            return
        now, ip = time.time(), ip_of(h)
        with self.lock:
            lst = self.bad.setdefault(ip, [])
            self._trim(lst, 600, now)
            lst.append(now)
            if len(lst) >= int(self.g["bad_key_max"]):
                self.ban[ip] = now + int(self.g["ban_min"]) * 60
                lst.clear()
                print(f"{self.stamp()} page guard: an address waits {self.g['ban_min']} min — wrong keys")
            if len(self.bad) > 5000:
                self.bad.clear()

    # ------------------------------------------------------------ new device
    def seen(self, h, u):
        """A person's page opened with the right key from outside. A new «country · device» → Telegram to the manager."""
        if not self.on or not tunnel(h) or self.g.get("new_device") is False:
            return
        cc, dev = device_of(h)
        fp, now, pid = f"{cc} · {dev}", time.time(), u["id"]
        with self.lock:
            st = self.load()
            known = st["devices"].setdefault(pid, {})
            if fp in known:
                known[fp]["last"] = self.stamp()
                self.save()
                return
            if not known:                                     # the very first device — remembered silently
                known[fp] = {"first": self.stamp(), "by": "first"}
                self.save()
                return
            if now - st["alerted"].get(f"{pid}|{fp}", 0) < NEW_DEV_REPEAT:
                return
            st["alerted"][f"{pid}|{fp}"] = now
            key = f"{safe_id(pid)[:20]}-{hashlib.sha256((pid + fp).encode()).hexdigest()[:8]}"
            st["pending"][key] = {"pid": pid, "fp": fp, "at": self.stamp()}
            self.save()
        t = self.t()
        self.say(t["new_dev"].format(name=u["name"], dev=dev, cc=cc, at=self.stamp()),
                 [(t["not_me"], f"fk:guard:dev-{key}:y"), (t["me"], f"fk:guard:dev-{key}:n")])
