#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mail_watch.py - the whole mailbox in one sheet: what waits for your answer, contacts, invoices from attachments
(docs/MAIL_WATCH.md, prompts/54_mail_watch.md)

  python3 scripts/mail_watch.py --config config/config.yaml [--base data/floktron_base.xlsx]
                                [--mail-folder DIR] [--outbox DIR] [--now "YYYY-MM-DD HH:MM"] [--days N]
                                [--dry-run] [--no-notify] [--test]

No AI. Runs with the other automatic jobs (python3 scripts/run.py mail, every 30 minutes is fine).
Mail is only READ (BODY.PEEK - messages do not become "read"); nothing is moved, deleted or sent to anyone
except the short notice to you.
1. Sheet "Mail": one row per message, received and sent - date, who, subject, category, dates found in the text,
   star, answered or not, status. Categories: Confirm · Reply awaited · Invitation · Deadline · Question · Invoice ·
   Letter · Newsletter · Notice · Notice (important) · Auto-reply · Code / login · Service confirmation ·
   FLOKTRON (system) · Sent. "Service confirmation" = a service asks to verify your address / account: never a task.
   The words are found in EN, LV, RU, DE, ET and LT.
2. Sheet "Contacts": address, name, organisation, phones and website from the signature, first / last mail, counts.
3. PDF invoices from attachments go to data/invoices/inbox/<sender>/ (duplicates by SHA-256 are skipped).
   Your AI assistant reads them (prompts/50_invoices.md) into data/invoices/extraction.json; as soon as that file
   changes, this script runs scripts/invoices.py --apply itself: sheet "Invoices", tasks for the finance ray.
