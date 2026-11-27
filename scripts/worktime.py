# -*- coding: utf-8 -*-
"""FLOKTRON · worktime.py — work time: the team marks start / pause / end in Telegram, the manager sees the hours.

How it works (docs/WORKTIME.md):
  1. A team member taps «▶ Start» in the work chat with the bot. With worktime.geo on, Telegram sends ONE location
     point at that moment (the phone asks first). No tracking during the day, no photos, no biometrics.
  2. «⏸ Pause» / «▶ Back» for a break, «⏹ End» at the end of the day.
  3. At worktime.remind_at the bot asks whoever has not ended: «Still at work?» — no answer = the day is flagged
     «no end mark», hours are NOT made up. Only the manager can correct a day, always with a reason (kept in the log).
  4. The dashboard shows who is at work now, today's and this month's hours, and what needs a look.
     Once a month: data/worktime_<YYYY-MM>.xlsx for the accountant (hours, overtime, night, weekend, holidays).

Every mark is one line in data/worktime.jsonl (append-only; corrections are new lines, nothing is rewritten).

    python3 scripts/worktime.py status                     # who is at work now
    python3 scripts/worktime.py month [--month 2026-11]    # → data/worktime_2026-11.xlsx
    python3 scripts/worktime.py remind                     # ask open days (scheduler at remind_at)
    python3 scripts/worktime.py fix --who "Anna" --date 2026-11-26 --end 17:30 --why "forgot to tap"
Network: none here; reminders go through the bot's Api (scripts/bot/telegram_bot.py).
"""
import argparse
import datetime
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
EVENTS = ("start", "pause", "back", "end", "fix")
FMT = "%Y-%m-%d %H:%M"

