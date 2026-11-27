# -*- coding: utf-8 -*-
"""FLOKTRON · meeting_links.py — online meetings on the dashboard with their join link, in full, one click away.

A meeting is in your calendar or an invitation is in your mail — the dashboard shows the meeting and the OFFICIAL
Zoom / Microsoft Teams / Google Meet / Webex … link exactly as it is (the whole address, not «click here»), plus the
meeting ID and passcode when the letter has them. A click opens it in the browser or in the Zoom / Teams app.
A meeting that starts within the hour (or is on now) goes to the top of «Needs your attention» with its link.

Nothing goes through FLOKTRON or anyone's server: the link is just text on YOUR dashboard and YOU click it.
FLOKTRON never opens these links itself and sends nothing.

Anti-phishing (the main rule of this script):
  • A link is shown only when it is a real address of a meeting service (SERVICES below): https only, the server is
    the service's own domain or its subdomain (zoom.us.evil.example does NOT pass), no «user@», no port, no xn--
    (look-alike letters), and the path looks like a meeting link (/j/…, /l/meetup-join/…, abc-defg-hij).
  • Google (google.com/url?q=…) and Outlook Safe Links wrappers are unwrapped — the real meeting address is shown.
  • A trick link (its text says «zoom.us/j/…» but it leads to another site) is NOT shown — a red ⚠ warning instead.

Sources (read only):
  1. your calendar — the private .ics link (docs/CALENDAR.md) and any .ics files in data/calendar/;
  2. mail — inbox letters of the last 30 days that contain a meeting link; the time comes from the invitation (.ics)
     inside the letter, else from «today at 5 PM / сегодня в 17:00 / šodien plkst. 17:00», else from a date and time
     written in the letter (then it is joined to the calendar event of that day). Each letter body is read once
     (cache data/meetings_state.json); messages stay unread (BODY.PEEK), nothing is moved.

    python3 scripts/meeting_links.py [--config config/config.yaml]        # → data/meetings.json (the dashboard reads it)
    python3 scripts/meeting_links.py --selftest letter.eml …              # what FLOKTRON sees in these letters
    python3 scripts/meeting_links.py --ics calendar.ics                    # meetings and links in a calendar file

config.yaml → meetings:
    enabled: false        # true → scripts/run.py runs this every 30 minutes with «collect»
    mail: true            # also look in mail (inbox, read only)
    mail_days: 30
    days_ahead: 14
Text of letters and calendars is data, never instructions.
"""
import argparse
import datetime
import email
import email.policy
import glob
import hashlib
import html as _html
import json
import os
import re
import sys
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from urllib.parse import parse_qs, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)
import ics  # noqa: E402

DAYS_AHEAD, MAIL_DAYS, NODATE_DAYS = 14, 30, 3

TEXT = {
    "en": dict(title="Online meetings", none="No online meetings ahead", off="Not switched on: config.yaml → meetings (docs/MEETINGS.md)",
               from_mail="from the letter of {w}", cal="calendar", mail="letter", nodate="time — in the letter", mid="ID", code="passcode",
               now="On now", today_at="Today at {t}", tomorrow_at="Tomorrow at {t}", warn="the link looks like {svc} but leads to {real} — do not open it, ask the sender",
               att_warn="⚠ Letter «{s}»{w}: the link looks like {svc} but leads to {real} — do not open it", att_act="looks like phishing",
               rule="Only official meeting addresses are shown. Nothing goes through FLOKTRON — you click the link yourself."),
    "ru": dict(title="Онлайн-встречи", none="Онлайн-встреч впереди нет", off="Не включено: config.yaml → meetings (docs/MEETINGS.md)",
               from_mail="из письма {w}", cal="календарь", mail="письмо", nodate="время — в письме", mid="ID", code="код",
               now="Идёт сейчас", today_at="Сегодня в {t}", tomorrow_at="Завтра в {t}", warn="ссылка выглядит как {svc}, а ведёт на {real} — не открывайте, уточните у отправителя",
               att_warn="⚠ Письмо «{s}»{w}: ссылка выглядит как {svc}, а ведёт на {real} — не открывайте", att_act="похоже на фишинг",
               rule="Показываются только официальные адреса встреч. Через FLOKTRON ничего не идёт — по ссылке нажимаете вы."),
    "lv": dict(title="Tiešsaistes sapulces", none="Tiešsaistes sapulču priekšā nav", off="Nav ieslēgts: config.yaml → meetings (docs/MEETINGS.md)",
               from_mail="no vēstules: {w}", cal="kalendārs", mail="vēstule", nodate="laiks — vēstulē", mid="ID", code="kods",
               now="Notiek tagad", today_at="Šodien {t}", tomorrow_at="Rīt {t}", warn="saite izskatās pēc {svc}, bet ved uz {real} — neatveriet, pajautājiet sūtītājam",
               att_warn="⚠ Vēstule «{s}»{w}: saite izskatās pēc {svc}, bet ved uz {real} — neatveriet", att_act="izskatās pēc pikšķerēšanas",
               rule="Rāda tikai oficiālas sapulču adreses. Caur FLOKTRON nekas neiet — saiti spiežat jūs paši."),
}


