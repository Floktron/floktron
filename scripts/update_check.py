# -*- coding: utf-8 -*-
"""FLOKTRON · update_check.py — is there a newer FLOKTRON? Tell the manager what was fixed.

Once a day (it rides along with the morning run) FLOKTRON asks GitHub for the list of its own releases:
one anonymous HTTPS request to api.github.com — no account, no ID, no data about you or your company.
If a release is newer than the version on this computer, the manager gets ONE short message per new version:
by e-mail (mail.manager_address) and, if the Telegram bot is on, in the bot (data/update_notice.json).
Only release news: what was fixed and added. No advertising, no support links. To update, tell your AI
assistant "update FLOKTRON" (prompts/58_update.md — backup first, your settings and data stay).

Switch it off: updates.check: false in config/config.yaml. See docs/UPDATES.md.

Usage:
    python3 scripts/update_check.py             # once a day; mail + bot notice when a new version exists
    python3 scripts/update_check.py --force     # check now, even if checked today
    python3 scripts/update_check.py --dry       # print only, send nothing, change nothing
    python3 scripts/update_check.py --releases tests/fixtures/updates/releases.json   # offline (tests)
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
import urllib.request
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

REPO = "koagu-element/floktron"
API = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
UA = "FLOKTRON-update-check"          # the only header sent besides Accept; nothing about the user

T = {
    "en": dict(subject="FLOKTRON {new} is out — you have {cur}", head="A newer FLOKTRON is out",
               intro="This computer runs FLOKTRON {cur}. Newer: {new}. What changed:",
               how='To update, tell your AI assistant: "update FLOKTRON". It makes a backup first; your settings and data stay.',
               off="Only release news, at most one message per version. Switch off: updates.check: false in config.yaml."),
    "lv": dict(subject="Iznākusi FLOKTRON {new} — jums ir {cur}", head="Iznākusi jaunāka FLOKTRON versija",
               intro="Šajā datorā darbojas FLOKTRON {cur}. Jaunākā: {new}. Kas mainījies:",
               how='Lai atjauninātu, pasakiet savam MI asistentam: "atjaunini FLOKTRON". Vispirms tiek izveidota rezerves kopija; iestatījumi un dati paliek.',
               off="Tikai ziņas par versijām, ne vairāk kā viena ziņa katrai versijai. Izslēgt: updates.check: false failā config.yaml."),
    "ru": dict(subject="Вышла FLOKTRON {new} — у вас {cur}", head="Вышла новая версия FLOKTRON",
               intro="На этом компьютере FLOKTRON {cur}. Новая: {new}. Что изменилось:",
               how="Чтобы обновить, скажите своему ИИ-ассистенту: «обнови FLOKTRON». Сначала он сделает резервную копию; настройки и данные останутся.",
               off="Только новости версий, не больше одного сообщения на версию. Выключить: updates.check: false в config.yaml."),
    "de": dict(subject="FLOKTRON {new} ist da — Sie haben {cur}", head="Eine neuere FLOKTRON-Version ist da",
               intro="Auf diesem Computer läuft FLOKTRON {cur}. Neu: {new}. Was sich geändert hat:",
               how="Zum Aktualisieren sagen Sie Ihrem KI-Assistenten: „FLOKTRON aktualisieren“. Zuerst wird gesichert; Einstellungen und Daten bleiben.",
               off="Nur Versionsnachrichten, höchstens eine pro Version. Abschalten: updates.check: false in config.yaml."),
    "lt": dict(subject="Išleista FLOKTRON {new} — jūs turite {cur}", head="Išleista naujesnė FLOKTRON versija",
               intro="Šiame kompiuteryje veikia FLOKTRON {cur}. Naujesnė: {new}. Kas pasikeitė:",
               how="Norėdami atnaujinti, pasakykite savo DI asistentui: „atnaujink FLOKTRON“. Pirmiausia daroma atsarginė kopija; nustatymai ir duomenys lieka.",
               off="Tik žinios apie versijas, ne daugiau kaip viena žinutė vienai versijai. Išjungti: updates.check: false faile config.yaml."),
    "et": dict(subject="FLOKTRON {new} on väljas — teil on {cur}", head="Uuem FLOKTRON on väljas",
               intro="Selles arvutis töötab FLOKTRON {cur}. Uuem: {new}. Mis muutus:",
               how="Uuendamiseks öelge oma tehisintellekti assistendile: „uuenda FLOKTRON“. Kõigepealt tehakse varukoopia; seaded ja andmed jäävad.",
               off="Ainult versiooniuudised, kõige rohkem üks sõnum versiooni kohta. Väljalülitamine: updates.check: false failis config.yaml."),
    "es": dict(subject="Ya está FLOKTRON {new} — usted tiene {cur}", head="Hay una versión más nueva de FLOKTRON",
               intro="Este ordenador usa FLOKTRON {cur}. Nueva: {new}. Qué ha cambiado:",
               how="Para actualizar, diga a su asistente de IA: «actualiza FLOKTRON». Primero hace una copia de seguridad; su configuración y sus datos se mantienen.",
               off="Solo noticias de versiones, como máximo un mensaje por versión. Desactivar: updates.check: false en config.yaml."),
    "it": dict(subject="È uscito FLOKTRON {new} — Lei ha {cur}", head="È uscita una versione più recente di FLOKTRON",
               intro="Su questo computer gira FLOKTRON {cur}. Nuova: {new}. Cosa è cambiato:",
               how="Per aggiornare, dica al Suo assistente IA: «aggiorna FLOKTRON». Prima viene fatto un backup; impostazioni e dati restano.",
               off="Solo notizie sulle versioni, al massimo un messaggio per versione. Disattivare: updates.check: false in config.yaml."),
    "fr": dict(subject="FLOKTRON {new} est disponible — vous avez {cur}", head="Une version plus récente de FLOKTRON est disponible",
               intro="Cet ordinateur utilise FLOKTRON {cur}. Nouvelle : {new}. Ce qui a changé :",
               how="Pour mettre à jour, dites à votre assistant IA : « mets à jour FLOKTRON ». Une sauvegarde est faite d'abord ; vos réglages et vos données restent.",
               off="Uniquement les nouvelles versions, au plus un message par version. Désactiver : updates.check: false dans config.yaml."),
}

# points about donations or partners are not release news — they never go into the message
NOT_NEWS = re.compile(r"support the project|donat|sponsor|funding|stripe|paypal|crypto|wallet|partner link|affiliate", re.I)
MAX_RELEASES = 5        # in one message: the newest five; the rest — one link
MAX_POINTS = 3          # per release: the title + up to three points
MAX_LEN = 220           # characters per point


def vtuple(v):
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", str(v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def local_version(root=ROOT):
    """The version of this copy — the first '## X.Y.Z' of CHANGELOG.md (same rule as scripts/move.py)."""
    p = os.path.join(root, "CHANGELOG.md")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            m = re.match(r"## (\d+\.\d+\.\d+)", line)
            if m:
                return m.group(1)
    return None


def fetch_releases(timeout=20):
    req = urllib.request.Request(API, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def clean(s):
    """Release text is plain information: drop markdown links/markup, keep it short."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(s or ""))
    s = re.sub(r"https?://\S+", "", s)            # no links in the message besides the releases page
    s = re.sub(r"\*{1,3}|`", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= MAX_LEN else s[:MAX_LEN - 1].rstrip() + "…"


def summarize(rel):
    """{version, title, points[]} from a GitHub release (its body is the CHANGELOG section)."""
    v = (rel.get("tag_name") or "").lstrip("v")
    title = clean(re.sub(r"^FLOKTRON\s*", "", rel.get("name") or v))
    points, cur = [], None
    for ln in (rel.get("body") or "").splitlines():
        m = re.match(r"\s*[-*]\s+(.*)", ln)
        if m:
            cur = [m.group(1)]
            points.append(cur)
        elif cur is not None and ln.startswith("  ") and ln.strip():
            cur.append(ln.strip())          # a point that goes on in the next line
        else:
            cur = None
    points = [clean(" ".join(p)) for p in points]
    points = [p for p in points if p and not NOT_NEWS.search(p)]
    return dict(version=v, title=title, points=points[:MAX_POINTS])


def newer_releases(releases, current):
    cur = vtuple(current)
    out = []
    for r in releases or []:
        if r.get("draft") or r.get("prerelease"):
            continue
        t = vtuple(r.get("tag_name"))
        if t and cur and t > cur:
            out.append((t, summarize(r)))
    return [s for _, s in sorted(out, key=lambda x: x[0], reverse=True)]


def build(news, current, lang):
    L = T.get(lang) or T["en"]
    new = news[0]["version"]
    shown = [n for n in news if not NOT_NEWS.search(n["title"])][:MAX_RELEASES]
    lines = [L["intro"].format(cur=current, new=new), ""]
    for n in shown:
        lines.append(f"• {n['title']}")
        lines += [f"   – {p}" for p in n["points"]]
    if len(news) > MAX_RELEASES and len(shown) == MAX_RELEASES:
        lines.append(f"• … +{len(news) - len(shown)}: {RELEASES_PAGE}")
    lines += ["", L["how"], RELEASES_PAGE, "", L["off"]]
    text = "\n".join(lines)
    li = "".join(f"<li><b>{html.escape(n['title'])}</b>"
                 + ("<ul>" + "".join(f"<li>{html.escape(p)}</li>" for p in n["points"]) + "</ul>" if n["points"] else "")
                 + "</li>" for n in shown)
    more = (f'<li>… +{len(news) - len(shown)} — <a href="{RELEASES_PAGE}">{RELEASES_PAGE}</a></li>'
            if len(news) > MAX_RELEASES and len(shown) == MAX_RELEASES else "")
    body = f"""<div style="font-family:Arial;max-width:640px;color:#1A365D">
<div style="background:#1A365D;color:#fff;padding:12px 16px;border-radius:8px 8px 0 0"><b>{html.escape(L['head'])}</b><br>
<small>{html.escape(current)} → {html.escape(new)}</small></div>
<div style="background:#f3f3f3;padding:12px 16px"><p>{html.escape(L['intro'].format(cur=current, new=new))}</p><ul>{li}{more}</ul>
<p>{html.escape(L['how'])}<br><a href="{RELEASES_PAGE}">{RELEASES_PAGE}</a></p>
<p style="color:#717171;font-size:12px">{html.escape(L['off'])}</p></div></div>"""
    return L["subject"].format(cur=current, new=new), text, body


def load_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Is there a newer FLOKTRON? Tell the manager once per version.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--data", default=os.path.join(ROOT, "data"))
    ap.add_argument("--releases", help="read releases from this JSON file instead of GitHub (offline, tests)")
    ap.add_argument("--current", help="pretend this version runs here (tests)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)

    cfg = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    up = cfg.get("updates") or {}
    if up.get("check", True) is False:
        print("updates.check is false — no check.")
        return 0
    lang = (up.get("language") or (cfg.get("company") or {}).get("language") or "en").lower()
    state_p = os.path.join(a.data, "update_state.json")
    state = load_json(state_p, {})
    today = datetime.date.today().isoformat()
    if state.get("checked") == today and not a.force and not a.releases:
        print("already checked today.")
        return 0

    current = a.current or local_version()
    if not current:
        print("no CHANGELOG.md here — version unknown, no check.")
        return 0
    try:
        releases = load_json(a.releases, []) if a.releases else fetch_releases()
    except Exception as e:      # offline, GitHub down, rate limit — never fails the morning run
        print(f"update check: GitHub not reachable ({type(e).__name__}) — next try tomorrow.")
        return 0
    news = newer_releases(releases, current)
    if not a.dry:
        state.update(checked=today, current=current, latest=(news[0]["version"] if news else current))
    if not news:
        print(f"FLOKTRON {current} is the newest version.")
        if not a.dry:
            save_json(state_p, state)
        return 0
    new = news[0]["version"]
    subject, text, body = build(news, current, lang)
    print(subject)
    print(text)
    if a.dry:
        return 0
    if state.get("notified") == new:
        print(f"the manager already knows about {new}.")
        save_json(state_p, state)
        return 0

    # Telegram: the bot sends this file to manager_chat_ids once (scripts/bot/telegram_bot.py)
    delivered = False
    tg = cfg.get("telegram") or {}
    if tg.get("enabled") and up.get("telegram", True) is not False:
        save_json(os.path.join(a.data, "update_notice.json"),
                  dict(version=new, current=current, text=f"🆕 {subject}\n\n{text}", created=today, sent=False))
        print("bot notice saved: data/update_notice.json")
        delivered = True
    # e-mail to the manager
    mail = cfg.get("mail") or {}
    to = mail.get("manager_address")
    if to and up.get("mail", True) is not False:
        try:
            from mail.send import MailError, Sender
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = mail.get("from") or mail.get("user"), to, subject
            msg.set_content(text)
            msg.add_alternative(body, subtype="html")
            with Sender(mail) as s:
                s.send(msg)
            print("sent →", to)
            delivered = True
        except Exception as e:      # mail not set up yet — the bot notice and the log still tell
            print(f"update mail not sent: {e}")
    if delivered:               # nothing reached the manager → try again tomorrow
        state["notified"] = new
    save_json(state_p, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