TEXT = {
    "en": dict(start="▶ Start", pause="⏸ Pause", back="▶ Back", end="⏹ End",
               started="✅ Work started · {t}{site}", paused="⏸ Pause · {t}", backed="▶ Back at work · {t}",
               ended="⏹ Day ended · {t} · {h} today", already="ℹ️ Already at work since {t}.", not_started="ℹ️ No start mark today — tap «▶ Start» first.",
               on_site=" · {site} ✓", off_site=" · {d} m from {site}", no_geo=" · no location",
               ask_geo="Tap «▶ Start» — Telegram will ask once to share your location at this moment (only this point is kept).",
               remind="⏰ Still at work? Started {t}, {h} so far.", still="▶ Still working", stop_now="⏹ End now",
               keep="👍 OK, the day stays open.", mine="⏱ Today {h} · this week {w} · this month {m}",
               who_head="👷 At work now", nobody="Nobody is at work now.", forwarded="⚠️ A forwarded location is not accepted — tap «▶ Start».",
               title="Work time", k_now="at work now", k_today="hours today", k_month="hours this month", k_flags="to check",
               since="since {t}", paused_s="on pause since {t}", done_s="{a}–{b}", absent="no mark today", none="No work-time marks yet. "
               "The team taps «▶ Start» in the bot (docs/WORKTIME.md).", month_head="This month", days="days", hours="hours",
               over="overtime", night="night", weekend="weekend/holiday", flag_noend="no end mark {d}", flag_far="started {dist} m from {site} ({d})",
               flag_nogeo="started without location ({d})", flag_fix="corrected by manager {d}: {why}", flag_long="{h} in one day ({d})"),
    "ru": dict(start="▶ Начал работу", pause="⏸ Пауза", back="▶ Продолжил", end="⏹ Закончил",
               started="✅ Начало работы · {t}{site}", paused="⏸ Пауза · {t}", backed="▶ Снова на работе · {t}",
               ended="⏹ День закончен · {t} · сегодня {h}", already="ℹ️ Ты уже на работе с {t}.", not_started="ℹ️ Сегодня нет отметки начала — сначала «▶ Начал работу».",
               on_site=" · {site} ✓", off_site=" · {d} м от «{site}»", no_geo=" · без места",
               ask_geo="Нажми «▶ Начал работу» — Telegram один раз спросит разрешение отправить место в эту минуту (хранится только эта точка).",
               remind="⏰ Ты ещё на работе? Начало {t}, уже {h}.", still="▶ Ещё работаю", stop_now="⏹ Закончил сейчас",
               keep="👍 Хорошо, день остаётся открытым.", mine="⏱ Сегодня {h} · неделя {w} · месяц {m}",
               who_head="👷 Сейчас на работе", nobody="Сейчас на работе никого.", forwarded="⚠️ Пересланное место не принимается — нажми «▶ Начал работу».",
               title="Учёт рабочего времени", k_now="сейчас на работе", k_today="часов сегодня", k_month="часов за месяц", k_flags="проверить",
               since="с {t}", paused_s="пауза с {t}", done_s="{a}–{b}", absent="сегодня не отмечался", none="Отметок пока нет. "
               "Сотрудники нажимают «▶ Начал работу» в боте (docs/WORKTIME.md).", month_head="За месяц", days="дней", hours="часов",
               over="сверхурочно", night="ночью", weekend="выходные/праздники", flag_noend="нет отметки ухода {d}", flag_far="начал в {dist} м от «{site}» ({d})",
               flag_nogeo="начал без места ({d})", flag_fix="исправлено управляющим {d}: {why}", flag_long="{h} за один день ({d})"),
    "lv": dict(start="▶ Sāku darbu", pause="⏸ Pauze", back="▶ Turpinu", end="⏹ Beidzu",
               started="✅ Darba sākums · {t}{site}", paused="⏸ Pauze · {t}", backed="▶ Atkal darbā · {t}",
               ended="⏹ Diena beigta · {t} · šodien {h}", already="ℹ️ Tu jau esi darbā kopš {t}.", not_started="ℹ️ Šodien nav sākuma atzīmes — vispirms «▶ Sāku darbu».",
               on_site=" · {site} ✓", off_site=" · {d} m no «{site}»", no_geo=" · bez vietas",
               ask_geo="Spied «▶ Sāku darbu» — Telegram vienreiz pajautās atļauju nosūtīt atrašanās vietu šajā brīdī (glabā tikai šo punktu).",
               remind="⏰ Vēl esi darbā? Sākums {t}, jau {h}.", still="▶ Vēl strādāju", stop_now="⏹ Beidzu tagad",
               keep="👍 Labi, diena paliek atvērta.", mine="⏱ Šodien {h} · nedēļā {w} · mēnesī {m}",
               who_head="👷 Tagad darbā", nobody="Tagad darbā neviena nav.", forwarded="⚠️ Pārsūtīta vieta netiek pieņemta — spied «▶ Sāku darbu».",
               title="Darba laika uzskaite", k_now="tagad darbā", k_today="stundas šodien", k_month="stundas mēnesī", k_flags="pārbaudīt",
               since="kopš {t}", paused_s="pauze kopš {t}", done_s="{a}–{b}", absent="šodien nav atzīmējies", none="Atzīmju vēl nav. "
               "Darbinieki spiež «▶ Sāku darbu» botā (docs/WORKTIME.md).", month_head="Mēnesī", days="dienas", hours="stundas",
               over="virsstundas", night="naktī", weekend="brīvdienas/svētki", flag_noend="nav beigu atzīmes {d}", flag_far="sāka {dist} m no «{site}» ({d})",
               flag_nogeo="sāka bez vietas ({d})", flag_fix="labojis vadītājs {d}: {why}", flag_long="{h} vienā dienā ({d})"),
}


def texts(lang):
    return TEXT.get(lang) or TEXT["en"]


def wcfg(cfg):
    w = dict(cfg.get("worktime") or {})
    w.setdefault("day_hours", 8)
    w.setdefault("week_hours", 40)
    w.setdefault("remind_at", "20:00")
    w.setdefault("night", ["22:00", "06:00"])
    w.setdefault("radius_m", 300)
    return w


def events_path(cfg, data=None):
    w = cfg.get("worktime") or {}
    return os.path.expanduser(w.get("file") or os.path.join(data or DATA, "worktime.jsonl"))


UNITS = {"en": ("h", "min"), "ru": ("ч", "мин"), "lv": ("st.", "min")}
_LANG = ["en"]   # set by collect()/mark() for the texts they build


def hm(minutes, lang=None):
    h, m = UNITS.get(lang or _LANG[0], UNITS["en"])
    minutes = int(round(minutes))
    return f"{minutes // 60} {h} {minutes % 60:02d} {m}" if minutes >= 60 else f"{minutes} {m}"


def hdec(minutes):
    return round(minutes / 60, 2)