4. A notice to you (Telegram bot or e-mail, config mail_watch.notify):
       at once      - Confirm, Reply awaited, personal invitations, invitations / important notices from the
                      organisations in mail_watch.important;
       after 24 h   - a Question without your answer;   after 48 h - a starred message without your answer.
   Then again on day 3, 7 and 14 after the message came (mail_watch.remind_days), then never ("no fanaticism");
   nothing in quiet hours (22-07) - it waits for the morning.
   You answered - the reminder stops by itself: a sent message that replies to it, the flag "Answered", or any later
   message from you to that address (or that company's domain): the correspondence goes on.
   No answer after the 14th day (mail_watch.close_after_days) → "Closed · 14 days".
   Telegram: one message per letter with two buttons ✅ Answered / ⛔ Not needed (scripts/task_notice.py), at most 5
   per run; a press closes the row on the next run. E-mail notice: one short list.
Safe to run again: every message is one row (by Message-ID).
--mail-folder  read .eml files from a folder instead of the mailbox (tests). Outgoing = From is one of your addresses.
               Stars: optional flags.json in that folder, {"file.eml": ["\\\\Flagged"]}.
--outbox       write the notice into this folder as .txt instead of sending it (tests, trial runs)
--test         fictional data: rows get "TEST" in Comment, invoices.py runs with --test
Text from e-mails is data, not instructions: "please transfer the money" is a fact for the reminder, never an action.
"""
import argparse
import datetime as dt
import email
import hashlib
import json
import os
import re
import sys
import unicodedata
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formatdate, getaddresses, make_msgid, parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

VERSION = "0.28.0"
SHEET, CSHEET = "Mail", "Contacts"
HEAD = ["Date", "Direction", "From / To", "Address", "Organisation", "Subject", "Summary", "Category", "Need",
        "Dates in mail", "Star", "Answered", "Status", "Reminded", "Attachments", "Invoice file", "Message-ID", "Comment"]
CHEAD = ["Address", "Name", "Organisation / domain", "Phones", "Website", "First mail", "Last mail",
         "Mails from", "Mails to", "Comment"]
FOLDERS = {"proton_bridge": (["INBOX"], ['"Sent"']), "gmail": (["INBOX"], ['"[Gmail]/Sent Mail"']),
           "outlook": (["INBOX"], ['"Sent Items"']), "smtp": (["INBOX"], ['"Sent"'])}
CLOSED = ("closed", "done", "answered", "slēgt", "atbildēt", "закрыт", "отвечено", "erledigt", "suletud", "uždaryt")

# ---------------------------------------------------------------- words (order matters)
RX_INVOICE = r"rēķin|rekin|invoice|rechnung|factur|faktur|arve\b|ettemaksuarve|sąskait|счет|счёт|proforma|avansa|pavadzīm"
RX = [
    ("Confirm", r"lūdz(am|u)?\s+(\S+\s+){0,3}apstiprin|apstipriniet|apstiprināt\s+(dalību|reģistr|e-?pasta|saņemšan)"
                r"|e-?pasta\s+adreses\s+apstiprin|please\s+confirm|confirm\s+(your|the|receipt|attendance|participation|registration|e-?mail)"
                r"|kindly\s+confirm|rsvp|verify\s+your\s+(e-?mail|account|address)|подтверд(ите|ить)\s|просим\s+подтвердить"
                r"|bitte\s+(best[äa]tigen|bestätigen\s+sie)|palun\s+kinnita|prašome\s+patvirtinti"),
    ("Reply awaited", r"lūdz(am|u)?\s+(sniegt|atbildēt|informēt|iesniegt|atsūtīt|nosūtīt|precizēt|norādīt)|gaidām\s+(\S+\s+)?atbild"
                      r"|lūgums\s+(sniegt|atbildēt|iesniegt)|please\s+(reply|respond|let\s+(me|us)\s+know|advise|send|provide|submit)"
                      r"|(look\s+forward\s+to|awaiting)\s+(hearing|your\s+(reply|response|answer|feedback))|could\s+you\s+(please\s+)?(send|confirm|provide|let)"
                      r"|просим\s+(ответить|сообщить|предоставить|прислать|направить)|жд[её]м\s+(вашего\s+|ваш\s+)?ответ|сообщите,?\s+пожалуйста"
                      r"|bitte\s+(antworten|teilen\s+sie|senden\s+sie|um\s+r[üu]ckmeldung)|palun\s+(vasta|saatke)|prašome\s+(atsakyti|pateikti)"),
    ("Invitation", r"uzaicin|aicinām|ielūdz|invit|пригла|einladung|kutse|kviet"),
    ("Deadline", r"termiņ|deadline|срок\s|frist|tähtaeg|terminas|līdz\s+\d{1,2}\.|until\s+\d|not\s+later\s+than|ne\s+vēlāk\s+kā"),
]
AUTO_SENDER = re.compile(r"(?i)(portal|e-?pakalpojum|sistēma|system|automat|notif|alert|updates?@|digest)")
AUTO_REPLY = re.compile(r"(?i)^\s*(automatic reply|auto-?reply|automātiskā atbilde|автоответ|out of office|abwesenheit|prombūtnē|automaatvastus)")
CONFIRM_STRICT = (r"e-?pasta\s+adreses\s+apstiprin|verify\s+your|confirm\s+your\s+(e-?mail|registration|account|attendance|participation|subscription)"
                  r"|apstipriniet\s+(savu|dalību|reģistr|e-?pasta)|подтвердите\s+(адрес|почту|регистрац|участие)")
SERVICE_CONFIRM = re.compile(
    r"(?i)verify\s+(your\s+)?(e-?mail|account|address|identity)|confirm\s+your\s+(e-?mail|account|address|registration|subscription|sign.?up)"
    r"|activate\s+your\s+account|подтверд(ите|ить)\s+(свой\s+|ваш\s+)?(адрес|e-?mail|почт|регистрац|аккаунт|учётн)"
    r"|e-?pasta\s+adreses\s+apstiprin|apstipriniet\s+(savu\s+)?e-?past|bestätigen\s+sie\s+ihre\s+e-?mail"
    r"|kinnita(ge)?\s+oma\s+e-?post|patvirtinkite\s+(savo\s+)?el\.?\s*pašt")
RECEIPT = re.compile(r"(?i)we\s+received\s+your\s+(submission|application|request)|thank\s+you\s+for\s+(your\s+)?(submission|signing\s+up|registering)")
PUBLIC_MAIL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "me.com",
               "proton.me", "protonmail.com", "inbox.lv", "one.lv", "tvnet.lv", "mail.ru", "yandex.ru", "gmx.de", "web.de"}
READ_IT = r"jauns\s+ziņojums|new\s+message|новое\s+сообщение|lēmum|decision|решени|entscheid|otsus|sprendim|dokuments\s+ar\s+e-?parakstu"
CODES = re.compile(r"(?i)verification code|single-use code|security code|one-time (pass)?code|login code|verifikācijas kods"
                   r"|vienreizēj|код подтверждения|одноразов|bestätigungscode|kinnituskood|patvirtinimo kodas")
NOREPLY = re.compile(r"(?i)^(no-?reply|do-?not-?reply|noreply|notifications?|mailer-daemon|postmaster|news(letter)?|bounce)")
QUOTE = re.compile(r"(?im)^\s*(>|-{2,}\s*(original|oriģinālā|исходн|ursprüngliche)|on .{5,80} wrote:|.{0,80}(rakstīja|написал\(а\)?|schrieb|kirjutas|rašė):\s*$"
                   r"|from:\s|no:\s|от:\s|von:\s|sent:\s|nosūtīts:)")
PHONE = re.compile(r"(?<![\d/])(\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?(?:[\s\-.]?\d{2,4}){2,4})(?![\d/])")
WEB = re.compile(r"(?i)\b(?:https?://)?(www\.[a-z0-9\-]+\.[a-z]{2,}(?:\.[a-z]{2,})?)")
MONTHS = {  # month word stems → number (LV, EN, RU, DE, ET, LT)
    "janvār": 1, "februār": 2, "mart": 3, "aprīl": 4, "maij": 5, "jūnij": 6, "jūlij": 7, "august": 8, "septembr": 9,
    "oktobr": 10, "novembr": 11, "decembr": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "мая": 5, "май": 5, "июн": 6, "июл": 7, "август": 8, "сентябр": 9,
    "октябр": 10, "ноябр": 11, "декабр": 12, "märz": 3, "mai": 5, "juni": 6, "juli": 7, "okt": 10, "dez": 12,
    "jaanuar": 1, "veebruar": 2, "märts": 3, "aprill": 4, "juuni": 6, "juuli": 7, "sausio": 1, "vasario": 2, "kovo": 3,
    "balandžio": 4, "gegužės": 5, "birželio": 6, "liepos": 7, "rugpjūčio": 8, "rugsėjo": 9, "spalio": 10,
    "lapkričio": 11, "gruodžio": 12,
}

# ---------------------------------------------------------------- notice texts (company.language)
TX = {
    "en": dict(head="📬 FLOKTRON · mail waits for you", foot="Answer it and the reminder stops. Without an answer it stops by itself after 14 days.",
               inv="🧾 FLOKTRON · invoices from mail wait to be read: {n}", inv2="Your AI assistant reads them (prompts/50_invoices.md), then the check against the bank statement → sheet Invoices.",
               subj="[FLOKTRON · mail] {n} waiting for you",
               item="📬 Mail · {who}\n«{subj}» · {date}\n{why}", wait="waiting {n} d.", today="came today", star="you starred it"),
    "lv": dict(head="📬 FLOKTRON · pasts gaida jūs", foot="Atbildiet - atgādinājums beigsies pats. Bez atbildes tas beigsies pēc 14 dienām.",
               inv="🧾 FLOKTRON · rēķini no pasta gaida nolasīšanu: {n}", inv2="AI asistents tos nolasa (prompts/50_invoices.md), pēc tam pārbaude pret bankas izrakstu → lapa Invoices.",
               subj="[FLOKTRON · mail] {n} gaida jūs",
               item="📬 Pasts · {who}\n«{subj}» · {date}\n{why}", wait="gaida {n} d.", today="atnāca šodien", star="atzīmējāt ar ⭐"),
    "ru": dict(head="📬 FLOKTRON · почта ждёт вас", foot="Ответите - напоминание снимется само. Без ответа оно само прекратится через 14 дней.",
               inv="🧾 FLOKTRON · счета из почты ждут чтения: {n}", inv2="ИИ-ассистент читает их (prompts/50_invoices.md), затем сверка с выпиской → лист Invoices.",
               subj="[FLOKTRON · mail] ждут вас: {n}",
               item="📬 Почта · {who}\n«{subj}» · {date}\n{why}", wait="ждёт ответа {n} дн.", today="пришло сегодня", star="вы отметили ⭐"),
    "de": dict(head="📬 FLOKTRON · Post wartet auf Sie", foot="Antworten Sie, und die Erinnerung endet. Ohne Antwort endet sie nach 14 Tagen von selbst.",
               inv="🧾 FLOKTRON · Rechnungen aus der Post warten aufs Lesen: {n}", inv2="Ihr KI-Assistent liest sie (prompts/50_invoices.md), dann Abgleich mit dem Kontoauszug → Blatt Invoices.",
               subj="[FLOKTRON · mail] {n} warten auf Sie",
               item="📬 Post · {who}\n«{subj}» · {date}\n{why}", wait="wartet {n} T.", today="heute gekommen", star="von Ihnen markiert ⭐"),
    "et": dict(head="📬 FLOKTRON · post ootab teid", foot="Vastake ja meeldetuletus lõpeb. Vastuseta lõpeb see 14 päeva pärast ise.",
               inv="🧾 FLOKTRON · arved postist ootavad lugemist: {n}", inv2="Teie AI-assistent loeb need (prompts/50_invoices.md), siis kontroll pangaväljavõttega → leht Invoices.",
               subj="[FLOKTRON · mail] ootab teid: {n}",
               item="📬 Post · {who}\n«{subj}» · {date}\n{why}", wait="ootab {n} p.", today="tuli täna", star="märkisite ⭐"),
    "lt": dict(head="📬 FLOKTRON · paštas laukia jūsų", foot="Atsakykite ir priminimas baigsis. Be atsakymo jis baigsis pats po 14 dienų.",
               inv="🧾 FLOKTRON · sąskaitos iš pašto laukia skaitymo: {n}", inv2="Jūsų DI asistentas jas perskaito (prompts/50_invoices.md), tada tikrinimas su banko išrašu → lapas Invoices.",
               subj="[FLOKTRON · mail] laukia jūsų: {n}",
               item="📬 Paštas · {who}\n«{subj}» · {date}\n{why}", wait="laukia {n} d.", today="atėjo šiandien", star="pažymėjote ⭐"),
}
NEED = {  # how the stored English "Need" is shown in a notice
    "lv": {"confirm": "apstiprināt", "reply": "atbildēt", "reply?": "atbildēt?", "decide: attend?": "izlemt: piedalīties?",
           "check deadline": "pārbaudīt termiņu", "read": "izlasīt", "starred, waiting": "⭐ atlikts", "deadline": "termiņš"},
    "ru": {"confirm": "подтвердить", "reply": "ответить", "reply?": "ответить?", "decide: attend?": "решить: участвовать?",
           "check deadline": "проверить срок", "read": "прочитать", "starred, waiting": "⭐ отложено", "deadline": "срок"},
    "de": {"confirm": "bestätigen", "reply": "antworten", "reply?": "antworten?", "decide: attend?": "entscheiden: teilnehmen?",
           "check deadline": "Frist prüfen", "read": "lesen", "starred, waiting": "⭐ zurückgestellt", "deadline": "Frist"},
    "et": {"confirm": "kinnitada", "reply": "vastata", "reply?": "vastata?", "decide: attend?": "otsustada: osaleda?",
           "check deadline": "kontrollida tähtaega", "read": "lugeda", "starred, waiting": "⭐ ootel", "deadline": "tähtaeg"},
    "lt": {"confirm": "patvirtinti", "reply": "atsakyti", "reply?": "atsakyti?", "decide: attend?": "nuspręsti: dalyvauti?",
           "check deadline": "patikrinti terminą", "read": "perskaityti", "starred, waiting": "⭐ atidėta", "deadline": "terminas"},
}


def need_word(lang, need):
    t = NEED.get(lang, {})
    if need.startswith("deadline: "):
        return t.get("deadline", "deadline") + need[8:]
    return t.get(need, need)


# ---------------------------------------------------------------- helpers
def hdr(v):
    v = str(v or "")
    try:
        return str(make_header(decode_header(v))).strip()
    except Exception:  # noqa: BLE001 — a broken header is kept as it is
        return v.strip()


def plain(s):
    """Outside text for a cell: no control characters (formulas are defused by safe_xlsx on save)."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", str(s or ""))


