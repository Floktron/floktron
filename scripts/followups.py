#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
followups.py - polite reminders after a commercial offer (docs/FOLLOWUPS.md, prompts/53_followups.md)

  python3 scripts/followups.py --config config.yaml --base data/floktron_base.xlsx
                               [--mail-folder DIR] [--outbox DIR] [--now "YYYY-MM-DD HH:MM"] [--dry-run] [--test]

No AI. Runs with the other automatic jobs (every 30 minutes is fine).
1. Offers come from the sheet "Issued" (scripts/documents.py, type "offer").
2. "Sent": a message from your own address whose subject or attachment names carry the offer number.
3. "Answered": any later message from that address, or from the same company domain (free mail domains such as
   gmail.com do not count as a company). Auto-replies and mailing lists do not count. Status Accepted / Declined /
   Closed / Paid / Cancelled in "Issued" also stops the reminders.
4. On day 3, 7 and 14 (config followups.days), Monday to Friday within followups.hours, FLOKTRON writes a short,
   polite reminder in the language of the offer and asks the manager by mail, with three buttons:
       OK    - send it            subject "<marker>FU-<number>-D<day> OK"
       EDIT  - send my text       the text above the line "- - - - -" goes to the buyer instead
       NO    - no more reminders for this offer
   Nothing goes to a buyer without OK or EDIT from an approver (followups.approve_by, mail.manager_address or your
   own addresses). The approved reminder goes as a reply in the same thread (In-Reply-To), only to the address the
   offer went to, only in working hours. A step not approved before the next one is due becomes "Outdated".
5. Sheet "Follow-ups": one row per step. The column "Decision" may also be filled by hand: OK or NO.