def hnum(minutes, lang=None):
    """Hours for people: one decimal, comma in ru/lv (194,4); 0 → «—»."""
    if not minutes:
        return "—"
    s = f"{minutes / 60:.1f}"
    return s.replace(".", ",") if (lang or _LANG[0]) in ("ru", "lv", "de", "lt", "et") else s


# ---------------------------------------------------------------- location
def distance_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return int(2 * r * math.asin(math.sqrt(a)))


def nearest_site(w, lat, lon):
    """(site name, distance m, inside radius) — or ("", None, None) without sites in config."""
    best = None
    for s in w.get("sites") or []:
        try:
            d = distance_m(float(lat), float(lon), float(s["lat"]), float(s["lon"]))
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or d < best[1]:
            best = (str(s.get("name") or "?"), d, d <= float(s.get("radius_m") or w.get("radius_m") or 300))
    return best or ("", None, None)


# ---------------------------------------------------------------- the log
def clean(s, n=120):
    return re.sub(r"[\x00-\x1f]", " ", str(s or "")).strip()[:n]


def add(path, who, name, ev, ts=None, lat=None, lon=None, site="", dist=None, by="bot", **extra):
    """Append one mark. ts = 'YYYY-MM-DD HH:MM' (default now). Returns the record."""
    if ev not in EVENTS:
        raise ValueError(ev)
    rec = {"ts": ts or datetime.datetime.now().strftime(FMT), "who": str(who), "name": clean(name, 60), "ev": ev, "by": by}
    if lat is not None and lon is not None:
        rec.update(lat=round(float(lat), 5), lon=round(float(lon), 5))   # ~1 m — enough, no more precision than needed
    if site:
        rec["site"] = clean(site, 60)
    if dist is not None:
        rec["dist"] = int(dist)
    for k, v in extra.items():
        if v not in (None, ""):
            rec[k] = clean(v, 200) if isinstance(v, str) else v
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read(path):
    out = []
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
                datetime.datetime.strptime(r["ts"], FMT)
            except (ValueError, KeyError, TypeError):
                continue
            if r.get("ev") in EVENTS and r.get("who"):
                out.append(r)
    out.sort(key=lambda r: r["ts"])
    return out


# ---------------------------------------------------------------- days
def _t(s):
    return datetime.datetime.strptime(s, FMT)


def apply_fixes(evs):
    """A manager fix (ev=fix, date, start/end, why) replaces that person's start or end mark of that day."""
    fixes = [e for e in evs if e["ev"] == "fix"]
    rest = [e for e in evs if e["ev"] != "fix"]
    for fx in fixes:
        d = fx.get("date") or fx["ts"][:10]
        for part in ("start", "end"):
            hhmm = fx.get(part)
            if not hhmm:
                continue
            same = [e for e in rest if e["who"] == fx["who"] and e["ts"][:10] == d and e["ev"] == part]
            ts = f"{d} {hhmm}"
            if same:
                (same[0] if part == "start" else same[-1]).update(ts=ts, fixed=fx.get("why", ""))
            else:
                rest.append({"ts": ts, "who": fx["who"], "name": fx.get("name", ""), "ev": part, "by": "manager", "fixed": fx.get("why", "")})
    rest.sort(key=lambda r: r["ts"])
    return rest, fixes


def night_minutes(a, b, night):
    """Minutes of [a, b) that fall in the night window (e.g. 22:00–06:00)."""
    n0, n1 = (datetime.datetime.strptime(x, "%H:%M").time() for x in night)
    total, t = 0, a
    while t < b:
        nt = t.time()
        inside = (nt >= n0 or nt < n1) if n0 > n1 else (n0 <= nt < n1)
        total += inside
        t += datetime.timedelta(minutes=1)
    return total


MAX_SHIFT_H = 20   # a start without an end for longer than this is a «no end mark» day, never counted


def sessions(evs):
    """Marks of one person in time order → shifts [{start, marks, end}]; a night shift may end the next day."""
    out, cur = [], None
    for e in evs:
        if e["ev"] == "start":
            if cur:
                out.append(cur)          # a new start while one is open: the open one had no end
            cur = {"start": e, "marks": [], "end": None}
        elif cur:
            if (_t(e["ts"]) - _t(cur["start"]["ts"])).total_seconds() > MAX_SHIFT_H * 3600:
                out.append(cur)
                cur = None
                continue
            if e["ev"] == "end":
                cur["end"] = e
                out.append(cur)
                cur = None
            else:
                cur["marks"].append(e)
    if cur:
        out.append(cur)
    return out