def squash(t):
    return re.sub(r"\s+", " ", t).strip()


def nfc(s):
    return unicodedata.normalize("NFC", s)


def body_text(msg, limit=8000):
    out = []
    for part in msg.walk():
        ct = part.get_content_type()
        if part.get_filename() or ct not in ("text/plain", "text/html"):
            continue
        try:
            t = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        if ct == "text/html":
            t = re.sub(r"(?is)<(style|script).*?</\1>", " ", t)
            t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", t)
            t = re.sub(r"<[^>]+>", " ", t)
            t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        out.append(t)
        if ct == "text/plain" or sum(map(len, out)) > limit:
            break
    return "\n".join(out)[:limit]


def own_part(text):
    """The new part of a message, without the quoted old one."""
    m = QUOTE.search(text)
    return text[:m.start()] if m and m.start() > 20 else text


def is_bulk(msg, addr):
    if msg.get("List-Unsubscribe") or msg.get("List-Id"):
        return True
    if (msg.get("Precedence", "") or "").lower() in ("bulk", "list", "junk"):
        return True
    if (msg.get("Auto-Submitted", "") or "").lower().startswith("auto"):
        return True
    local = addr.split("@")[0] if addr else ""
    return bool(local and (NOREPLY.match(local + "@") or AUTO_SENDER.search(local)))