def texts(lang):
    return TEXT.get(lang) or TEXT["en"]


# ---------------------------------------------------------------- 1. official addresses only
# (name, domains — the domain itself or a subdomain, path of a meeting link)
SERVICES = [
    ("Zoom", ("zoom.us", "zoom.com", "zoomgov.com"), r"/(j|w|s|wc/join|wc|my)/[\w.\-]+"),
    ("Microsoft Teams", ("teams.microsoft.com", "teams.live.com", "teams.cloud.microsoft"), r"/(l/meetup-join/|meet/\d{6,}|dl/launcher/)"),
    ("Google Meet", ("meet.google.com",), r"/([a-z]{3,4}-[a-z]{4}-[a-z]{3,4}|lookup/[\w\-]+)(\b|$)"),
    ("Webex", ("webex.com",), r"/(meet/|join/|wbxmjs/joinservice/|[\w\-]+/j\.php|j\.php|[\w\-]+/meet/)"),
    ("Jitsi Meet", ("meet.jit.si",), r"/[\w\-]{4,}"),
    ("GoTo Meeting", ("meet.goto.com", "global.gotomeeting.com", "app.gotomeeting.com"), r"/(join/)?\d{6,}"),
    ("Whereby", ("whereby.com",), r"/[\w\-]{3,}"),
    ("Skype", ("join.skype.com",), r"/[\w]{6,}"),
]
WRAPPERS = (  # wrappers that are unwrapped (only when the link INSIDE is an official one)
    (("google.com", "www.google.com"), "/url", ("q", "url")),
    (("safelinks.protection.outlook.com",), "/", ("url",)),
)
HOST_OK = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+$")
URL_RX = re.compile(r"https?://[^\s<>\"'`\]\[(){}|\\^]+", re.I)


def _host_in(host, doms):
    return any(host == d or host.endswith("." + d) for d in doms)


def _unwrap(u, depth=0):
    """google.com/url?q=… / Outlook Safe Links → the link inside (up to 3 levels)."""
    if depth > 2:
        return u
    try:
        s = urlsplit(u)
    except ValueError:
        return u
    host = (s.hostname or "").lower()
    for doms, path, keys in WRAPPERS:
        if _host_in(host, doms) and s.path.startswith(path):
            q = parse_qs(s.query)
            for k in keys:
                if q.get(k):
                    return _unwrap(q[k][0], depth + 1)
    return u


def check(u):
    """→ (service, clean link) or None. Only real addresses of meeting services."""
    u = _html.unescape(str(u or "")).strip().strip("<>").rstrip(".,;:!?»”'\"")
    u = _unwrap(u)
    if not u or len(u) > 600 or re.search(r"[\s\x00-\x1f\x7f]", u):
        return None
    try:
        s = urlsplit(u)
        port = s.port
    except ValueError:
        return None
    if s.scheme.lower() not in ("https", "http") or "@" in s.netloc or port not in (None, 443):
        return None
    host = (s.hostname or "").lower().rstrip(".")
    if not host or "xn--" in host or not HOST_OK.match(host):
        return None
    for name, doms, path in SERVICES:
        if _host_in(host, doms):
            if not re.match(path, s.path or "/", re.I):
                return None
            return name, "https://" + host + s.path + ("?" + s.query if s.query else "") + ("#" + s.fragment if s.fragment else "")
    return None


def looks_like_meeting(label):
    """The visible text of a link looks like a meeting address (zoom.us/j/…), even without https:// — to catch tricks."""
    t = re.sub(r"\s+", "", _html.unescape(label or "")).lower()
    m = re.search(r"((https?://)?[a-z0-9.\-]+\.[a-z]{2,}(/\S*)?)", t)
    if not m:
        return None
    return check(m.group(1) if m.group(1).startswith("http") else "https://" + m.group(1))