def days(evs, now=None, w=None, holidays=()):
    """Marks → one row per shift (the day = the day of its start): start, end, pause, worked minutes, flags."""
    w = w or wcfg({})
    now = now or datetime.datetime.now()
    evs, fixes = apply_fixes(list(evs))
    per = {}
    for e in evs:
        per.setdefault(e["who"], []).append(e)
    rows = []
    for who, es in per.items():
        name = next((e.get("name") for e in reversed(es) if e.get("name")), who)
        for sh in sessions(es):
            start, end = sh["start"], sh["end"]
            d = start["ts"][:10]
            t0 = _t(start["ts"])
            alive = end is None and (now - t0).total_seconds() <= MAX_SHIFT_H * 3600
            stop = _t(end["ts"]) if end else (now if alive else None)
            pause, p0, worked, nightm, seg0 = 0, None, 0, 0, t0
            for e in sh["marks"]:
                if e["ev"] == "pause" and p0 is None:
                    p0 = _t(e["ts"])
                    worked += (p0 - seg0).total_seconds() / 60
                    nightm += night_minutes(seg0, p0, w["night"])
                elif e["ev"] == "back" and p0 is not None:
                    pause += (_t(e["ts"]) - p0).total_seconds() / 60
                    p0, seg0 = None, _t(e["ts"])
            if stop and p0 is None:
                worked += max(0, (stop - seg0).total_seconds() / 60)
                nightm += night_minutes(seg0, stop, w["night"])
            elif stop and p0 is not None:
                pause += (stop - p0).total_seconds() / 60
            state = "done" if end else ("pause" if p0 is not None else "work") if alive else "noend"
            if state == "noend":
                worked, nightm = 0, 0          # no end mark → hours are not made up; the manager fixes the day
            flags = []
            if state == "noend":
                flags.append(("noend", {}))
            if start.get("dist") is not None and start.get("site") and start.get("inside") is False:
                flags.append(("far", {"dist": start["dist"], "site": start["site"]}))
            if w.get("geo") and start.get("lat") is None and start.get("by") == "bot":
                flags.append(("nogeo", {}))
            for f in fixes:
                if f["who"] == who and (f.get("date") or f["ts"][:10]) == d:
                    flags.append(("fix", {"why": f.get("why", "")}))
            if worked > 12 * 60:
                flags.append(("long", {"h": hm(worked)}))
            wk = datetime.date.fromisoformat(d).weekday() >= 5 or d in holidays
            rows.append(dict(who=who, name=name, date=d, start=start["ts"][11:], end=end["ts"][11:] if end else "",
                             end_day=end["ts"][:10] if end else "", site=start.get("site", ""), inside=start.get("inside"),
                             dist=start.get("dist"), pause=int(pause), worked=int(worked), night=int(nightm), weekend=wk,
                             state=state, over=int(max(0, worked - w["day_hours"] * 60)), flags=flags,
                             since=(p0.strftime("%H:%M") if p0 else start["ts"][11:])))
    rows.sort(key=lambda r: (r["date"], r["start"], r["who"]))
    return rows


def flag_text(f, row, L):
    k, a = f
    d = datetime.date.fromisoformat(row["date"]).strftime("%d.%m")
    return L["flag_" + k].format(d=d, **a)


# ---------------------------------------------------------------- summaries
def people(cfg):
    """chat id → name: worktime.people, else telegram.voice.users / team (chat id as name)."""
    w = cfg.get("worktime") or {}
    tg = cfg.get("telegram") or {}
    p = {str(k): str(v) for k, v in (w.get("people") or {}).items()}
    if not p:
        p = {str(k): str(v) for k, v in ((tg.get("voice") or {}).get("users") or {}).items()}
    return p