def classify(subject, own, msg, addr, pdfs, outgoing, own_addrs, system):
    if outgoing:
        return "Sent"
    if system.search(subject) or addr in own_addrs:
        return "FLOKTRON (system)"
    if CODES.search(subject):
        return "Code / login"
    if SERVICE_CONFIRM.search(subject + " " + own[:600]):
        return "Service confirmation"   # "verify your e-mail" from a service is never a task
    s = (subject + "\n" + own[:2500]).lower()
    if pdfs and (re.search(RX_INVOICE, subject.lower()) or any(re.search(RX_INVOICE, f.lower()) for f in pdfs)):
        return "Invoice"
    if AUTO_REPLY.match(subject) or msg.get("X-Autoreply") or (msg.get("Auto-Submitted", "") or "").lower() == "auto-replied":
        return "Auto-reply"
    bulk = is_bulk(msg, addr)
    if RECEIPT.search(subject):
        return "Notice"                 # "we received your submission" — nothing to answer
    for name, rx in RX:
        if re.search(rx, s):
            if bulk and name == "Confirm" and not re.search(CONFIRM_STRICT, s):
                continue  # "approved" in a notice is not a request to you
            if bulk and name in ("Reply awaited", "Deadline"):
                continue  # "please reply" in a newsletter is not personal
            return name
    if bulk and re.search(READ_IT, s):
        return "Notice (important)"
    if bulk:
        return "Notice" if NOREPLY.match(addr.split("@")[0] + "@") else "Newsletter"
    if "?" in own[:1200]:
        return "Question"
    return "Letter"


def dates_in(text, sent_day):
    found, low = set(), text.lower()
    for d, m, y in re.findall(r"\b(\d{1,2})\.(\d{1,2})\.(20\d\d)\b", text):
        found.add((int(y), int(m), int(d)))
    for y, m, d in re.findall(r"\b(20\d\d)-(\d{2})-(\d{2})\b", text):
        found.add((int(y), int(m), int(d)))
    for d, w in re.findall(r"\b(\d{1,2})\.?\s+([a-zäöüõāčēģīķļņšūžąęėįųа-я]{3,})", low):
        for k, m in MONTHS.items():
            if w.startswith(k) and (len(k) > 3 or len(w) <= 9):
                found.add((sent_day.year + (1 if m < sent_day.month - 2 else 0), m, int(d)))
                break
    out = []
    for y, m, d in sorted(found):
        try:
            x = dt.date(y, m, d)
        except ValueError:
            continue
        if sent_day <= x <= sent_day + dt.timedelta(days=400):
            out.append(x)
    return out[:5]


def signature(own):
    tail = own[-1500:]
    phones = []
    for p in PHONE.findall(tail):
        p = re.sub(r"\s+", " ", p).strip()
        if len(re.sub(r"\D", "", p)) >= 8 and p not in phones:
            phones.append(p)
    webs = [w.lower() for w in WEB.findall(tail)]
    return ", ".join(phones[:3]), (webs[0] if webs else "")


def safe_name(s, n=50):
    s = re.sub(r'[\\/:*?"<>|®™\r\n\t]+', " ", s)
    s = re.sub(r"\s+", " ", s.strip())
    return s[:n].strip(" ._") or "unnamed"


def org_of(addr, important):
    d = addr.split("@")[-1].lower().strip(">")
    for dom, org in (important or {}).items():
        dom = str(dom).lower()
        if d == dom or d.endswith("." + dom):
            return str(org)
    return ""


def analyse(raw, ctx, outgoing=None):
    msg = email.message_from_bytes(raw, policy=policy.default)
    frm = getaddresses([hdr(msg.get("From", ""))])
    to = getaddresses([hdr(x) for x in msg.get_all("To", []) + msg.get_all("Cc", [])])
    sender = (frm[0][1] if frm else "").lower()
    if outgoing is None:
        outgoing = sender in ctx["own"]
    subject = hdr(msg.get("Subject")) or "(no subject)"
    who = [(n, a.lower()) for n, a in (to if outgoing else frm) if a]
    name, addr = (who[0] if who else ("", ""))
    try:
        when = parsedate_to_datetime(msg["Date"]).astimezone(ctx["tz"])
    except Exception:  # noqa: BLE001
        when = ctx["now"]
    text = body_text(msg)
    own = own_part(text)
    pdfs = [hdr(p.get_filename()) for p in msg.walk() if p.get_filename() and hdr(p.get_filename()).lower().endswith(".pdf")]
    natt = sum(1 for p in msg.walk() if p.get_filename())
    cat = classify(subject, own, msg, addr, pdfs, outgoing, ctx["own"], ctx["system"])
    phones, web = signature(own) if not outgoing else ("", "")
    refs = set(re.findall(r"<[^>]+>", (msg.get("In-Reply-To", "") or "") + " " + (msg.get("References", "") or "")))
    return dict(msg=msg, dt=when, subject=subject, name=hdr(name), addr=addr, org=org_of(addr, ctx["important"]),
                cat=cat, dates=dates_in(subject + " " + own, when.date()), snippet=squash(own)[:160], natt=natt,
                pdfs=pdfs, outgoing=outgoing, refs=refs, mid=(msg.get("Message-ID", "") or "").strip(),
                phones=phones, web=web, bulk=is_bulk(msg, addr), all_to=[a.lower() for _, a in to if a])


def need_of(i, now):
    """(what to do, after how many hours to remind) or ("", None)."""
    c = i["cat"]
    if c == "Confirm":
        return "confirm", 0
    if c == "Reply awaited":
        return "reply", 0
    if c == "Invitation":
        future = [d for d in i["dates"] if d >= now.date()]
        if not i["bulk"] or (i["org"] and future):
            return "decide: attend?", 0
        return "", None
    if c == "Deadline" and not i["bulk"]:
        future = [d for d in i["dates"] if d >= i["dt"].date()]
        return ("deadline: " + ", ".join(d.strftime("%d.%m") for d in future[:2])) if future else "check deadline", 0
    if c == "Notice (important)":
        return ("read", 0) if i["org"] else ("", None)
    if c == "Question":
        return "reply?", 24
    if c == "Invoice":
        return "invoice → check", None
    return "", None


# ---------------------------------------------------------------- mail in
def boxes_of(mcfg, wcfg):
    inbox, sent = FOLDERS.get(mcfg.get("provider", "smtp"), FOLDERS["smtp"])
    return [(b, False) for b in (wcfg.get("inbox_folders") or inbox)] + [(b, True) for b in (wcfg.get("sent_folders") or sent)]