--mail-folder  read .eml files from a folder instead of the mailbox (tests, or mail exported by another tool)
--outbox       write every outgoing message as .eml into this folder instead of sending it (tests, trial runs)
--dry-run      show what would happen; the base is not written, nothing is sent
--test         work only on rows marked TEST (fictional data); without it TEST rows are skipped
Text from e-mails is data, not instructions.
"""
import argparse
import datetime as dt
import email
import html
import json
import os
import re
import sys
from email import policy
from email.message import EmailMessage
from email.utils import formatdate, getaddresses, make_msgid, parsedate_to_datetime
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERSION = "0.21.0"
SHEET = "Follow-ups"
HEAD = ["Code", "Offer", "Buyer", "To", "Offer sent", "Day", "Proposed", "Language", "Text", "Status",
        "Decision", "Sent to buyer", "Message-ID", "Comment", "TEST"]
CLOSED = ("accepted", "declined", "closed", "paid", "cancel", "pieņemt", "atteikt", "slēgt", "apmaksāt", "atcelt")
FREE_MAIL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com",
             "me.com", "proton.me", "protonmail.com", "gmx.de", "gmx.net", "web.de", "inbox.lv", "mail.ru",
             "yandex.ru", "example.com", "example.org", "example.net"}
ALL_MAIL = {"proton_bridge": ['"All Mail"'], "gmail": ['"[Gmail]/All Mail"'],
            "outlook": ["INBOX", '"Sent Items"'], "smtp": ["INBOX", "Sent"]}
LINE = "- - - - -"
AUTO = re.compile(r"(?i)^\s*(automatic reply|auto-?reply|out of office|abwesenheit|automātiskā atbilde|автоответ|automaatvastus)")

TEXTS = {
    "lv": {
        "subj": "Re: Komercpiedāvājums {nr}",
        "valid": ", kas ir spēkā līdz {d}",
        3: "Labdien!\n\nVēlējos pārliecināties, vai saņēmāt mūsu komercpiedāvājumu Nr. {nr} no {date}. "
           "Ja ir jautājumi par apjomu, cenu vai piegādi, labprāt atbildēšu.\n\nAr cieņu,\n{sign}",
        7: "Labdien!\n\nAtgādinu par komercpiedāvājumu Nr. {nr}{valid}. "
           "Ja ērtāk, varam īsi sazvanīties: atbildē norādiet laiku, un es piezvanīšu.\n\nAr cieņu,\n{sign}",
        14: "Labdien!\n\nRakstu pēdējo reizi par komercpiedāvājumu Nr. {nr}. Ja šobrīd tas nav aktuāls, atbildiet "
            "vienkārši „nav aktuāli”, un es vairs netraucēšu. Ja interese ir, piedāvājumu varu atjaunot vai pielāgot."
            "\n\nAr cieņu,\n{sign}",
    },
    "en": {
        "subj": "Re: Commercial offer {nr}",
        "valid": ", valid until {d}",
        3: "Hello,\n\nI wanted to make sure you received our commercial offer No. {nr} of {date}. "
           "If you have any questions about quantity, price or delivery, I will be glad to answer.\n\nBest regards,\n{sign}",
        7: "Hello,\n\nA short reminder about our offer No. {nr}{valid}. "
           "If a quick call is easier, just reply with a convenient time and I will call you.\n\nBest regards,\n{sign}",
        14: "Hello,\n\nThis is my last note about offer No. {nr}. If it is not relevant right now, simply reply "
            "\"not relevant\" and I will not write again. If you are still interested, I can renew or adjust the offer."
            "\n\nBest regards,\n{sign}",
    },
}


# ---------------------------------------------------------------- helpers
def addrs(s):
    return [a.lower() for _, a in getaddresses([str(s or "")]) if "@" in a]


def domain(a):
    return a.rsplit("@", 1)[-1].lower() if a and "@" in a else ""


def parse_dt(v):
    if isinstance(v, dt.datetime):
        return v.replace(tzinfo=None)
    if isinstance(v, dt.date):
        return dt.datetime(v.year, v.month, v.day, 9, 0)
    s = str(v or "").strip()
    for f in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            d = dt.datetime.strptime(s, f)
            return d.replace(hour=9) if len(s) <= 10 else d
        except ValueError:
            pass
    return None


def cell_text(s):
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", str(s or ""))
    return ("'" + s) if s[:1] in "=+-@" else s


def working(t, hours):
    a, b = [int(x) for x in str(hours or "08-20").split("-")]
    return t.weekday() < 5 and a <= t.hour < b


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML is needed to read config.yaml (pip install -r requirements.txt).")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------- mail in
def parse_mail(raw):
    m = email.message_from_bytes(raw, policy=policy.default)
    try:
        when = parsedate_to_datetime(m["Date"])
        when = when.astimezone().replace(tzinfo=None) if when.tzinfo else when
    except Exception:
        when = None
    files = [str(p.get_filename()) for p in m.walk() if p.get_filename()]
    body = ""
    try:
        b = m.get_body(preferencelist=("plain",))
        body = b.get_content() if b else ""
    except Exception:
        pass
    subj = str(m.get("Subject", "") or "")
    auto = bool(AUTO.match(subj) or m.get("X-Autoreply") or m.get("List-Id") or m.get("List-Unsubscribe")
                or str(m.get("Auto-Submitted", "")).lower().startswith("auto")
                or str(m.get("Precedence", "")).lower() in ("bulk", "list", "junk"))
    return dict(mid=str(m.get("Message-ID", "") or "").strip(), frm=(addrs(m.get("From")) or [""])[0],
                to=addrs(m.get("To")) + addrs(m.get("Cc")), date=when, subject=subj, files=files, body=body, auto=auto)


def mail_from_imap(mail_cfg, folders, days=60):
    from mail.read import all_messages
    seen = set()
    for raw in all_messages(mail_cfg, folders, days):
        msg = parse_mail(raw)
        if msg["mid"] not in seen:
            seen.add(msg["mid"])
            yield msg


def mail_from_folder(path):
    for name in sorted(os.listdir(path)):
        if name.lower().endswith(".eml"):
            with open(os.path.join(path, name), "rb") as f:
                yield parse_mail(f.read())


# ---------------------------------------------------------------- logic
def find_sent(offer, mails, own):
    nr = str(offer["Number"])
    stem = os.path.splitext(str(offer.get("File") or ""))[0]
    hits = []
    for m in mails:
        if m["frm"] not in own or not m["date"] or "FU-" + nr in m["subject"]:
            continue
        others = [a for a in m["to"] if a not in own]
        text = m["subject"] + " " + " ".join(m["files"])
        if others and (nr in text or (stem and stem in text)):
            hits.append((m["date"], others[0], m["mid"], m["subject"]))
    if hits:
        return min(hits)
    if str(offer.get("Status") or "").lower().startswith("sent"):        # sent another way: status by hand
        to, d = (addrs(offer.get("E-mail")) or [""])[0], parse_dt(offer.get("Date"))
        if to and d:
            return (d, to, "", "")
    return None


def find_answer(sent, to, mails, own, marker, free):
    dm = domain(to)
    for m in sorted((m for m in mails if m["date"]), key=lambda m: m["date"]):
        if m["date"] <= sent or m["frm"] in own or m["auto"] or marker in m["subject"]:
            continue
        if m["frm"] == to or (dm and dm not in free and domain(m["frm"]) == dm):
            return m
    return None


def edit_text(body):
    out = []
    for ln in body.split(LINE)[0].splitlines():
        if ln.startswith(">") or re.match(r"^(On|Am|Le|\d{1,2}[./]\d{1,2}[./]\d{2,4}) .+(wrote|schrieb|écrit|rakstīja)", ln):
            break
        out.append(ln.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def lang_of(offer, to):
    lang = str(offer.get("Language") or "").lower()
    if lang.startswith("en"):
        return "en"
    if lang.startswith("lv"):
        return "lv"
    return "lv" if domain(to).endswith(".lv") else "en"


def draft(offer, day, lang, sign, now):
    T = TEXTS[lang]
    d = parse_dt(offer.get("Date"))
    vu = parse_dt(offer.get("Due"))
    valid = T["valid"].format(d=vu.strftime("%d.%m.%Y")) if vu and vu.date() >= now.date() else ""
    return T[day].format(nr=offer["Number"], date=d.strftime("%d.%m.%Y") if d else "", valid=valid, sign=sign)


def button(label, color, to, subj, body):
    href = "mailto:%s?subject=%s&body=%s" % (to, quote(subj), quote(body))
    return (f'<a href="{href}" style="display:inline-block;background:{color};color:#fff;text-decoration:none;'
            f'padding:11px 16px;border-radius:8px;font-weight:bold;margin:4px 6px 4px 0">{label}</a>')


def approval_mail(cfg, offer, to, sent, day, code, text, now):
    mail = cfg.get("mail", {})
    col = cfg.get("colors", {}) or {}
    marker = mail.get("marker") or "FLOKTRON#"
    reply = mail.get("reply_to") or mail.get("user") or ""
    days = (now.date() - sent.date()).days
    e = html.escape
    ok_b = f"OK - send it to the buyer ({offer['Number']}, day {day}).\n\n{LINE}\n{text}"
    ed_b = f"{text}\n\n{LINE}\nChange the text ABOVE the line and send this message. Only the text above the line goes to the buyer."
    no_b = f"NO - no more reminders for {offer['Number']}.\n{LINE}"
    body = f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:620px;color:#1F2933">
<div style="background:{col.get('main', '#1A365D')};color:#fff;padding:14px 18px;border-radius:10px 10px 0 0"><b>FLOKTRON · reminder after an offer</b></div>
<div style="border:1px solid #D9DEE5;border-top:0;padding:16px 18px;border-radius:0 0 10px 10px">
<p style="margin:0 0 10px"><b>{e(str(offer.get('Buyer') or ''))}</b> has not answered offer <b>{e(str(offer['Number']))}</b>
(sent {sent:%d.%m.%Y} to {e(to)}, {days} days ago). Suggested reply in the same thread:</p>
<div style="background:#F3F3F3;border-left:4px solid {col.get('ok', '#4A9928')};padding:12px 14px;white-space:pre-wrap;font-size:14px">{e(text)}</div>
<p style="margin:14px 0 4px">{button('✅ Send', col.get('ok', '#4A9928'), reply, f'{marker}{code} OK', ok_b)}{button('✏️ My text', col.get('main', '#1A365D'), reply, f'{marker}{code} EDIT', ed_b)}{button('⏸ No more reminders', col.get('neutral', '#717171'), reply, f'{marker}{code} NO', no_b)}</p>
<p style="color:#717171;font-size:12px;margin:10px 0 0">Nothing goes to the buyer without your button. If the buyer answers first,
the reminder is withdrawn. Sending only in working hours. Code: {marker}{code}</p></div></div>"""
    plain = (f"FLOKTRON · reminder for offer {offer['Number']} (day {days})\nBuyer: {offer.get('Buyer')} · {to}\n\n{text}\n\n"
             f"Reply to {reply} with subject \"{marker}{code} OK\" (send) / \"... EDIT\" (your text above {LINE}) / \"... NO\".")
    approver = (cfg.get("followups", {}) or {}).get("approve_by") or mail.get("manager_address") or reply
    return build(cfg, approver, f"{marker}{code} · reminder for offer {offer['Number']} — approve?", plain, body)