def collect(cfg, data=None, now=None):
    """Everything the dashboard shows about work time."""
    now = now or datetime.datetime.now()
    w = wcfg(cfg)
    lang = (cfg.get("company") or {}).get("language", "en")
    L = texts(lang)
    _LANG[0] = lang
    hol = {str(h) for h in (w.get("holidays") or [])}
    rows = days(read(events_path(cfg, data)), now, w, hol)
    today, month = now.date().isoformat(), now.strftime("%Y-%m")
    team = people(cfg)
    names = {r["who"]: r["name"] for r in rows}
    names.update(team)
    on, att = [], []
    seen_today = set()
    for r in rows:
        if r["date"] != today and r["state"] not in ("work", "pause") and r.get("end_day") != today:
            continue
        seen_today.add(r["who"])
        st = {"work": "ok", "pause": "wait", "done": "idle"}.get(r["state"], "warn")
        when = L["since"].format(t=r["since"]) if r["state"] == "work" else L["paused_s"].format(t=r["since"]) if r["state"] == "pause" \
            else L["done_s"].format(a=r["start"], b=r["end"])
        site = (f'{r["site"]} ✓' if r["inside"] else f'{r["site"]} · {r["dist"]} {"м" if lang == "ru" else "m"}') if r["site"] else ""
        on.append(dict(st=st, name=names.get(r["who"], r["name"]), when=when, site=site, far=bool(r["site"] and r["inside"] is False),
                       h=hm(r["worked"]), m=r["worked"], state=r["state"]))
    for who, name in team.items():
        if who not in seen_today:
            on.append(dict(st="idle", name=name, when=L["absent"], site="", far=False, h="—", m=0, state="absent"))
    on.sort(key=lambda x: ({"work": 0, "pause": 1, "done": 2, "absent": 3}.get(x["state"], 4), x["name"]))
    mon = {}
    for r in rows:
        if not r["date"].startswith(month):
            continue
        m = mon.setdefault(r["who"], dict(name=names.get(r["who"], r["name"]), days=0, m=0, over=0, night=0, wk=0))
        m["days"] += 1
        m["m"] += r["worked"]
        m["over"] += r["over"]
        m["night"] += r["night"]
        m["wk"] += r["worked"] if r["weekend"] else 0
    flags = []
    week_ago = (now.date() - datetime.timedelta(days=7)).isoformat()
    for r in rows:
        if r["date"] < week_ago:
            continue
        for f in r["flags"]:
            lvl = "warn" if f[0] in ("noend", "far", "long") else "idle"
            flags.append(dict(lvl=lvl, name=names.get(r["who"], r["name"]), text=flag_text(f, r, L), d=r["date"]))
            if lvl == "warn":
                att.append(dict(lvl="warn", text=f'{L["title"]}: {names.get(r["who"], r["name"])} — {flag_text(f, r, L)}', act=""))
    flags.sort(key=lambda x: x["d"], reverse=True)
    flags.sort(key=lambda x: x["lvl"] != "warn")
    return dict(n=len(rows), now=sum(1 for x in on if x["state"] in ("work", "pause")), team=len(set(team) | seen_today),
                today=hm(sum(x["m"] for x in on)), month=hdec(sum(m["m"] for m in mon.values())),
                on=on, mon=sorted(mon.values(), key=lambda x: -x["m"]), flags=flags[:10], attention=att[:5])


def person_totals(evs, who, now, w):
    rows = [r for r in days(evs, now, w) if r["who"] == str(who)]
    d0 = now.date()
    wk0 = d0 - datetime.timedelta(days=d0.weekday())
    t = sum(r["worked"] for r in rows if r["date"] == d0.isoformat())
    wk = sum(r["worked"] for r in rows if r["date"] >= wk0.isoformat())
    mo = sum(r["worked"] for r in rows if r["date"].startswith(now.strftime("%Y-%m")))
    return t, wk, mo


def state_of(evs, who, now):
    """'none' | 'work' | 'pause' | 'done' — the person's latest shift (an open night shift counts), plus its start time."""
    r = [x for x in days(evs, now) if x["who"] == str(who)]
    if not r:
        return "none", ""
    last = r[-1]
    if last["state"] in ("work", "pause"):
        return last["state"], last["start"]
    if last["date"] == now.date().isoformat() or last.get("end_day") == now.date().isoformat():
        return last["state"], last["start"]
    return "none", ""


# ---------------------------------------------------------------- the bot side
def keyboard(lang, geo, state="none"):
    """Reply keyboard under the chat: Start (with location when geo) · Pause/Back · End."""
    L = texts(lang)
    first = {"text": L["start"], "request_location": True} if geo else {"text": L["start"]}
    mid = {"text": L["back"] if state == "pause" else L["pause"]}
    return {"keyboard": [[first], [mid, {"text": L["end"]}]], "resize_keyboard": True, "is_persistent": True}