def from_folder(path):
    """Yield (raw, flags) from .eml files; flags from an optional flags.json in the folder."""
    fl = {}
    if os.path.exists(os.path.join(path, "flags.json")):
        with open(os.path.join(path, "flags.json"), encoding="utf-8") as f:
            fl = json.load(f)
    for name in sorted(os.listdir(path)):
        if name.lower().endswith(".eml"):
            with open(os.path.join(path, name), "rb") as f:
                yield f.read(), " ".join(fl.get(name, []))


# ---------------------------------------------------------------- invoices
def invoice_hashes(root):
    hs = set()
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith(".pdf"):
                try:
                    with open(os.path.join(d, f), "rb") as fh:
                        hs.add(hashlib.sha256(fh.read()).hexdigest())
                except OSError:
                    pass
    return hs


def save_invoice(i, inbox, known):
    """Save the invoice PDFs of a message (only the invoice-named ones if any are named so). Returns paths."""
    out = []
    names = [hdr(p.get_filename()) for p in i["msg"].walk() if p.get_filename() and hdr(p.get_filename()).lower().endswith(".pdf")]
    only = [n for n in names if re.search(RX_INVOICE, n.lower())]
    folder = os.path.join(inbox, safe_name(i["org"] or i["name"] or i["addr"].split("@")[-1], 40))
    for part in i["msg"].walk():
        fn = hdr(part.get_filename() or "")
        if not fn.lower().endswith(".pdf") or (only and fn not in only):
            continue
        try:
            data = part.get_payload(decode=True)
        except Exception:  # noqa: BLE001
            continue
        h = hashlib.sha256(data).hexdigest()
        if h in known:
            out.append("(already there)")
            continue
        os.makedirs(folder, exist_ok=True)
        p = os.path.join(folder, f'{i["dt"]:%Y-%m-%d}_{safe_name(fn, 80)}')
        if not p.lower().endswith(".pdf"):
            p += ".pdf"
        with open(p, "wb") as f:
            f.write(data)
        known.add(h)
        out.append(nfc(os.path.relpath(p, inbox)))
    return "; ".join(out)


def unread_invoices(inbox, extraction):
    known = set()
    if os.path.exists(extraction):
        with open(extraction, encoding="utf-8") as f:
            known = {nfc(r.get("file", "")) for r in (json.load(f).get("docs") or [])}
    out = []
    for d, _, fs in os.walk(inbox):
        if any(x in d for x in ("statements", "_done", "_archive")):
            continue
        for f in sorted(fs):
            if f.lower().endswith(".pdf"):
                rel = nfc(os.path.relpath(os.path.join(d, f), inbox))
                if rel not in known:
                    out.append(rel)
    return sorted(out), known


# ---------------------------------------------------------------- notices
def notify(cfg, wcfg, text, subject, outbox, log):
    """Send the notice to the manager: Telegram (bot of config telegram) or e-mail. Returns an error text or ""."""
    how = wcfg.get("notify") or ("telegram" if (cfg.get("telegram") or {}).get("enabled") else "mail")
    if how == "none":
        return ""
    if outbox:
        os.makedirs(outbox, exist_ok=True)
        n = len([x for x in os.listdir(outbox) if x.endswith(".txt")]) + 1
        with open(os.path.join(outbox, f"notice_{n:02d}_{how}.txt"), "w", encoding="utf-8") as f:
            f.write(f"{subject}\n\n{text}\n")
        return ""
    if how == "telegram":
        tg = cfg.get("telegram") or {}
        try:
            from bot.telegram_bot import token_from
            tok = token_from(tg)
        except Exception as e:  # noqa: BLE001
            return f"Telegram: {e}"[:120]
        ids = [str(x) for x in (tg.get("manager_chat_ids") or [])]
        if not ids:
            return "Telegram: telegram.manager_chat_ids is empty"
        from bot.telegram_bot import Api
        api = Api(tok, timeout=20)
        for cid in ids:
            try:
                api.call("sendMessage", chat_id=cid, text=text[:3900], disable_web_page_preview=True)
            except Exception as e:  # noqa: BLE001
                return f"Telegram: {str(e)[:80]}"
        return ""
    mcfg = cfg.get("mail") or {}
    to = wcfg.get("notify_to") or mcfg.get("manager_address")
    if not to:
        return "mail: mail.manager_address is empty"
    try:
        from mail.send import Sender
        m = EmailMessage()
        m["From"] = mcfg.get("from") or mcfg.get("user")
        m["To"] = to
        m["Subject"] = subject
        m["Date"] = formatdate(localtime=True)
        m["Message-ID"] = make_msgid(domain=(m["From"] or "floktron.local").split("@")[-1])
        m.set_content(text)
        with Sender(mcfg) as s:
            s.send(m)
    except Exception as e:  # noqa: BLE001
        return f"mail: {e}"[:120]
    return ""


# ---------------------------------------------------------------- base
def sheet(wb, name, head, widths, color):
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    if name not in wb.sheetnames:
        ws = wb.create_sheet(name)
        ws.append(head)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=color)
        for n, w in enumerate(widths):
            ws.column_dimensions[get_column_letter(n + 1)].width = w
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(head))}1"
    return wb[name]