def build(cfg, to, subject, text, html_body=None, in_reply_to=""):
    mail = cfg.get("mail", {})
    sender = mail.get("from") or mail.get("user") or ""
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, to, subject
    msg["Reply-To"] = mail.get("reply_to") or sender
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=domain(sender) or "floktron.local")
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(text)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    return msg


class Out:
    """Send through mail/send.py, or write .eml files into --outbox."""

    def __init__(self, cfg, outbox, now):
        self.cfg, self.outbox, self.now, self.sender = cfg, outbox, now, None

    def send(self, msg, tag):
        if self.outbox:
            os.makedirs(self.outbox, exist_ok=True)
            with open(os.path.join(self.outbox, f"{self.now:%Y-%m-%d_%H%M}_{tag}.eml"), "wb") as f:
                f.write(bytes(msg))
            return
        from mail.send import Sender
        if self.sender is None:
            self.sender = Sender(self.cfg.get("mail", {})).__enter__()
        self.sender.send(msg)

    def close(self):
        if self.sender is not None:
            self.sender.__exit__(None, None, None)


def rows(wb, name):
    if name not in wb.sheetnames:
        return [], []
    it = wb[name].iter_rows()
    head = [str(c.value or "").strip() for c in next(it, [])]
    return head, [r for r in it if any(c.value not in (None, "") for c in r)]