ID_RX = re.compile(r"(?i)(meeting id|id встречи|идентификатор (конференции|встречи)|sapulces id|konferences id|besprechungs-id|kohtumise id)\s*[:：]?\s*((?:\d[\d ]{7,22}\d))")
CODE_RX = re.compile(r"(?i)(passcode|password|код доступа|пароль|piekļuves kods|pieejas kods|parole|kenncode|pääsukood)\s*[:：]?\s*([A-Za-z0-9]{4,20})\b")


def extras(text):
    """Meeting ID and passcode — for joining in the app by hand (when the letter has them)."""
    i, c = ID_RX.search(text or ""), CODE_RX.search(text or "")
    return dict(mid=re.sub(r"\s+", " ", i.group(3)).strip() if i else "", code=c.group(2) if c else "")


def find(text="", htm=""):
    """Meeting links in a letter or an event → (links [{svc, url}] one per service, first one wins;
    warns [{svc, shown, real}] — trick links)."""
    links, warns, seen = [], [], set()

    def add(svc, url):
        if svc in seen:      # Teams gives two links for one meeting (short /meet/… and long meetup-join) — show the short one
            for x in links:
                if x["svc"] == svc == "Microsoft Teams" and len(url) < len(x["url"]):
                    x["url"] = url
            return
        seen.add(svc)
        links.append(dict(svc=svc, url=url))

    for href, label in re.findall(r'(?is)<a\s[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', htm or ""):
        real = check(href)
        lab = re.sub(r"<[^>]+>", " ", label)
        shown = looks_like_meeting(lab)
        if shown and (not real or urlsplit(real[1]).hostname != urlsplit(shown[1]).hostname):
            try:
                rh = (urlsplit(_unwrap(_html.unescape(href))).hostname or "?").lower()
            except ValueError:
                rh = "?"
            warns.append(dict(svc=shown[0], shown=re.sub(r"\s+", " ", _html.unescape(lab)).strip()[:80], real=rh[:60]))
            continue
        if real:
            add(*real)
    plain = (text or "") + "\n" + re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<a\s[^>]*>.*?</a>", " ", htm or ""))
    for u in URL_RX.findall(_html.unescape(plain)):
        r = check(u)
        if r:
            add(*r)
    return links, warns


# ---------------------------------------------------------------- 2. calendar (.ics)
LINK_FIELDS = ("LOCATION", "URL", "DESCRIPTION", "X-ALT-DESC", "X-GOOGLE-CONFERENCE", "X-MICROSOFT-SKYPETEAMSMEETINGURL",
               "X-MICROSOFT-ONLINEMEETINGCONFLINK", "X-MICROSOFT-ONLINEMEETINGEXTERNALLINK", "CONFERENCE")