def load_yaml(path):
    if not path or not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run(cfg, base, sources, now, state_path, outbox=None, dry=False, test=False, no_notify=False, log=print,
        replied=None, flags=None):
    """sources: list of dicts from analyse(). replied: Message-IDs your sent mail answers. flags: {mid: (star, answered)}."""
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
    wcfg = cfg.get("mail_watch") or {}
    lang = (cfg.get("company") or {}).get("language", "en")
    T = TX.get(lang, TX["en"])
    st = {}
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            st = json.load(f)
    st.setdefault("start", now.timestamp())  # mail older than 48 h from before the first run: only in the sheet
    replied, flags = set(replied or ()), dict(flags or {})
    for i in sources:
        if i["outgoing"]:
            replied |= i["refs"]
    new = sorted(sources, key=lambda i: i["dt"])
    if dry:
        for i in new:
            nd, _ = need_of(i, now)
            log(f'{i["dt"]:%d.%m %H:%M} {"→" if i["outgoing"] else "←"} {i["cat"]:18} {nd or "-":18} {(i["org"] or i["addr"])[:28]:28} {i["subject"][:60]}')
        log(f"DRY RUN — {len(new)} messages, nothing written or sent.")
        return dict(added=0, due=0, invoices=0, unread=0)
    if not os.path.exists(base):
        sys.exit(f"Base not found: {base} (run scripts/base_create.py first)")
    color = re.sub(r"[^0-9A-Fa-f]", "", str((cfg.get("colors") or {}).get("main") or "1A365D"))[:6] or "1A365D"
    wb = openpyxl.load_workbook(base)
    ws = sheet(wb, SHEET, HEAD, (16, 12, 24, 28, 16, 50, 50, 16, 20, 18, 5, 10, 18, 16, 12, 34, 30, 20), color)
    cs = sheet(wb, CSHEET, CHEAD, (30, 24, 22, 26, 22, 12, 12, 10, 10, 30), color)
    col = {h: n for n, h in enumerate(HEAD)}
    rows = {str(r[col["Message-ID"]].value): r for r in ws.iter_rows(min_row=2) if r[col["Message-ID"]].value}
    inv_cfg = cfg.get("invoices") or {}
    inv_root = os.path.join(DATA, "invoices")
    inbox = os.path.abspath(inv_cfg.get("folder") or os.path.join(inv_root, "inbox"))
    extraction = os.path.abspath(inv_cfg.get("extraction") or os.path.join(inv_root, "extraction.json"))
    hashes = invoice_hashes(inbox) if any(i["cat"] == "Invoice" for i in new) else set()
    contacts = {str(r[0].value).lower(): r for r in cs.iter_rows(min_row=2) if r[0].value}
    skip = {a.lower() for a in (wcfg.get("skip_contacts") or []) + [(cfg.get("mail") or {}).get("manager_address") or ""]} | cfg["_own"]
    added = inv = 0
    for i in new:
        if not i["mid"] or i["mid"] in rows:
            continue
        nd, _ = need_of(i, now)
        star, ans = flags.get(i["mid"], (False, False))
        invf = save_invoice(i, inbox, hashes) if i["cat"] == "Invoice" else ""
        inv += bool(invf and invf != "(already there)")
        status = "Sent" if i["outgoing"] else ("Action needed" if nd and i["cat"] != "Invoice" else ("Invoice saved" if invf else "—"))
        att = (f'{i["natt"]} · ' + "; ".join(i["pdfs"]))[:250] if i["pdfs"] else (i["natt"] or "")
        ws.append([i["dt"].strftime("%Y-%m-%d %H:%M"), "→ sent" if i["outgoing"] else "← received", plain(i["name"] or i["addr"]),
                   plain(", ".join(i["all_to"])[:120] if i["outgoing"] else i["addr"]), plain(i["org"]), plain(i["subject"]),
                   plain(i["snippet"]), i["cat"], nd, ", ".join(d.strftime("%d.%m.%Y") for d in i["dates"]),
                   "⭐" if star else "", "yes" if (ans or i["mid"] in replied) else "", status, "", plain(att), plain(invf),
                   i["mid"], "TEST" if test else ""])
        rows[i["mid"]] = ws[ws.max_row]
        added += 1
        for a in ([i["addr"]] if not i["outgoing"] else i["all_to"]):
            if not a or a in skip or (not i["outgoing"] and i["bulk"]) or NOREPLY.match(a.split("@")[0] + "@"):
                continue
            day = i["dt"].strftime("%Y-%m-%d")
            r = contacts.get(a)
            if r is None:
                cs.append([a, plain(i["name"] if not i["outgoing"] else ""), plain(i["org"] or a.split("@")[-1]), plain(i["phones"]),
                           plain(i["web"]), day, day, 0 if i["outgoing"] else 1, 1 if i["outgoing"] else 0, "TEST" if test else ""])
                contacts[a] = cs[cs.max_row]
                continue
            if not r[1].value and i["name"] and not i["outgoing"]:
                r[1].value = plain(i["name"])
            if i["phones"] and i["phones"] not in str(r[3].value or ""):
                r[3].value = plain(", ".join(x for x in [str(r[3].value or ""), i["phones"]] if x)[:120])
            if i["web"] and not r[4].value:
                r[4].value = plain(i["web"])
            r[5].value = min(str(r[5].value or day), day)
            r[6].value = max(str(r[6].value or day), day)
            k = 8 if i["outgoing"] else 7
            r[k].value = int(r[k].value or 0) + 1

    # stars, answers, reminders - over every received row
    hours = str(wcfg.get("quiet_hours") or "22-07").split("-")
    q0, q1 = int(hours[0]), int(hours[1])
    quiet = (now.hour >= q0 or now.hour < q1) if q0 > q1 else (q0 <= now.hour < q1)
    days_r = [float(x) for x in (wcfg.get("remind_days") or [3, 7, 14])]   # after the first notice: day 3, 7, 14 — then stop
    close_d = float(wcfg.get("close_after_days", 14))
    q_h, star_h = float(wcfg.get("question_hours", 24)), float(wcfg.get("star_hours", 48))
    rem = st.get("rem", {})
    due = []
    # presses ✅ / ⛔ in Telegram (data/task_actions.jsonl, written by the bot) → this sheet
    import task_notice
    acts, st["tg_offset"] = task_notice.read_actions(task_notice.actions_path(cfg), st.get("tg_offset", 0), "mail")
    by_key = {task_notice.key_of(m): r for m, r in rows.items()} if acts else {}
    for a in acts:
        r = by_key.get(str(a["key"]))
        if r is not None:
            yes = a["ans"] == "y"
            r[col["Status"]].value = "Closed · Telegram ✅" if yes else "Closed · not needed"
            if yes:
                r[col["Answered"]].value = "yes"
            old = str(r[col["Comment"]].value or "")
            r[col["Comment"]].value = (old + "; " if old else "") + task_notice.note(a)
    # the correspondence goes on: the last message you sent to each address and company domain
    sent_to = {}
    for r in rows.values():
        if str(r[col["Direction"]].value or "").startswith("→"):
            when_s = str(r[col["Date"]].value or "")[:16]
            for a in re.split(r"[,;\s]+", str(r[col["Address"]].value or "").lower()):
                if "@" in a:
                    dom = a.split("@")[-1]
                    for k in (a, None if dom in PUBLIC_MAIL else "@" + dom):
                        if k and when_s > sent_to.get(k, ""):
                            sent_to[k] = when_s
    for mid, r in rows.items():
        if str(r[col["Direction"]].value or "").startswith("→"):
            continue
        if test != (str(r[col["Comment"]].value or "").upper().startswith("TEST")):
            continue  # test rows only in --test runs, real rows never in them
        star, ans = flags.get(mid, (r[col["Star"]].value == "⭐", False))
        r[col["Star"]].value = "⭐" if star else ""
        if ans or mid in replied:
            r[col["Answered"]].value = "yes"
        status = str(r[col["Status"]].value or "")
        cat0 = str(r[col["Category"]].value or "")
        if status in ("Action needed", "Reminded", "Starred, waiting", "", "—") and cat0 in ("Confirm", "Question", "Code / login") \
                and SERVICE_CONFIRM.search(str(r[col["Subject"]].value or "") + " " + str(r[col["Summary"]].value or "")):
            r[col["Category"]].value, r[col["Need"]].value = "Service confirmation", ""   # rows from before 0.28
            r[col["Status"]].value = status = "Closed · service"
        addr0 = str(r[col["Address"]].value or "").lower()
        dom0 = addr0.split("@")[-1]
        later = max(sent_to.get(addr0, ""), "" if dom0 in PUBLIC_MAIL else sent_to.get("@" + dom0, ""))
        if later and later > str(r[col["Date"]].value or "")[:16] and status in ("Action needed", "Reminded", "Starred, waiting"):
            r[col["Answered"]].value = "yes"   # you wrote to them after this message: the correspondence goes on
        if r[col["Answered"]].value == "yes" and status in ("Action needed", "Reminded", "Starred, waiting"):
            r[col["Status"]].value = status = "Answered"
        if status.lower().startswith(CLOSED):
            rem.pop(mid, None)
            continue
        need, cat = str(r[col["Need"]].value or ""), str(r[col["Category"]].value or "")
        try:
            when = dt.datetime.strptime(str(r[col["Date"]].value), "%Y-%m-%d %H:%M").replace(tzinfo=now.tzinfo)
        except ValueError:
            continue
        age = (now - when).total_seconds() / 3600
        if r[col["Answered"]].value == "yes":
            continue
        if age > 24 * (close_d + 1) and status in ("Action needed", "Reminded", "Starred, waiting"):
            r[col["Status"]].value = f"Closed · {close_d:g} days"   # no answer for 14 days — stop, no fanaticism
            rem.pop(mid, None)
            continue
        if age > 24 * 21:
            continue  # older than 3 weeks: only in the sheet
        if star and not need:
            need, delay = "starred, waiting", star_h
            if status in ("—", "", "Invoice saved"):
                r[col["Status"]].value = "Starred, waiting"
        elif need and cat != "Invoice":
            delay = q_h if need == "reply?" else 0
        else:
            continue
        sent = rem.get(mid, [])
        if len(sent) > len(days_r) or age < (delay if not sent else days_r[len(sent) - 1] * 24) \
                or (sent and now.timestamp() - sent[-1] < 20 * 3600):
            continue
        if age > 48 and not sent and when.timestamp() < st["start"]:
            continue  # mail from before FLOKTRON watched the mailbox: only in the sheet and on the dashboard
        due.append((mid, r, need))
    how = wcfg.get("notify") or ("telegram" if (cfg.get("telegram") or {}).get("enabled") else "mail")

    # invoices from mail → invoices.py, as soon as the AI assistant has read them
    unread, known = unread_invoices(inbox, extraction) if os.path.isdir(inbox) else ([], set())
    note = ""
    jm = os.path.getmtime(extraction) if os.path.exists(extraction) else 0
    if known and jm > st.get("extraction_mtime", 0) and wcfg.get("run_invoices", True):
        wb.save(base)  # invoices.py writes the same base: save first, read again after
        import contextlib
        import io
        import invoices
        argv = ["--config", cfg["_path"], "--base", base, "--folder", inbox, "--extraction", extraction, "--apply"] \
            + (["--test", "--today", now.strftime("%Y-%m-%d")] if test else [])
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                invoices.main(argv)
        except (Exception, SystemExit) as e:  # noqa: BLE001 — a broken extraction file must not stop the mail run
            out.write(f" {e}")
        m = re.search(r"New documents: (\d+)", out.getvalue())
        note = f"invoices: new {m.group(1)}" if m else f"invoices: error {out.getvalue()[-120:]}"
        if m:
            st["extraction_mtime"] = jm
        wb = openpyxl.load_workbook(base)
        ws = wb[SHEET]
        rows = {str(x[col["Message-ID"]].value): x for x in ws.iter_rows(min_row=2) if x[col["Message-ID"]].value}
        due = [(mid, rows[mid], need) for mid, _, need in due if mid in rows]

    err = ""
    new_unread = [u for u in unread if u not in st.get("unread_told", [])]
    if new_unread and not quiet and not no_notify:
        e = notify(cfg, wcfg, T["inv"].format(n=len(unread)) + "\n" + "\n".join("• " + u for u in new_unread[:10]) + "\n" + T["inv2"],
                   T["subj"].format(n=len(unread)), outbox, log)
        if e:
            err = e
        else:
            st["unread_told"] = sorted(set(st.get("unread_told", [])) | set(new_unread))
    told = due
    if due and not quiet and not no_notify and how == "telegram":   # one letter = one message, ✅ / ⛔
        show_subj = wcfg.get("notify_subjects", True)
        told = []
        for mid, r, need in due[:5]:   # the rest — in the next run
            who = str(r[col["Organisation"]].value or "") or str(r[col["From / To"]].value or "")
            d = str(r[col["Date"]].value)
            try:
                n = (now - dt.datetime.strptime(d, "%Y-%m-%d %H:%M").replace(tzinfo=now.tzinfo)).days
            except ValueError:
                n = 0
            why = T["star"] if need == "starred, waiting" else (T["wait"].format(n=n) if n else T["today"])
            subj = str(r[col["Subject"]].value or "")[:90] if show_subj else need_word(lang, need)
            e = task_notice.send(cfg, T["item"].format(who=who[:40], subj=subj, date=f"{d[8:10]}.{d[5:7]}", why=why),
                                 "mail", task_notice.key_of(mid), lang, outbox)
            if e:
                err = e
                break
            told.append((mid, r, need))
        for mid, r, need in told:
            rem.setdefault(mid, []).append(now.timestamp())
            r[col["Reminded"]].value = now.strftime("%d.%m %H:%M") + (f" ({len(rem[mid])})" if len(rem[mid]) > 1 else "")
            if str(r[col["Status"]].value) == "Action needed":
                r[col["Status"]].value = "Reminded"
    elif due and not quiet and not no_notify:
        show_subj = wcfg.get("notify_subjects", True)
        lines = [T["head"]]
        for mid, r, need in due[:15]:
            who = str(r[col["Organisation"]].value or "") or str(r[col["From / To"]].value or "")
            subj = f' «{str(r[col["Subject"]].value or "")[:70]}»' if show_subj else ""
            lines.append(f'• {need_word(lang, need)} · {who[:40]}{subj} · {str(r[col["Date"]].value)[8:10]}.{str(r[col["Date"]].value)[5:7]}')
        lines.append(T["foot"])
        e = notify(cfg, wcfg, "\n".join(lines), T["subj"].format(n=len(due)), outbox, log)
        if e:
            err = e
        else:
            for mid, r, need in due:
                rem.setdefault(mid, []).append(now.timestamp())
                r[col["Reminded"]].value = now.strftime("%d.%m %H:%M") + (f" ({len(rem[mid])})" if len(rem[mid]) > 1 else "")
                if str(r[col["Status"]].value) == "Action needed":
                    r[col["Status"]].value = "Reminded"
    wb.save(base)
    st["rem"] = rem
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, state_path)
    log(f"mail_watch {VERSION}: new {added}, invoices saved {inv} (waiting to be read {len(unread)}), remind {len(told)}"
        + (" (quiet hours — in the morning)" if quiet and due else "") + (f"; {note}" if note else "") + (f"; ⚠ {err}" if err else ""))
    return dict(added=added, due=len(told), invoices=inv, unread=len(unread), note=note, err=err, presses=len(acts))