def which_button(text):
    for lang, L in TEXT.items():
        for k in ("start", "pause", "back", "end"):
            if text == L[k]:
                return k
    return {"/in": "start", "/start_work": "start", "/pause": "pause", "/back": "back", "/out": "end", "/end": "end"}.get(text.split("@")[0], "")


def mark(cfg, path, who, name, action, now=None, location=None, lang="en"):
    """One button press → (reply text, new state). location = Telegram location dict or None."""
    now = now or datetime.datetime.now()
    w = wcfg(cfg)
    L = texts(lang)
    _LANG[0] = lang
    evs = read(path)
    st, t0 = state_of(evs, who, now)
    ts = now.strftime(FMT)
    if action == "start":
        if st in ("work", "pause"):
            return L["already"].format(t=t0), st
        lat = lon = None
        site, dist, inside = "", None, None
        extra = {}
        if location:
            lat, lon = location.get("latitude"), location.get("longitude")
            site, dist, inside = nearest_site(w, lat, lon)
            if location.get("horizontal_accuracy"):
                extra["acc"] = int(location["horizontal_accuracy"])
        rec = add(path, who, name, "start", ts, lat, lon, site, dist, inside=inside, **extra)
        if rec.get("site"):
            where = L["on_site"].format(site=site) if inside else L["off_site"].format(d=dist, site=site)
        else:
            where = "" if location or not w.get("geo") else L["no_geo"]
        return L["started"].format(t=ts[11:], site=where), "work"
    if st not in ("work", "pause"):
        return L["not_started"], st
    if action == "pause":
        if st == "pause":
            action = "back"
        else:
            add(path, who, name, "pause", ts)
            return L["paused"].format(t=ts[11:]), "pause"
    if action == "back":
        if st != "pause":
            return L["already"].format(t=t0), st
        add(path, who, name, "back", ts)
        return L["backed"].format(t=ts[11:]), "work"
    if action == "end":
        if st == "pause":
            add(path, who, name, "back", ts)
        add(path, who, name, "end", ts)
        t, _, _ = person_totals(read(path), who, now, w)
        return L["ended"].format(t=ts[11:], h=hm(t)), "done"
    return "", st


def due_reminders(cfg, path, now=None):
    """[(chat id, text)] for open days after remind_at — once per person and day (state file next to the log)."""
    now = now or datetime.datetime.now()
    w = wcfg(cfg)
    if now.strftime("%H:%M") < str(w["remind_at"]):
        return []
    lang = (cfg.get("company") or {}).get("language", "en")
    L = texts(lang)
    _LANG[0] = lang
    sp = path + ".remind.json"
    try:
        done = json.load(open(sp, encoding="utf-8"))
    except (OSError, ValueError):
        done = {}
    out = []
    for r in days(read(path), now, w):
        if r["state"] not in ("work", "pause"):
            continue
        k = f'{r["who"]}:{r["date"]}'
        if k in done:
            continue
        out.append((r["who"], L["remind"].format(t=r["start"], h=hm(r["worked"]))))
        done[k] = now.strftime(FMT)
    if out:
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(done, f)
    return out


def remind_buttons(lang):
    L = texts(lang)
    return [[{"text": L["stop_now"], "callback_data": "wt:end"}, {"text": L["still"], "callback_data": "wt:keep"}]]