def _uesc(v):
    return v.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def ics_meetings(text, today, tz="", src="calendar", days=DAYS_AHEAD):
    """Events with (or without — to join with letters) an online link, from today to +days. Repeats are expanded."""
    out = []
    raw = ics.unfold(str(text or "")).replace("\r\n", "\n")
    method = (re.search(r"(?m)^METHOD:(.*)$", raw) or [None, ""])[1].strip().upper()
    zone = ics.zone(tz)
    for b in re.findall(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", raw, re.S):
        evs = ics.parse("BEGIN:VCALENDAR\nBEGIN:VEVENT\n" + b + "\nEND:VEVENT\nEND:VCALENDAR", tz)
        if not evs:
            continue
        e = evs[0]
        flds = "\n".join(_uesc(v) for k, v in re.findall(r"(?m)^([A-Z\-]+)[^:\n]*:(.*)$", b) if k in LINK_FIELDS)
        htm = "\n".join(_uesc(v) for _, v in re.findall(r"(?m)^(X-ALT-DESC)[^:\n]*:(.*)$", b))
        links, warns = find(flds, htm)
        title = (e.get("title") or "").strip() or "(no title)"
        for i in range(days + 1):
            d = today + datetime.timedelta(days=i)
            if not ics.occurs_on(e, d):
                continue
            st = e["start"]
            start = None
            if not e["all_day"]:
                start = datetime.datetime.combine(d, st.timetz() if st.tzinfo else st.time())
                if start.tzinfo is None:
                    start = start.replace(tzinfo=zone) if zone else start.astimezone()
            dur = (e["end"] - e["start"]) if (e.get("end") is not None and not e["all_day"]) else None
            out.append(dict(uid=e.get("uid") or "", title=title[:120], day=d.isoformat(), start=start.isoformat() if start else None,
                            end=(start + dur).isoformat() if (start and dur) else None, links=links, warns=warns,
                            extra=extras(flds), src=src, cancel=(method == "CANCEL")))
            if not e.get("rrule"):
                break
    return out


# ---------------------------------------------------------------- 3. mail
def _hdr(v):
    try:
        return str(make_header(decode_header(str(v or "")))).strip()
    except Exception:  # noqa: BLE001
        return str(v or "").strip()


def _squash(t):
    return re.sub(r"\s+", " ", str(t or "")).strip()


def key_of(s):
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()[:12]   # a short dedupe key, not security


TODAY_RX = re.compile(r"(?i)\b(today|tonight|šodien|сегодня|heute|täna|šiandien)\b[^.\n]{0,40}?(?:at|plkst\.?|в|um|kell|kl\.?|\s)\s*(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?")


def time_today(text, dt):
    """«today at 5 PM», «šodien plkst. 17:00», «сегодня в 17:00» → that time on the day of the letter."""
    m = TODAY_RX.search(text or "")
    if not m:
        return None
    h, mi, ap = int(m.group(2)), int(m.group(3) or 0), (m.group(4) or "").lower().replace(".", "")
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if not (0 <= h <= 23 and 0 <= mi <= 59) or (not ap and not m.group(3)):   # «today 5» without minutes or am/pm is not a time
        return None
    return dt.replace(hour=h, minute=mi, second=0, microsecond=0)


MONTHS = {}
for _i, _names in enumerate([("jan", "janvār", "январ", "januar", "jaanuar", "sausio"), ("feb", "februār", "феврал", "februar", "veebruar", "vasario"),
                             ("mar", "mart", "март", "märz", "marts", "kovo"), ("apr", "aprīl", "апрел", "aprill", "balandžio"),
                             ("may", "maij", "мая", "май", "mai", "gegužės"), ("jun", "jūnij", "июн", "juuni", "birželio"),
                             ("jul", "jūlij", "июл", "juuli", "liepos"), ("aug", "august", "август", "rugpjūčio"),
                             ("sep", "septembr", "сентябр", "september", "rugsėjo"), ("oct", "oktobr", "октябр", "okt", "spalio"),
                             ("nov", "novembr", "ноябр", "lapkričio"), ("dec", "decembr", "декабр", "dez", "detsembr", "gruodžio")], 1):
    for _n in _names:
        MONTHS[_n] = _i
MON_RX = "|".join(sorted(map(re.escape, MONTHS), key=len, reverse=True))
DATE_RXS = (re.compile(r"\b(\d{1,2})[./](\d{1,2})(?:[./](20\d\d))?\b"), re.compile(r"\b(20\d\d)-(\d{2})-(\d{2})\b"),
            re.compile(rf"(?i)\b(\d{{1,2}})\.?\s*({MON_RX})[a-zāēīūčšžёа-я]*"), re.compile(rf"(?i)\b({MON_RX})[a-z]*\.?\s+(\d{{1,2}})\b"))
TIME_RX = re.compile(r"(?:\b|plkst\.?\s*|kl\.?\s*)([01]?\d|2[0-3]):([0-5]\d)\b|(?:plkst|kl)\.?\s*([01]?\d|2[0-3])\.([0-5]\d)\b")


def text_days(text, ref):
    """Dates written in a letter (02.12.2026, 2026-12-02, 2. decembrī, 2 декабря, December 2) → {ISO}; the year nearest to the letter."""
    out = set()

    def add(d, m, y=None):
        try:
            x = datetime.date(int(y) if y else ref.year, int(m), int(d))
            if not y and x < ref - datetime.timedelta(days=60):   # «5 January» in a December letter
                x = x.replace(year=ref.year + 1)
            out.add(x.isoformat())
        except (ValueError, TypeError):
            pass
    t = text or ""
    for m in DATE_RXS[0].finditer(t):
        if int(m.group(2)) <= 12:
            add(m.group(1), m.group(2), m.group(3))
    for m in DATE_RXS[1].finditer(t):
        add(m.group(3), m.group(2), m.group(1))
    for m in DATE_RXS[2].finditer(t):
        add(m.group(1), MONTHS.get(m.group(2).lower()))
    for m in DATE_RXS[3].finditer(t):
        add(m.group(2), MONTHS.get(m.group(1).lower()))
    return out


def parse_mail(raw, today=None, tz=""):
    """A letter → dict(k, mid, frm, addr, subj, date, bulk, meets [events of its .ics], links, warns, extra, when, days, times)."""
    try:
        msg = email.message_from_bytes(raw, policy=email.policy.default)
    except Exception:  # noqa: BLE001
        msg = email.message_from_bytes(raw)
    txt = htm = ""
    cal = []
    for part in msg.walk():
        ct = part.get_content_type()
        fn = (part.get_filename() or "").lower()
        if ct == "text/calendar" or fn.endswith(".ics"):
            try:
                cal.append(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace"))
            except Exception:  # noqa: BLE001
                pass
            continue
        if part.get_filename() or ct not in ("text/plain", "text/html"):
            continue
        try:
            t = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        if ct == "text/plain" and not txt:
            txt = t[:60000]
        if ct == "text/html" and not htm:
            htm = t[:200000]
    name, addr = parseaddr(_hdr(msg.get("From")))
    zone = ics.zone(tz)
    try:
        dt = parsedate_to_datetime(str(msg.get("Date")))
        dt = dt.astimezone(zone) if zone else dt.astimezone()
    except Exception:  # noqa: BLE001
        dt = datetime.datetime.now(zone) if zone else datetime.datetime.now().astimezone()
    subj = _squash(_hdr(msg.get("Subject"))) or "(no subject)"
    mid = str(msg.get("Message-ID") or "").strip() or f"{addr}|{subj}|{dt:%Y%m%d%H%M}"
    links, warns = find(txt, htm)
    plain = _html.unescape(txt or re.sub(r"<[^>]+>", " ", htm))
    today = today or dt.date()
    meets = []
    for c in cal:
        try:
            meets += ics_meetings(c, today - datetime.timedelta(days=1), tz, src="letter", days=DAYS_AHEAD + 1)
        except Exception:  # noqa: BLE001 — a broken invitation is skipped
            pass
    w = time_today(plain, dt)
    return dict(k=key_of(mid), mid=mid, frm=_squash(name) or addr.lower(), addr=addr.lower(), subj=subj[:140], date=dt.isoformat(),
                bulk=bool(msg.get("List-Unsubscribe") or msg.get("List-Id")), meets=meets, links=links, warns=warns,
                extra=extras(plain), when=w.isoformat() if w else None, days=sorted(text_days(subj + "\n" + plain, dt.date())),
                times=sorted({f"{int(m[0] or m[2]):02d}:{m[1] or m[3]}" for m in TIME_RX.findall(plain)}))


def useful(it):
    return bool(it.get("links") or it.get("warns") or any(m["links"] for m in it.get("meets", [])))


# ---------------------------------------------------------------- 4. one meeting = one line
STOP = set("the and for with your from meeting invitation invite online call session zoom teams microsoft google meet webex "
           "tikšanās sapulce uzaicinājums встреча встречи приглашение онлайн звонок".split())


def _words(t):
    return {w for w in re.findall(r"[\wāčēģīķļņšūžа-яё]{4,}", (t or "").lower()) if w not in STOP}


def _near(a, b, sec=1800):
    """Two meetings at the same time (±30 min); a missing time does not stop the join."""
    if not a or not b:
        return True
    try:
        return abs((datetime.datetime.fromisoformat(a) - datetime.datetime.fromisoformat(b)).total_seconds()) <= sec
    except ValueError:
        return True


def _extras_of(x, m):
    e, xe = m.get("extra") or {}, x.get("extra") or {}
    return dict(mid=e.get("mid") or xe.get("mid", ""), code=e.get("code") or xe.get("code", ""))


def build(cal_events, mails, now):
    """→ items [{k, title, start, end, day, svc, url, extra, src, frm, subj, warn, nodate}] — the nearest first."""
    today = now.date()
    items = []

    def alive(start, end, day):
        if start:
            s = datetime.datetime.fromisoformat(start)
            e = datetime.datetime.fromisoformat(end) if end else s + datetime.timedelta(hours=1)
            return e >= now
        return datetime.date.fromisoformat(day) >= today

    cancelled = {m["uid"] for x in mails for m in x["meets"] if m.get("cancel") and m["uid"]}
    mails = sorted(mails, key=lambda x: x["date"])            # the newer letter wins (a moved meeting)
    by_uid = {}
    for x in mails:
        for m in x["meets"]:
            if m["uid"] and not m.get("cancel"):
                by_uid[(m["uid"], m["day"])] = (x, m)
    used = set()

    def item(ev, lk, src, frm="", subj="", warn=None, extra=None):
        k = key_of(f'{ev.get("uid") or ev["title"]}|{ev["day"]}|{ev.get("start") or ""}')
        return dict(k=k, title=ev["title"], start=ev.get("start"), end=ev.get("end"), day=ev["day"],
                    svc=lk["svc"] if lk else (warn or {}).get("svc", ""), url=lk["url"] if lk else "",
                    extra=extra or ev.get("extra") or {}, src=src, frm=frm, subj=subj, warn=warn, nodate=False)

    # (a) calendar events: own link → else the letter with the same UID → else a letter about the same meeting
    for ev in cal_events:
        if ev["uid"] in cancelled or not alive(ev.get("start"), ev.get("end"), ev["day"]):
            continue
        if ev["links"]:
            items.append(item(ev, ev["links"][0], ev["src"]))
            continue
        hit = by_uid.get((ev["uid"], ev["day"])) if ev["uid"] else None
        if hit:
            x, m = hit
            lk = (m["links"] or x["links"] or [None])[0]
            if lk or x["warns"]:
                used.add(x["k"])
                items.append(item(ev, lk, ev["src"], x["frm"], x["subj"], None if lk else x["warns"][0], _extras_of(x, m)))
                continue
        ew = _words(ev["title"])
        for x in reversed(mails):
            if x["k"] in used or not (x["links"] or x["warns"]):
                continue
            words = bool(ew & (_words(x["subj"]) | {w for m in x["meets"] for w in _words(m["title"])}))
            mdays = {m["day"] for m in x["meets"] if _near(m.get("start"), ev.get("start"))}
            same_day = ev["day"] in mdays or ((x["when"] or x["date"])[:10] == ev["day"] and _near(x["when"], ev.get("start")))
            said = ev["day"] in (x.get("days") or ()) and (words or (ev.get("start") or "")[11:16] in (x.get("times") or ()))
            if (same_day and words) or said:     # same day + common words, or the letter names its date and time
                used.add(x["k"])
                lk = (x["links"] or [None])[0]
                items.append(item(ev, lk, ev["src"], x["frm"], x["subj"], None if lk else x["warns"][0], x["extra"]))
                break
    have = {(i["day"], i["url"]) for i in items if i["url"]} | {(i["day"], i["title"].lower()) for i in items}
    # (b) invitations in letters that are not in the calendar
    for x in mails:
        if x["k"] in used:
            continue
        for m in x["meets"]:
            if m.get("cancel") or m["uid"] in cancelled or not alive(m.get("start"), m.get("end"), m["day"]):
                continue
            lk = (m["links"] or x["links"] or [None])[0]
            wn = None if lk else (m["warns"] or x["warns"] or [None])[0]
            if (not lk and not wn) or (m["day"], lk["url"] if lk else "") in have or (m["day"], m["title"].lower()) in have:
                continue
            have |= {(m["day"], lk["url"] if lk else ""), (m["day"], m["title"].lower())}
            items.append(item(m, lk, "letter", x["frm"], x["subj"], wn, _extras_of(x, m)))
            used.add(x["k"])
        if x["k"] in used or x["meets"]:
            continue
        # (c) a letter without an invitation: «today at 17:00», or «time — in the letter» (3 days, not newsletters)
        lk = (x["links"] or [None])[0]
        wn = None if lk else (x["warns"] or [None])[0]
        d = datetime.datetime.fromisoformat(x["date"])
        if x["when"]:
            ev = dict(uid="", title=x["subj"], day=x["when"][:10], start=x["when"], end=None)
            if not alive(ev["start"], None, ev["day"]):
                continue
        else:
            if x["bulk"] or (now - d).days >= NODATE_DAYS:
                continue
            ev = dict(uid="", title=x["subj"], day=d.date().isoformat(), start=None, end=None)
        if lk and ((ev["day"], lk["url"]) in have or (not x["when"] and lk["url"] in {i["url"] for i in items})):
            continue                                       # the same link is already shown with its meeting
        it = item(ev, lk, "letter", x["frm"], x["subj"], wn, x["extra"])
        it["nodate"] = not x["when"]
        items.append(it)
    items.sort(key=lambda i: (i["nodate"], i["start"] or i["day"] + "T23:59"))
    return items


# ---------------------------------------------------------------- 5. run
def mcfg(cfg):
    m = dict(cfg.get("meetings") or {})
    m.setdefault("mail", True)
    m.setdefault("mail_days", MAIL_DAYS)
    m.setdefault("days_ahead", DAYS_AHEAD)
    return m


def tz_of(cfg):
    return ((cfg.get("calendar") or {}).get("timezone") or (cfg.get("company") or {}).get("timezone") or "")


def calendar_texts(cfg, data=DATA, log=print):
    """Your calendar link (when calendar.enabled) + .ics files in data/calendar/."""
    out = []
    cal = cfg.get("calendar") or {}
    if cal.get("enabled"):
        try:
            import calendar_read
            url = calendar_read.link(cal)
            if url:
                out.append(("calendar", calendar_read.fetch(url)))
        except Exception as e:  # noqa: BLE001 — the calendar problem never stops the rest
            log(f"meetings: calendar not read ({str(e)[:100]})")
    for f in sorted(glob.glob(os.path.join(data, "calendar", "*.ics"))):
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                out.append(("calendar", fh.read()))
        except OSError as e:
            log(f"meetings: {os.path.basename(f)} not read: {e}")
    return out


def scan_mail(messages, st, today, tz=""):
    """messages: iterable of dict(mid, raw or None) (mail/read.py meeting_mail). Each body is parsed once (cache)."""
    cache = st.setdefault("mail", {})
    items, alive = [], set()
    for m in messages:
        k0 = key_of(m["mid"]) if m.get("mid") else None
        if k0 and k0 in cache:
            it = cache[k0]
        elif m.get("raw"):
            it = parse_mail(m["raw"], today, tz)
            if not useful(it):
                it = {"k": it["k"], "none": 1}          # no meeting link — never opened again
            cache[it["k"]] = it
        else:
            continue
        alive.add(it["k"])
        if not it.get("none"):
            items.append(it)
    st["mail"] = {k: v for k, v in cache.items() if k in alive}
    return items


def _dump(path, obj, indent=None):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, path)


def out_path(data=DATA):
    return os.path.join(data, "meetings.json")


def run(cfg, data=DATA, now=None, messages=None, texts_=None, log=print):
    """→ items; writes data/meetings.json (+ data/meetings_state.json). messages=None → read the mailbox (if meetings.mail)."""
    tz = tz_of(cfg)
    zone = ics.zone(tz)
    now = now or (datetime.datetime.now(zone) if zone else datetime.datetime.now().astimezone())
    m = mcfg(cfg)
    spath = os.path.join(data, "meetings_state.json")
    try:
        with open(spath, encoding="utf-8") as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {}
    cal, seen = [], {}
    for src, t in (texts_ if texts_ is not None else calendar_texts(cfg, data, log)):
        try:
            for e in ics_meetings(t, now.date(), tz, src=src, days=int(m["days_ahead"])):
                key = (e["uid"] or e["title"].lower(), e["day"], e.get("start"))
                if key in seen:     # the same event in two sources — keep the one with a link
                    if e["links"] and not cal[seen[key]]["links"]:
                        cal[seen[key]] = e
                    continue
                seen[key] = len(cal)
                cal.append(e)
        except Exception as e:  # noqa: BLE001
            log(f"meetings: calendar ({src}) — {str(e)[:80]}")
    if messages is None and m.get("mail") and (cfg.get("mail") or {}).get("provider"):
        try:
            from mail.read import meeting_mail
            known = {v.get("mid") for v in (st.get("mail") or {}).values() if v.get("mid")} | set(st.get("seen_mids") or [])
            messages = list(meeting_mail(cfg["mail"], int(m["mail_days"]), [w for w in TERMS], skip_ids=known))
        except Exception as e:  # noqa: BLE001 — no mail = calendar only
            log(f"meetings: mail not read ({str(e)[:100]})")
            messages = None
    if messages is None:
        mails = [v for v in (st.get("mail") or {}).values() if not v.get("none")]
    else:
        mails = scan_mail(messages, st, now.date(), tz)
        st["seen_mids"] = sorted({x.get("mid") for x in messages if x.get("mid")})
    items = build(cal, mails, now)
    os.makedirs(data, exist_ok=True)
    _dump(out_path(data), {"updated": now.strftime("%Y-%m-%d %H:%M"), "items": items}, indent=1)
    _dump(spath, st)
    w = sum(1 for i in items if i["warn"])
    log(f"meetings: {sum(1 for i in items if i['url'])} with a link" + (f", ⚠ trick links {w}" if w else "") + f" · letters with a link {len(mails)}")
    return items


TERMS = ("zoom.", "teams.microsoft", "teams.live", "teams.cloud.microsoft", "meet.google", "webex.com", "meet.jit.si",
         "gotomeeting", "meet.goto", "whereby.com", "join.skype")


# ---------------------------------------------------------------- 6. dashboard
def collect(cfg, data=DATA, now=None, lang="en"):
    """For dashboard.py: dict(items, attention). Every link is checked AGAIN before it is shown (a changed file shows nothing)."""
    L = texts(lang)
    try:
        with open(out_path(data), encoding="utf-8") as f:
            raw = json.load(f).get("items", [])
    except (OSError, ValueError):
        raw = []
    zone = ics.zone(tz_of(cfg))
    now = now or (datetime.datetime.now(zone) if zone else datetime.datetime.now().astimezone())
    if now.tzinfo is None:
        now = now.replace(tzinfo=zone) if zone else now.astimezone()
    items, att = [], []
    for it in raw:
        ok = check(it.get("url")) if it.get("url") else None
        if it.get("url") and not ok:
            continue
        try:
            st = datetime.datetime.fromisoformat(it["start"]) if it.get("start") else None
            if st is not None:
                st = st.astimezone(now.tzinfo)
            day = st.date() if st else datetime.date.fromisoformat(it["day"])
        except (KeyError, ValueError, TypeError):
            continue
        x = dict(title=str(it.get("title") or "")[:120], svc=str(it.get("svc") or ""), url=ok[1] if ok else "", day=day,
                 time=st.strftime("%H:%M") if st else "", days=(day - now.date()).days, extra=it.get("extra") or {},
                 frm=str(it.get("frm") or "")[:60], src=str(it.get("src") or ""), warn=it.get("warn"), nodate=bool(it.get("nodate")))
        items.append(x)
        if x["warn"]:
            w = x["warn"]
            att.append(dict(lvl="bad", text=L["att_warn"].format(s=(it.get("subj") or x["title"])[:60], w=(" · " + x["frm"]) if x["frm"] else "",
                                                                 svc=w.get("svc", "?"), real=w.get("real", "?")), act=L["att_act"]))
        elif st and x["url"]:
            try:
                end = datetime.datetime.fromisoformat(it["end"]).astimezone(now.tzinfo) if it.get("end") else st + datetime.timedelta(hours=1)
            except ValueError:
                end = st + datetime.timedelta(hours=1)
            if (st - now).total_seconds() <= 3600 and now <= end:
                when = L["now"] if st <= now else (L["today_at"] if st.date() == now.date() else L["tomorrow_at"]).format(t=st.strftime("%H:%M"))
                att.append(dict(lvl="warn", text=f'🎥 {when}: {x["title"][:70]} — {x["svc"]}', act="", link=x["url"]))
    return dict(items=items, attention=att)


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON online meetings: official join links on the dashboard")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--selftest", nargs="+", metavar="EML")
    ap.add_argument("--ics", nargs="+", metavar="ICS")
    a = ap.parse_args(argv)
    if a.selftest:
        for p in a.selftest:
            with open(p, "rb") as f:
                it = parse_mail(f.read())
            print(os.path.basename(p)[:40], "→", it["frm"][:25], "|", it["subj"][:45], "|",
                  ", ".join(f'{x["svc"]}: {x["url"]}' for x in it["links"]) or "-", "|", ("⚠ " + str(it["warns"])) if it["warns"] else "",
                  "| .ics:", len(it["meets"]), "| time:", it["when"] or "-")
        return 0
    if a.ics:
        for p in a.ics:
            with open(p, encoding="utf-8") as f:
                for e in ics_meetings(f.read(), datetime.date.today()):
                    print(e["day"], (e["start"] or "")[11:16], e["title"][:50], "|", ", ".join(f'{x["svc"]}: {x["url"]}' for x in e["links"]) or "-")
        return 0
    cfg = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    if not (cfg.get("meetings") or {}).get("enabled"):
        print("meetings: off (config.yaml → meetings.enabled: true — docs/MEETINGS.md)")
        return 0
    run(cfg, a.data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