def context(cfg, now):
    from zoneinfo import ZoneInfo
    tz = ZoneInfo((cfg.get("company") or {}).get("timezone") or "Europe/Riga")
    mcfg, wcfg = cfg.get("mail") or {}, cfg.get("mail_watch") or {}
    own = {str(a).lower() for a in [mcfg.get("user"), mcfg.get("from"), mcfg.get("reply_to"),
                                     (cfg.get("documents") or {}).get("email")] + list(wcfg.get("own_addresses") or []) if a}
    marker = re.escape(mcfg.get("marker") or "FLOKTRON#")
    cfg["_own"] = own
    return dict(tz=tz, now=now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=tz), own=own,
                important=wcfg.get("important") or {}, system=re.compile(marker + r"|\[FLOKTRON ·|\[TEST\]"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON mail watch: every message in one sheet, reminders, contacts, invoices")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--base", default=os.path.join(DATA, "floktron_base.xlsx"))
    ap.add_argument("--state", default="")
    ap.add_argument("--mail-folder", help="read .eml files from this folder instead of the mailbox")
    ap.add_argument("--outbox", help="write the notice as .txt here instead of sending it")
    ap.add_argument("--now", help='"YYYY-MM-DD HH:MM" (tests)')
    ap.add_argument("--days", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-notify", action="store_true")
    ap.add_argument("--test", action="store_true", help="fictional data: rows marked TEST")
    a = ap.parse_args(argv)
    cfg = load_yaml(a.config)
    cfg["_path"] = a.config
    if not (cfg.get("mail_watch") or {}).get("enabled", False) and not (a.test or a.dry_run):
        print("mail_watch.enabled is false in config.yaml — nothing to do (docs/MAIL_WATCH.md).")
        return 0
    now = dt.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else dt.datetime.now().astimezone()
    ctx = context(cfg, now)
    now = ctx["now"]
    state = a.state or os.path.join(os.path.dirname(os.path.abspath(a.base)), ".mail_watch_state.json")
    first = not os.path.exists(state)
    days = a.days or int((cfg.get("mail_watch") or {}).get("first_days" if first else "days", 30 if first else 4))
    src, flags, replied = [], {}, set()
    if a.mail_folder:
        for raw, fl in from_folder(a.mail_folder):
            i = analyse(raw, ctx)
            if i["mid"] and not i["outgoing"]:
                flags[i["mid"]] = ("\\Flagged" in fl, "\\Answered" in fl)
            src.append(i)
    else:
        known = set()
        if os.path.exists(a.base):
            import openpyxl
            wb = openpyxl.load_workbook(a.base, read_only=True)
            if SHEET in wb.sheetnames:
                known = {str(r[16]) for r in wb[SHEET].iter_rows(min_row=2, values_only=True) if len(r) > 16 and r[16]}
        try:
            from mail.read import with_flags
            for m in with_flags(cfg.get("mail") or {}, boxes_of(cfg.get("mail") or {}, cfg.get("mail_watch") or {}), days, known):
                if m["outgoing"]:
                    replied |= set(re.findall(r"<[^>]+>", m["refs"]))
                else:
                    flags[m["mid"]] = ("\\Flagged" in m["flags"], "\\Answered" in m["flags"])
                if m["raw"]:
                    src.append(analyse(m["raw"], ctx, m["outgoing"]))
        except Exception as e:  # noqa: BLE001 — the mail server may be down; the next run tries again
            print(f"mail_watch: ⚠ {e}")
            return 1
    run(cfg, os.path.abspath(a.base), src, now, state, outbox=a.outbox, dry=a.dry_run, test=a.test,
        no_notify=a.no_notify, replied=replied, flags=flags)
    return 0


if __name__ == "__main__":
    sys.exit(main())