def run(cfg, base, mails, now, outbox=None, dry=False, test=False, log=print):
    import openpyxl
    import safe_xlsx  # noqa: F401  outside text never becomes a formula
    from openpyxl.styles import Font, PatternFill
    fcfg = cfg.get("followups", {}) or {}
    mail = cfg.get("mail", {}) or {}
    marker = mail.get("marker") or "FLOKTRON#"
    days = sorted(int(d) for d in (fcfg.get("days") or [3, 7, 14]))
    hours = fcfg.get("hours") or "08-20"
    free = FREE_MAIL | {d.lower() for d in (fcfg.get("free_mail_domains") or [])}
    if test:
        free -= {"example.com", "example.org", "example.net"}
    own = {a.lower() for a in (mail.get("user"), mail.get("from"), mail.get("reply_to"),
                               (cfg.get("documents") or {}).get("email")) if a}
    approvers = own | {a.lower() for a in (fcfg.get("approve_by"), mail.get("manager_address")) if a}
    sign = fcfg.get("signature") or "\n".join(x for x in (
        (cfg.get("company") or {}).get("name", ""), (cfg.get("documents") or {}).get("phone", ""),
        (cfg.get("documents") or {}).get("email", "") or mail.get("from", "")) if x)
    mails = [m for m in mails if m["date"]]

    wb = openpyxl.load_workbook(base)
    ih, irs = rows(wb, "Issued")
    offers = []
    for r in irs:
        d = {h: (r[i].value if i < len(r) else None) for i, h in enumerate(ih) if h}
        if str(d.get("Type") or "") == "offer" and bool(d.get("TEST")) == bool(test):
            offers.append(d)
    if not offers and SHEET not in wb.sheetnames:
        return dict(offers=0, proposed=0, sent=0, answered=0)
    if SHEET not in wb.sheetnames:
        ws = wb.create_sheet(SHEET)
        ws.append(HEAD)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1A365D")
    ws = wb[SHEET]
    col = {h: i for i, h in enumerate(HEAD)}
    steps = {str(r[0].value): r for r in ws.iter_rows(min_row=2) if r[0].value}
    get = lambda r, k: r[col[k]].value
    def put(r, k, v): r[col[k]].value = v

    # 1) decisions: button replies from an approver, or the Decision column
    rx = re.compile(re.escape(marker) + r"(FU-\S+?-D\d{1,3})\s+(OK|EDIT|NO)\b", re.I)
    dec = []
    for m in mails:
        hit = rx.search(m["subject"])
        if hit and m["frm"] in approvers:
            dec.append((m["date"], hit.group(1), hit.group(2).upper(), edit_text(m["body"])))
    for code, r in steps.items():
        v = str(get(r, "Decision") or "").strip().upper()
        if v in ("OK", "NO") and get(r, "Status") == "Waiting for OK":
            dec.append((now, code, v, ""))
    for when, code, act, text in sorted(dec):
        r = steps.get(code)
        if r is None or get(r, "Status") != "Waiting for OK" or when < (parse_dt(get(r, "Proposed")) or now):
            continue
        put(r, "Decision", act)
        if act == "NO":
            put(r, "Status", "Not needed")
            put(r, "Comment", f"no more reminders ({when:%d.%m %H:%M})")
        elif act == "EDIT" and len(text) < 15:
            put(r, "Comment", "EDIT without text — waiting for OK or a new text")
        else:
            if act == "EDIT":
                put(r, "Text", cell_text(text))
            put(r, "Status", "Approved")

    out = Out(cfg, outbox if not dry else None, now)
    n = dict(offers=len(offers), proposed=0, sent=0, answered=0)
    try:
        for off in offers:
            nr = str(off["Number"])
            hit = find_sent(off, mails, own)
            if not hit:
                continue
            sent, to, mid, subj = hit
            mine = sorted((r for r in steps.values() if str(get(r, "Offer")) == nr), key=lambda r: str(get(r, "Code")))
            stop = None
            if any(str(off.get("Status") or "").lower().startswith(c) for c in CLOSED):
                stop = f"status {off.get('Status')}"
            ans = find_answer(sent, to, mails, own, marker, free)
            if ans:
                stop = f"Buyer answered {ans['date']:%d.%m %H:%M}"
            if any(get(r, "Status") == "Not needed" for r in mine):
                stop = stop or "Not needed"
            lang = lang_of(off, to)
            if stop:
                for r in mine:
                    if get(r, "Status") in ("Waiting for OK", "Approved"):
                        put(r, "Status", "Stopped: " + stop)
                code = f"FU-{nr}-D0"
                if ans and code not in steps:
                    ws.append([code, nr, cell_text(off.get("Buyer")), to, f"{sent:%Y-%m-%d %H:%M}", "", f"{now:%Y-%m-%d %H:%M}",
                               lang, "", stop, "", "", "", "", "TEST" if off.get("TEST") else ""])
                    steps[code] = ws[ws.max_row]
                    n["answered"] += 1
                continue
            for r in mine:                                         # approved → buyer, in working hours
                if get(r, "Status") != "Approved" or not working(now, hours):
                    continue
                s = subj or TEXTS[lang]["subj"].format(nr=nr)
                if not s.lower().startswith(("re:", "aw:", "atb.:")):
                    s = "Re: " + s
                msg = build(cfg, to, s, str(get(r, "Text") or ""), in_reply_to=mid)
                if dry:
                    log(f"would send to {to}: {get(r, 'Code')}")
                    continue
                out.send(msg, f"{get(r, 'Code')}_to_buyer")
                put(r, "Status", "Sent")
                put(r, "Sent to buyer", f"{now:%Y-%m-%d %H:%M}")
                put(r, "Message-ID", msg["Message-ID"])
                n["sent"] += 1
            age = (now - sent).total_seconds() / 86400
            due = [d for d in days if age >= d]
            if not due or not working(now, hours):
                continue
            day = due[-1]
            code = f"FU-{nr}-D{day}"
            last = max([parse_dt(get(r, "Sent to buyer")) for r in mine if parse_dt(get(r, "Sent to buyer"))], default=None)
            if code in steps or (last and (now - last).total_seconds() < 3 * 86400):
                continue
            for r in mine:
                if get(r, "Status") == "Waiting for OK":
                    put(r, "Status", "Outdated")
            text = draft(off, day, lang, sign, now) if day in TEXTS[lang] else draft(off, 7, lang, sign, now)
            ws.append([code, nr, cell_text(off.get("Buyer")), to, f"{sent:%Y-%m-%d %H:%M}", day, f"{now:%Y-%m-%d %H:%M}",
                       lang, cell_text(text), "Waiting for OK", "", "", "", "", "TEST" if off.get("TEST") else ""])
            steps[code] = ws[ws.max_row]
            n["proposed"] += 1
            if dry:
                log(f"would ask approval: {code}")
            else:
                out.send(approval_mail(cfg, off, to, sent, day, code, text, now), f"{code}_approve")
    finally:
        out.close()
    if not dry:
        wb.save(base)
    return n