# ---------------------------------------------------------------- the month for the accountant
def month_xlsx(cfg, out, month, data=None, now=None):
    import openpyxl
    import safe_xlsx  # noqa: F401 — every script that writes .xlsx
    from openpyxl.styles import Font, PatternFill
    now = now or datetime.datetime.now()
    w = wcfg(cfg)
    hol = {str(h) for h in (w.get("holidays") or [])}
    rows = [r for r in days(read(events_path(cfg, data)), now, w, hol) if r["date"].startswith(month)]
    names = people(cfg)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Month"
    head = ["Person", "Days", "Hours", "Overtime h", "Night h", "Weekend/holiday h", "Days without end mark", "Corrected days"]
    ws.append(head)
    tot = {}
    for r in rows:
        t = tot.setdefault(r["who"], [names.get(r["who"], r["name"]), 0, 0, 0, 0, 0, 0, 0])
        t[1] += 1
        t[2] += r["worked"]
        t[3] += r["over"]
        t[4] += r["night"]
        t[5] += r["worked"] if r["weekend"] else 0
        t[6] += r["state"] == "noend"
        t[7] += any(f[0] == "fix" for f in r["flags"])
    for t in sorted(tot.values(), key=lambda x: x[0]):
        ws.append([t[0], t[1], hdec(t[2]), hdec(t[3]), hdec(t[4]), hdec(t[5]), t[6], t[7]])
    ds = wb.create_sheet("Days")
    ds.append(["Date", "Person", "Start", "End", "Pause min", "Hours", "Night h", "Weekend/holiday", "Site", "Distance m", "Notes"])
    for r in rows:
        ds.append([r["date"], names.get(r["who"], r["name"]), r["start"], r["end"], r["pause"], hdec(r["worked"]), hdec(r["night"]),
                   "yes" if r["weekend"] else "", r["site"], r["dist"] if r["dist"] is not None else "",
                   "; ".join(flag_text(f, r, TEXT["en"]) for f in r["flags"])])
    for sh in (ws, ds):
        for c in sh[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1A365D")
        for col in sh.columns:
            sh.column_dimensions[col[0].column_letter].width = max(10, min(40, max(len(str(c.value or "")) for c in col) + 2))
        sh.freeze_panes = "A2"
    wb.save(out)
    return len(rows)


# ---------------------------------------------------------------- command line
def load_cfg(path):
    if not path or not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        c = yaml.safe_load(f) or {}
    c["_path"] = os.path.abspath(path)
    return c


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON work time")
    ap.add_argument("cmd", choices=["status", "month", "remind", "fix"])
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--month", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--who", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--start", default="")
    ap.add_argument("--end", default="")
    ap.add_argument("--why", default="")
    ap.add_argument("--outbox", default="", help="tests: write reminders to a file instead of Telegram")
    a = ap.parse_args(argv)
    cfg = load_cfg(a.config)
    path = events_path(cfg, a.data)
    if a.cmd == "status":
        D = collect(cfg, a.data)
        for x in D["on"]:
            print(f'{x["name"]:<20} {x["when"]:<18} {x["site"]:<22} {x["h"]}')
        print(f'at work now: {D["now"]} · today {D["today"]} · month {D["month"]} h · to check {len(D["flags"])}')
        return 0
    if a.cmd == "month":
        month = a.month or datetime.date.today().strftime("%Y-%m")
        out = a.out or os.path.join(a.data, f"worktime_{month}.xlsx")
        n = month_xlsx(cfg, out, month, a.data)
        print(f"worktime: {out} · {n} day rows")
        return 0
    if a.cmd == "fix":
        if not (a.who and a.why and (a.start or a.end) and re.match(r"^\d{4}-\d{2}-\d{2}$", a.date or "")):
            sys.exit("fix needs --who, --date YYYY-MM-DD, --start and/or --end HH:MM, and --why (kept in the log)")
        team = people(cfg)
        who = next((k for k, v in team.items() if v.lower() == a.who.lower()), a.who)
        add(path, who, team.get(who, a.who), "fix", by="manager", date=a.date, start=a.start, end=a.end, why=a.why)
        print(f"worktime: {team.get(who, a.who)} {a.date} corrected ({a.start or '—'}–{a.end or '—'}): {a.why}")
        return 0
    if a.cmd == "remind":
        lang = (cfg.get("company") or {}).get("language", "en")
        due = due_reminders(cfg, path)
        for chat, text in due:
            if a.outbox:
                os.makedirs(a.outbox, exist_ok=True)
                with open(os.path.join(a.outbox, "telegram_worktime.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"chat": chat, "text": text, "buttons": remind_buttons(lang)}, ensure_ascii=False) + "\n")
                continue
            try:
                from bot.telegram_bot import Api, token_from
                Api(token_from(cfg.get("telegram") or {}), timeout=20).call(
                    "sendMessage", chat_id=chat, text=text, reply_markup={"inline_keyboard": remind_buttons(lang)})
            except Exception as e:  # noqa: BLE001
                print(f"worktime remind {chat}: {str(e)[:100]}")
        print(f"worktime: {len(due)} reminder(s)")
        return 0
    return 1


if __name__ == "__main__":
    import utf8_console  # noqa: F401
    sys.exit(main())