def main():
    ap = argparse.ArgumentParser(description="FLOKTRON reminders after an offer (3 / 7 / 14 days, only after OK)")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--base", default=os.path.join("data", "floktron_base.xlsx"))
    ap.add_argument("--mail-folder", help="read .eml files from this folder instead of the mailbox")
    ap.add_argument("--outbox", help="write outgoing messages as .eml here instead of sending")
    ap.add_argument("--now", help='"YYYY-MM-DD HH:MM" (tests)')
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true", help="only rows marked TEST (fictional data)")
    a = ap.parse_args()
    cfg = load_yaml(a.config) if os.path.exists(a.config) else {}
    if not (cfg.get("followups") or {}).get("enabled", True) and not a.test:
        print("followups.enabled is false in config.yaml — nothing to do.")
        return 0
    if not os.path.exists(a.base):
        sys.exit(f"No base {a.base}")
    now = dt.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else dt.datetime.now()
    if a.mail_folder:
        mails = list(mail_from_folder(a.mail_folder))
    else:
        mcfg = cfg.get("mail", {}) or {}
        folders = (cfg.get("followups") or {}).get("imap_folders") or ALL_MAIL.get(mcfg.get("provider", "smtp"), ["INBOX"])
        mails = list(mail_from_imap(mcfg, folders))
    n = run(cfg, a.base, mails, now, outbox=a.outbox, dry=a.dry_run, test=a.test)
    print(json.dumps(n))
    return 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    raise SystemExit(main())
