#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gateways.py - card payments through payment gateways: find the receipt, get the business invoice, see what is missing
(docs/GATEWAYS.md, prompts/56_gateways.md)

  python3 scripts/gateways.py --config config/config.yaml [--base data/floktron_base.xlsx]
                              [--mail-folder DIR] [--statements DIR] [--outbox DIR] [--today YYYY-MM-DD]
                              [--since YYYY-MM-DD] [--days N] [--dry-run] [--no-mail] [--no-notify] [--test]

No AI. Runs with the other automatic jobs (python3 scripts/run.py gateways; after every reply collection once
gateways.enabled is true).

Why. Small online payments by card - subscriptions, AI tools, domains, apps - are sold through a payment gateway:
Stripe, Paddle, Lemon Squeezy, Apple (App Store), Google Play, PayPal, FastSpring. The document gets lost in three places:
  1) the mailbox - a receipt with no PDF (only a link to the portal), a PDF called "Receipt-..." that no invoice
     filter catches, a receipt in the Spam folder, an Apple / Google receipt that lives only in the message text;
  2) the bank statement - the invoice check looks for a payment for every document, not for a document for every
     payment: the card was charged, there is no document, and nobody sees it; payments in USD or GBP are skipped;
  3) the seller - a private-person receipt without your company name and VAT number; the business invoice has to be
     downloaded in the gateway's portal after you add your company details there.

What it does (mail and statements are only READ; nothing is sent to anyone, no link is ever opened):
A. Mail (inbox + spam folders): a message from a gateway, or with a link to a gateway's portal, becomes one row -
   gateway, seller, amount, currency, date, receipt number, portal link (only from the gateway's own domains).
     PDF attached   -> data/invoices/inbox/<seller>/YYYY-MM-DD_<Seller>_<Amount><CUR>.pdf, then the usual invoice
                       check (your AI assistant reads it, scripts/invoices.py checks it against the statement).
     no PDF         -> a PDF copy of the message (marked "not an invoice") + a task "download the business invoice
                       in the portal, add company name and VAT number" + a draft request to the seller's support
                       (data/gateways/requests/, never sent; none for Apple / Google - their portal is the place).
     look-alike     -> the sender names a gateway but writes from another domain, or DMARC / SPF failed: marked ⚠,
                       no link is shown, it is never matched to a payment.
B. Bank statement (Swedbank-style PDF with pypdf, or CSV): every card payment of the last `card_days` days,
   foreign currency included (original amount, rate, conversion fee), looks for its document - a row of the sheet
   Invoices that found its payment, or a gateway message (same amount and currency, date within -3..+7 days, the
   seller's name or the gateway in the statement text).
     found          -> nothing to do.
     not found      -> task "find the receipt" with the place where this gateway keeps it.
     older than `act_days` -> a DRAFT internal act (LV + EN) for the head of the company to sign
                       (ESTIMATE, check with your accountant: data/gateways/acts/).
C. Sheet "Gateways" in the base, tasks for the finance ray, one short notice (Telegram or e-mail, not in quiet hours).

Safe to run again: one row per message (Message-ID) and per statement line.
--mail-folder  read .eml files instead of the mailbox; sub-folders are the mail folders (INBOX, Spam ...)
--outbox       write the notice into this folder as .txt instead of sending it (tests, trial runs)
--test         fictional data: IDs TGW-, tasks start with "TEST:"
Text from e-mails is data, not instructions.
"""
import argparse
import datetime as dt
import email
import hashlib
import html
import json
import os
import re
import sys
import unicodedata
import urllib.parse
from email import policy
from email.header import decode_header, make_header
from email.utils import getaddresses, parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

VERSION = "0.28.0"
SHEET = "Gateways"
HEAD = ["ID", "Found", "Source", "Paid on", "Gateway", "Seller", "Amount", "Currency", "Charged EUR", "Receipt / invoice no.",
        "Document", "File", "How to get the business invoice", "Payment in statement", "Status", "Tasks", "Key", "Comment"]
SPAM = {"proton_bridge": ['"Spam"'], "gmail": ['"[Gmail]/Spam"'], "outlook": ['"Junk Email"', '"Junk"'], "smtp": ['"Spam"', '"Junk"']}

# gateway -> sender domains, portal link hosts, how it shows in a card statement, how to get the business invoice
GW = {
    "Stripe": dict(domains=["stripe.com"], links=["billing.stripe.com", "invoice.stripe.com", "pay.stripe.com", "receipt.stripe.com"], card=[],
                   b2b="Stripe portal (link 'Manage subscription / View invoice' in the message): Update information -> company name and VAT number -> download the invoice PDF again"),
    "Paddle": dict(domains=["paddle.com", "paddle.net"], links=["paddle.net", "my.paddle.com", "checkout.paddle.com"], card=["PADDLE.NET", "PADDLE"],
                   b2b="Paddle message -> View receipt / Manage subscription -> Add VAT / Business details -> business invoice with reverse charge"),
    "Lemon Squeezy": dict(domains=["lemonsqueezy.com", "lmsqueezy.com"], links=["app.lemonsqueezy.com", "lemonsqueezy.com"], card=["LEMSQZY", "LEMON SQUEEZY"],
                          b2b="Lemon Squeezy message -> View receipt / Manage subscription -> Add business details (VAT) -> business invoice with reverse charge"),
    "Apple": dict(domains=["apple.com", "email.apple.com", "itunes.com"], links=["reportaproblem.apple.com", "apps.apple.com"], card=["APPLE.COM/BILL", "APPLE.COM"],
                  b2b="reportaproblem.apple.com -> the purchase -> receipt PDF (Apple issues it, not the app developer)"),
    "Google Play": dict(domains=["google.com"], links=["pay.google.com", "payments.google.com", "play.google.com"], card=["GOOGLE*", "GOOGLE "],
                        b2b="pay.google.com -> Activity / Transactions -> the purchase -> invoice PDF"),
    "PayPal": dict(domains=["paypal.com"], links=["paypal.com", "www.paypal.com"], card=["PAYPAL"],
                   b2b="paypal.com -> Activity -> the payment -> Print / Download; the seller's invoice comes from the seller"),
    "FastSpring": dict(domains=["fastspring.com", "onfastspring.com"], links=["fastspring.com", "onfastspring.com"], card=["FS *", "FS*", "FASTSPRING"],
                       b2b="FastSpring message -> View invoice -> Add / change VAT ID -> invoice"),
}
PAY_RX = re.compile(r"(?i)receipt|invoice|payment\s+(confirm|received|success)|your\s+order|order\s+(confirm|receipt)|subscription\s+"
                    r"(renew|confirm|start)|you\s+paid|amount\s+paid|charged|kvīts|rēķins|maksājum|čeks|чек|квитанц|оплат|"
                    r"zahlungsbest|quittung|rechnung|kviitung|kvitas")
BRAND_RX = re.compile(r"(?i)\b(stripe|paddle|lemon\s*squeezy|apple|app\s+store|google\s+play|paypal|fastspring)\b")
AMT = re.compile(r"(?i)(US\$|€|\$|£|EUR|USD|GBP)\s?(\d{1,6}(?:[.,]\d{3})*[.,]\d{2})(?!\d)|(\d{1,6}(?:[.,]\d{3})*[.,]\d{2})\s?(€|EUR|USD|GBP|\$|£)(?![A-Za-z])")
TOTAL_RX = re.compile(r"(?i)(amount\s+(paid|charged)|total(\s+paid|\s+charged)?|grand\s+total|you\s+paid|kopā|summa|итого|к\s+оплате|gesamt|order\s+total|charged)")
NUM_RX = [re.compile(r"(?i)receipt\s*(?:number|no\.?|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{3,})"),
          re.compile(r"(?i)invoice\s*(?:number|no\.?|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{3,})"),
          re.compile(r"(?i)order\s*(?:id|number|no\.?|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9.\-]{3,})"),
          re.compile(r"#\s?([0-9]{4}-[0-9]{4}(?:-[0-9]{4})?)")]
DATE_LIKE = re.compile(r"(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}|\b20\d\d\b|\d{1,2}\.\d{1,2}\.")
STOP = {"TEST", "FICTIONAL", "LTD", "LIMITED", "SIA", "INC", "LLC", "GMBH", "PBC", "THE", "APP", "PRO", "PREMIUM", "MONTHLY"}
CARD_WORDS = re.compile(r"(?i)\b(card|karte|kartes|ctx|pirkums|kaart|kortel|karta)\b")

TX = {  # the notice, in company.language
    "en": dict(head="💳 FLOKTRON · card payments: {n} new", foot="Details: sheet Gateways; tasks for the finance ray.", subj="[FLOKTRON · gateways] {n} new"),
    "lv": dict(head="💳 FLOKTRON · maksājumi ar karti: jauni {n}", foot="Sīkāk: lapa Gateways; uzdevumi finanšu starim.", subj="[FLOKTRON · gateways] jauni {n}"),
    "ru": dict(head="💳 FLOKTRON · оплаты картой: новых {n}", foot="Подробно — лист Gateways; задачи — лучу финансов.", subj="[FLOKTRON · gateways] новых {n}"),
    "de": dict(head="💳 FLOKTRON · Kartenzahlungen: {n} neu", foot="Details: Blatt Gateways; Aufgaben für den Finanz-Strahl.", subj="[FLOKTRON · gateways] {n} neu"),
    "et": dict(head="💳 FLOKTRON · kaardimaksed: uusi {n}", foot="Täpsemalt: leht Gateways; ülesanded finantskiirele.", subj="[FLOKTRON · gateways] uusi {n}"),
    "lt": dict(head="💳 FLOKTRON · mokėjimai kortele: nauji {n}", foot="Plačiau: lapas Gateways; užduotys finansų spinduliui.", subj="[FLOKTRON · gateways] nauji {n}"),
}


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


def safe_name(s, n=50):
    s = re.sub(r'[\\/:*?"<>|®™\r\n\t]+', " ", str(s))
    s = re.sub(r"\s+", " ", s.strip())
    return s[:n].strip(" ._") or "unnamed"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def tokens(name):
    """Words of a seller's name to look for in the statement (4+ letters, without TEST / LTD / SIA ...)."""
    return [w for w in (norm(x) for x in re.split(r"[\s,.*/()\-]+", str(name))) if len(w) >= 4 and w not in STOP]


def money(s):
    s = s.replace(" ", "")
    if re.search(r",\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    return round(float(s), 2)


def workday(day, n):
    while n > 0:
        day += dt.timedelta(days=1)
        if day.weekday() < 5:
            n -= 1
    return day


def dom_match(d, doms):
    return any(d == x or d.endswith("." + x) for x in doms)


def bodies(msg):
    """(text, html) of the message without attachments."""
    txt, htm = "", ""
    for part in msg.walk():
        if part.get_filename() or part.get_content_type() not in ("text/plain", "text/html"):
            continue
        try:
            t = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        if part.get_content_type() == "text/plain" and not txt:
            txt = t
        elif part.get_content_type() == "text/html" and not htm:
            htm = t
    if not txt and htm:
        t = re.sub(r"(?is)<(style|script).*?</\1>", " ", htm)
        t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>|</li>", "\n", t)
        txt = html.unescape(re.sub(r"<[^>]+>", " ", t))
    txt = re.sub(r"[ \t\u00a0]+", " ", txt)
    return re.sub(r"\n\s*\n+", "\n", txt).strip(), htm


def links_of(text, htm):
    out = []
    for u in re.findall(r"https?://[^\s\"'<>)\]]+", (htm or "") + "\n" + text):
        u = html.unescape(u).rstrip(".,;")
        try:
            out.append(((urllib.parse.urlparse(u).hostname or "").lower(), u))
        except ValueError:
            continue
    return out


def find_amount(text):
    """(amount, currency): first a line with Total / Amount paid / Kopā, else the largest amount in the message."""
    def all_in(s):
        res = []
        for m in AMT.finditer(s):
            sym, v1, v2, sym2 = m.groups()
            cur = {"€": "EUR", "$": "USD", "US$": "USD", "£": "GBP"}.get((sym or sym2 or "").upper(), (sym or sym2 or "").upper())
            try:
                res.append((money(v1 or v2), cur))
            except ValueError:
                pass
        return res
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if TOTAL_RX.search(ln):
            got = all_in(ln) or all_in(" ".join(lines[i + 1:i + 2]))
            if got:
                return got[-1]
    got = all_in(text)
    return max(got) if got else (None, "")


def find_number(subject, text):
    for rx in NUM_RX:
        m = rx.search(subject + "\n" + text)
        if m:
            return m.group(1).strip(".-")
    return ""


def find_seller(gw, subject, name, text):
    for p in (r"(?i)receipt\s+from\s+(.+?)(?:\s+#|\s*\[|$)", r"(?i)receipt\s+for\s+(?:your\s+)?(.+?)(?:\s+#|\s+order|\s+purchase|$)",
              r"(?i)order\s+from\s+(.+?)(?:\s+#|$)", r"(?i)payment\s+to\s+(.+?)(?:\s+#|$)", r"(?i)invoice\s+from\s+(.+?)(?:\s+#|$)"):
        m = re.search(p, subject)
        if m:
            v = m.group(1).strip(" .!-")
            if v and not re.fullmatch(r"(?i)apple|google( play)?|paddle|stripe|paypal", v) and not DATE_LIKE.search(v):
                return v
    for p in (r"(?im)^\s*(?:seller|sold\s+by|merchant|vendor|developer|app|item)\s*[:\-]\s*(.+)$",
              r"(?im)^\s*(.+?)\s+(?:subscription|monthly|yearly|annual)\b"):
        m = re.search(p, text)
        if m and len(m.group(1).strip()) > 2:
            return m.group(1).strip()[:60]
    nm = re.sub(r"(?i)\s*(via|through)\s+.*$", "", name or "").strip(' "')
    if nm and not re.fullmatch(r"(?i)(apple|google( play)?|google payments|paddle(\.com)?|stripe|paypal|lemon squeezy|fastspring)(\s+(receipts?|billing|payments?))?", nm):
        return nm
    return gw


def analyse(raw, box, tz, now):
    """One message -> a gateway record, or None (not a gateway payment)."""
    msg = email.message_from_bytes(raw, policy=policy.default)
    subject = hdr(msg.get("Subject")) or ""
    frm = getaddresses([hdr(msg.get("From", ""))])
    name, addr = (frm[0] if frm else ("", ""))
    addr = addr.lower()
    d = addr.split("@")[-1].strip("> ")
    text, htm = bodies(msg)
    links = links_of(text, htm)
    gw, by = None, ""
    for g, c in GW.items():
        if dom_match(d, c["domains"]) and (g != "Google Play" or re.search(r"(?i)googleplay|payments-noreply|google\s+play|google\s+payments", addr + " " + name + " " + subject)):
            gw, by = g, "sender"
            break
    if not gw:
        for g, c in GW.items():
            if g != "PayPal" and any(dom_match(h, c["links"]) for h, _ in links):
                gw, by = g, "portal link"
                break
    pay_like = bool(PAY_RX.search(subject)) or bool(re.search(r"(?i)receipt|invoice|amount paid|kvīts|чек", text[:600]))
    amount, cur = find_amount(text)
    auth = (msg.get("Authentication-Results", "") or "").lower()
    claim = BRAND_RX.search(subject + " " + name)
    fake = ""
    if claim and not gw:
        fake = f"⚠ names '{claim.group(1)}' but the sender is {d} - not the gateway's domain; do not open the links"
    if "dmarc=fail" in auth or "spf=fail" in auth:
        fake = f"⚠ sender check failed ({'DMARC' if 'dmarc=fail' in auth else 'SPF'} fail, {d}); do not open the links"
    if not fake and not (gw and pay_like and amount):
        return None  # an ordinary supplier invoice stays with mail_watch.py and invoices.py
    pdfs = [(hdr(p.get_filename()), p) for p in msg.walk() if p.get_filename() and hdr(p.get_filename()).lower().endswith(".pdf")]
    if msg.get("List-Unsubscribe") and not pdfs and not re.search(r"(?i)receipt|kvīts|чек|invoice|amount paid", subject):
        return None  # news and marketing of the gateway
    try:
        when = parsedate_to_datetime(msg["Date"]).astimezone(tz)
    except Exception:  # noqa: BLE001
        when = now
    good = [] if fake else [u for h, u in links if gw and dom_match(h, GW[gw]["links"])]
    portal = next((u for u in good if re.search(r"(?i)invoice|receipt|billing|subscription|manage|portal|reportaproblem|transactions|pay\.google", u)), good[0] if good else "")
    seller = (hdr(name) or d) if fake else find_seller(gw, subject, hdr(name), text)
    return dict(msg=msg, raw=raw, box=box, dt=when, subject=subject, name=hdr(name), addr=addr, gw=gw or "?", by=by,
                seller=safe_name(seller, 40), amount=amount, cur=cur or "EUR", number=find_number(subject, text), pdfs=pdfs,
                portal=portal, text=text, fake=fake,
                mid=(msg.get("Message-ID", "") or "").strip() or ("sha:" + hashlib.sha256(raw).hexdigest()[:24]))


# ---------------------------------------------------------------- bank statements
def read_card_pdf(path, our_iban):
    """Card payments (CTX) of a Swedbank-style PDF statement, foreign currency included. None = no pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    text = "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
    head = text[:2000]
    if not re.search(r"(Account statement|Konta pārskats)", head):
        return []
    if our_iban and our_iban not in head.replace(" ", ""):
        return []  # another account
    blocks, cur = [], None
    for ln in text.split("\n"):
        if re.match(r"^\d\d\.\d\d\.\d{4}(\s|$)", ln) and not re.search(r"(?i)balance|atlikums", ln):
            cur = [ln]
            blocks.append(cur)
        elif cur is not None:
            cur.append(ln)
    out = []
    for b in blocks:
        c = re.search(r"(\d{16})\s+CTX PIRKUMS \S+ (\d\d\.\d\d\.\d{4}) ([\d.]+) ([A-Z]{3})(.*?)\((\d+)\)\s*(.*)", "\n".join(b), re.S)
        if not c:
            continue
        arch, buy, orig, ccy, mid, ref, rest = c.groups()
        mid1 = mid.replace("\n", " ")
        rate = re.search(r"KURSS\s*([\d.]+)", mid1)
        fee = re.search(r"MAKSA\s*([\d.]+)\s*EUR", mid1)
        lines = [x.strip() for x in rest.split("\n") if x.strip()]
        nums = [x for x in lines if re.fullmatch(r"\d+\.\d\d", x)]
        desc = " ".join(x for x in lines if not re.fullmatch(r"\d+\.\d\d", x))[:80]
        if nums:
            eur = float(nums[-1])
        elif ccy == "EUR":
            eur = float(orig)
        else:
            eur = round(float(orig) / float(rate.group(1)) + float(fee.group(1) if fee else 0), 2) if rate else None
        out.append(dict(key=f"{arch}/{ref}", date=dt.datetime.strptime(buy, "%d.%m.%Y").date(), orig=float(orig), cur=ccy,
                        rate=float(rate.group(1)) if rate else None, fee=float(fee.group(1)) if fee else 0.0, eur=eur, desc=desc,
                        file=os.path.basename(path)))
    return out


def read_card_csv(path):
    """Card payments of a CSV statement: money out with a card word in the text (card / karte / CTX / pirkums)."""
    import invoices
    out = []
    for t in invoices.read_csv(path):
        if t["amount"] is None or not CARD_WORDS.search(f'{t["cp"]} {t["details"]}'):
            continue
        a = abs(float(t["amount"]))
        out.append(dict(key=t["arch"], date=t["date"], orig=a, cur="EUR", rate=None, fee=0.0, eur=a,
                        desc=re.sub(r"\s+", " ", f'{t["cp"]} {t["details"]}').strip()[:80], file=os.path.basename(path)))
    return out


def read_cards(folder, our_iban, gaps):
    out = {}
    if not folder or not os.path.isdir(folder):
        return []
    for root, _, files in os.walk(folder):
        for fn in sorted(files):
            low = fn.lower()
            if "privat" in low:
                continue
            p = os.path.join(root, fn)
            got = read_card_csv(p) if low.endswith(".csv") else read_card_pdf(p, our_iban) if low.endswith(".pdf") else []
            if got is None:
                gaps.append(f"{fn}: PDF statements need 'pip install pypdf' — or download the statement as CSV")
                continue
            for t in got:
                out[t["key"]] = t
    return list(out.values())


def gw_of_desc(desc):
    u = desc.upper()
    for g, c in GW.items():
        if any(k in u for k in c["card"]):
            return g
    return ""


def where_hint(desc):
    g = gw_of_desc(desc)
    return GW[g]["b2b"] if g else "Search the mailbox (spam and private mailboxes too) for the name in the statement; if the seller uses Stripe, the portal link is in its message"


# ---------------------------------------------------------------- matching
def match_cards(cards, mails, invoice_rows):
    """For every card payment: a row of the sheet Invoices that found it, or a gateway message. {key: (kind, ref)}."""
    res, used = {}, set()
    for t in cards:
        hit = None
        for r in invoice_rows:
            if r["total"] is not None and abs(r["total"] - (t["eur"] if t["cur"] == "EUR" else t["orig"])) < 0.006 \
                    and t["date"].strftime("%d.%m.%Y") in r["paid"]:
                hit = ("Invoices", r["id"])
                break
        if not hit:
            best, bs = None, -1.0
            for m in mails:
                if m["mid"] in used or m["fake"] or m["amount"] is None or m["cur"] != t["cur"] or abs(m["amount"] - t["orig"]) > 0.006:
                    continue
                lag = (t["date"] - m["dt"].date()).days
                if lag < -3 or lag > 7:
                    continue
                s = 1 - abs(lag) / 10
                g = gw_of_desc(t["desc"])
                if g and g == m["gw"]:
                    s += 3
                if any(w in norm(t["desc"]) for w in tokens(m["seller"])):
                    s += 3
                if s > bs:
                    best, bs = m, s
            if best is not None and bs >= 3:  # amount and date alone are not enough
                used.add(best["mid"])
                hit = ("mail", best)
        if hit:
            res[t["key"]] = hit
    return res


def invoice_rows(wb):
    rows = []
    if "Invoices" not in wb.sheetnames:
        return rows
    ws = wb["Invoices"]
    h = [c.value for c in ws[1]]
    for r in ws.iter_rows(min_row=2, values_only=True):
        x = dict(zip(h, r))
        try:
            tot = float(x.get("Total")) if x.get("Total") is not None else None
        except (TypeError, ValueError):
            tot = None
        rows.append(dict(id=x.get("ID"), total=tot, paid=str(x.get("Payment in statement") or "")))
    return rows


# ---------------------------------------------------------------- PDF
def _fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for reg, bold in (("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
                      ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
                      ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
                      ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                      ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")):
        if os.path.exists(reg) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("GwF", reg))
            pdfmetrics.registerFont(TTFont("GwFB", bold))
            return "GwF", "GwFB"
    return "Helvetica", "Helvetica-Bold"


def pdf_text(path, title, meta, body, banner, foot, color="#1A365D"):
    """A plain A4: band in the company colour, a table of facts, the text. Returns the path, or "" without reportlab."""
    try:
        from reportlab.lib.colors import HexColor, white
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas
    except ImportError:
        return ""
    F, FB = _fonts()
    W, H = A4
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle(title)

    def wrap(s, font, size, width):
        out = []
        for para in str(s).split("\n"):
            line = ""
            for w in para.split(" "):
                t = (line + " " + w).strip()
                if stringWidth(t, font, size) <= width:
                    line = t
                    continue
                if line:
                    out.append(line)
                while stringWidth(w, font, size) > width and len(w) > 1:
                    k = len(w)
                    while k > 1 and stringWidth(w[:k], font, size) > width:
                        k -= 1
                    out.append(w[:k])
                    w = w[k:]
                line = w
            out.append(line)
        return out

    def head():
        c.setFillColor(HexColor(color))
        c.rect(0, H - 60, W, 60, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont(FB, 13)
        c.drawString(40, H - 32, title[:80])
        c.setFont(F, 8)
        c.drawRightString(W - 40, H - 50, f"FLOKTRON · gateways {VERSION}")
        y = H - 78
        if banner:
            c.setFillColor(HexColor("#c53030"))
            c.setFont(FB, 10)
            c.drawString(40, y, banner)
            y -= 16
        c.setFillColor(HexColor("#14213a"))
        return y

    y = head()
    for k, v in meta:
        c.setFont(FB, 9)
        c.drawString(40, y, k)
        c.setFont(F, 9)
        for ln in wrap(v, F, 9, W - 200) or [""]:
            c.drawString(170, y, ln)
            y -= 12
        y -= 2
    y -= 6
    c.setStrokeColor(HexColor("#717171"))
    c.line(40, y, W - 40, y)
    y -= 16
    c.setFont(F, 9)
    for ln in wrap(body, F, 9, W - 80):
        if y < 50:
            c.showPage()
            y = head()
            c.setFont(F, 9)
        c.drawString(40, y, ln)
        y -= 12
    c.setFont(F, 7)
    c.setFillColor(HexColor("#717171"))
    c.drawString(40, 28, foot)
    c.save()
    return path


def receipt_pdf(m, path, test, color):
    meta = [("Gateway", f'{m["gw"]} (found by: {m["by"]})'), ("Seller", m["seller"]),
            ("Amount", f'{m["amount"]:.2f} {m["cur"]}' if m["amount"] is not None else "—"), ("Message date", f'{m["dt"]:%d.%m.%Y %H:%M}'),
            ("Receipt / invoice no.", m["number"] or "—"), ("From", f'{m["name"]} <{m["addr"]}>'), ("Subject", m["subject"]),
            ("Portal", m["portal"] or "—"), ("Message-ID", m["mid"]), ("SHA-256 of the message", hashlib.sha256(m["raw"]).hexdigest())]
    return pdf_text(path, "Payment message — copy (not an invoice)", meta, m["text"][:6000],
                    "TEST · FICTIONAL" if test else "", "Made by FLOKTRON from the e-mail. It is not the seller's invoice.", color)


def act_pdf(t, path, co, test, color):
    fx = f' (rate {t["rate"]}, conversion fee {t["fee"]:.2f} EUR)' if t["cur"] != "EUR" else ""
    meta = [("Company / Sabiedrība", f'{co["name"]}, reg. {co["reg"] or "—"}'), ("Date / Datums", dt.date.today().strftime("%d.%m.%Y")),
            ("Payment / Maksājums", f'{t["date"]:%d.%m.%Y} · card · {t["orig"]:.2f} {t["cur"]}{fx}'),
            ("Charged / Norakstīts", f'{t["eur"]:.2f} EUR' if t["eur"] is not None else "—"),
            ("Payee in statement", t["desc"]), ("Bank operation", t["key"]), ("Statement", t["file"])]
    body = ("INTERNAL ACT / IEKŠĒJAIS AKTS — expense without the seller's document\n\n"
            f"I confirm that the payment above was made for the business of {co['name']}. / Apliecinu, ka maksājums veikts "
            "uzņēmuma saimnieciskās darbības vajadzībām.\n"
            "Service or goods / Pakalpojums vai prece: ____________________________________________\n"
            "Used for (who and why) / Lietojums: ______________________________________________\n"
            "The seller's document cannot be obtained because / Dokumentu saņemt nav iespējams, jo:  ☐ no business invoice is issued  "
            "☐ no answer  ☐ seller closed  ☐ other: __________\n"
            "Attached / Pielikumā: bank statement, payment message or screenshot.\n\n"
            "Head of the company / Valdes loceklis: ______________________ (signature)      Date: ______________\n\n"
            "Note (ESTIMATE — check with your accountant): such an act with the statement usually lets the expense count as a "
            "business expense, but input VAT cannot be deducted without a proper invoice; for a service bought from abroad "
            "the accountant decides whether reverse charge is declared.")
    return pdf_text(path, "Internal act — payment without the seller's document (DRAFT)", meta, body,
                    "TEST · FICTIONAL" if test else "DRAFT — sign only after checking", "Made by FLOKTRON. Draft — check and sign.", color)


def request_letter(m, co):
    """Draft request to the seller's support (EN). Never sent; take the support address from the seller's website."""
    return (f"Subject: VAT invoice request — {m['seller']} payment {m['dt']:%d.%m.%Y} ({m['amount']:.2f} {m['cur']})\n\n"
            f"Hello,\n\nwe paid {m['amount']:.2f} {m['cur']} on {m['dt']:%d %B %Y}" + (f" (receipt {m['number']})" if m["number"] else "")
            + ". Please send a VAT invoice issued to our company:\n\n"
            f"{co['name']}\nReg. No. {co['reg']}\nVAT No. {co['vat']}\n{co['address']}\n\n"
            "If your billing portal lets us add the company details ourselves, a link is enough.\n\n"
            f"Thank you,\n{co['name']}\n")


# ---------------------------------------------------------------- notices, base
def notify(cfg, gcfg, text, subject, outbox):
    import mail_watch
    return mail_watch.notify(cfg, gcfg, text, subject, outbox, print)


def load_yaml(path):
    if not path or not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def known_hashes(root):
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


def mail_from_folder(path, tz, now):
    out = []
    for root, _, files in os.walk(path):
        box = os.path.relpath(root, path)
        box = "INBOX" if box == "." else box
        for fn in sorted(files):
            if fn.lower().endswith(".eml"):
                with open(os.path.join(root, fn), "rb") as f:
                    i = analyse(f.read(), box, tz, now)
                if i:
                    out.append(i)
    return out


def mail_from_box(cfg, gcfg, days, skip, tz, now):
    from mail.read import with_flags
    mcfg = cfg.get("mail") or {}
    inbox = gcfg.get("folders") or (["INBOX"] + SPAM.get(mcfg.get("provider", "smtp"), SPAM["smtp"]))
    out = []
    for box in inbox:
        for m in with_flags(mcfg, [(box, False)], days, skip):
            if m["raw"]:
                i = analyse(m["raw"], box.strip('"'), tz, now)
                if i:
                    out.append(i)
    return out


def run(cfg, a):
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    from zoneinfo import ZoneInfo
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
    gcfg = cfg.get("gateways") or {}
    icfg = cfg.get("invoices") or {}
    dcfg = cfg.get("documents") or {}
    company = cfg.get("company") or {}
    lang = company.get("language", "en")
    tz = ZoneInfo(company.get("timezone") or "Europe/Riga")
    now = dt.datetime.now(tz)
    today = dt.date.fromisoformat(a.today) if a.today else now.date()
    if a.today:
        now = dt.datetime.combine(today, dt.time(12, 0), tz)
    color = "#" + (re.sub(r"[^0-9A-Fa-f]", "", str((cfg.get("colors") or {}).get("main") or "1A365D"))[:6] or "1A365D")
    co = dict(name=dcfg.get("legal_name") or company.get("name") or "your company", reg=dcfg.get("reg_no") or "",
              vat=dcfg.get("vat_no") or icfg.get("our_vat") or "", address=dcfg.get("address") or "")
    ray = icfg.get("ray") or "L7"
    inbox = os.path.abspath(icfg.get("folder") or os.path.join(DATA, "invoices", "inbox"))
    statements = a.statements or icfg.get("statements") or os.path.join(DATA, "invoices", "statements")
    our_iban = (icfg.get("our_iban") or "").replace(" ", "")
    out_dir = os.path.abspath(gcfg.get("out") or os.path.join(DATA, "gateways"))
    base = os.path.abspath(a.base)
    state_path = a.state or os.path.join(os.path.dirname(base), ".gateways_state.json")
    st = {}
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            st = json.load(f)
    seen = set(st.get("seen", []))
    if not os.path.exists(base):
        sys.exit(f"Base not found: {base} (run scripts/base_create.py first)")

    # A. mail
    mails, errs = [], []
    if a.mail_folder:
        mails = mail_from_folder(a.mail_folder, tz, now)
    elif not a.no_mail:
        days = a.days or int(gcfg.get("first_days" if not st else "days", 30 if not st else 4))
        try:
            mails = mail_from_box(cfg, gcfg, days, seen, tz, now)
        except Exception as e:  # noqa: BLE001 — the mail server may be down; the statement part still runs
            errs.append(f"mail: {e}"[:120])
    mails = [m for m in mails if m["mid"] not in seen]
    uniq, dupes = {}, 0
    for m in sorted(mails, key=lambda x: (x["box"] != "INBOX", x["dt"])):
        k = (m["gw"], m["number"] or m["mid"], m["amount"], m["cur"])
        if k in uniq:
            dupes += 1
            seen.add(m["mid"])
            continue
        uniq[k] = m
    mails = list(uniq.values())

    # B. statements
    gaps = []
    cards = read_cards(statements, our_iban, gaps)
    since = dt.date.fromisoformat(a.since) if a.since else today - dt.timedelta(days=int(gcfg.get("card_days", 120)))
    cards = [t for t in cards if t["date"] >= since]

    wb = openpyxl.load_workbook(base)
    if SHEET not in wb.sheetnames:
        ws = wb.create_sheet(SHEET)
        ws.append(HEAD)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=color[1:])
        for n, w in enumerate((10, 11, 12, 11, 13, 24, 9, 7, 10, 18, 18, 40, 48, 30, 30, 14, 26, 40)):
            ws.column_dimensions[get_column_letter(n + 1)].width = w
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(HEAD))}1"
    ws = wb[SHEET]
    col = {h: n for n, h in enumerate(HEAD)}
    # presses in Telegram (✅ Found / ⛔ Not needed, data/task_actions.jsonl) → column "Status"
    import task_notice
    acts, st["tg_offset"] = task_notice.read_actions(task_notice.actions_path(cfg), st.get("tg_offset", 0), "gw")
    by_id = {str(r[col["ID"]].value): r for r in ws.iter_rows(min_row=2) if r[col["ID"]].value} if acts else {}
    for x in acts:
        r = by_id.get(str(x["key"]))
        if r is not None:
            r[col["Status"]].value = "PDF found (Telegram ✅)" if x["ans"] == "y" else "Not needed (Telegram ⛔)"
            old_c = str(r[col["Comment"]].value or "")
            r[col["Comment"]].value = (old_c + "; " if old_c else "") + task_notice.note(x)
    have = {str(r[col["Key"]].value) for r in ws.iter_rows(min_row=2) if r[col["Key"]].value}
    old = []  # gateway messages of earlier runs, for matching with a later statement
    for r in ws.iter_rows(min_row=2, values_only=True):
        if str(r[2] or "").startswith("mail") and r[6] is not None:
            try:
                old.append(dict(mid=r[16], gw=r[4], seller=r[5], amount=float(r[6]), cur=r[7], fake="⚠" in str(r[14] or ""),
                                dt=dt.datetime.strptime(str(r[3]), "%Y-%m-%d").replace(tzinfo=tz)))
            except (TypeError, ValueError):
                pass
    links = match_cards(cards, mails + old, invoice_rows(wb))
    by_mail = {ref["mid"]: next(t for t in cards if t["key"] == k) for k, (kind, ref) in links.items() if kind == "mail"}
    pre = "TGW" if a.test else "GW"
    seq = ws.max_row
    hashes = known_hashes(inbox)
    rows, tasks, files, by_gw = [], [], [], {}
    tag = "TEST · FICTIONAL; " if a.test else ""

    for m in sorted(mails, key=lambda x: x["dt"]):
        if m["mid"] in have:
            continue
        t = by_mail.get(m["mid"])
        paid = (f'{t["date"]:%d.%m.%Y} · {(t["eur"] or 0):.2f} EUR · {t["desc"][:28]}'
                + (f' ({t["orig"]:.2f} {t["cur"]}, fee {t["fee"]:.2f})' if t["cur"] != "EUR" else "")) if t else ""
        rid = f"{pre}-{seq:04d}"
        seq += 1
        folder = os.path.join(inbox, safe_name(m["seller"], 40))
        amt = f'{m["amount"]:.2f}{m["cur"]}' if m["amount"] is not None else ""
        stem = f'{m["dt"]:%Y-%m-%d}_{safe_name(m["seller"], 30).replace(" ", "_")}_{amt}'
        doc, fpath = "—", ""
        if m["fake"]:
            status = m["fake"]
            tasks.append(dict(text=f"Check the suspicious message '{m['subject'][:60]}' from {m['addr']}: do not open its links; delete it if in doubt",
                              due=workday(today, 1), rid=rid))
        elif m["pdfs"]:
            saved = []
            for fn, part in m["pdfs"]:
                data = part.get_payload(decode=True) or b""
                h = hashlib.sha256(data).hexdigest()
                if h in hashes:
                    saved.append("(already there)")
                    continue
                p = os.path.join(folder, stem + ("" if len(m["pdfs"]) == 1 else "_" + safe_name(fn, 20)) + ".pdf")
                if not a.dry_run:
                    os.makedirs(folder, exist_ok=True)
                    with open(p, "wb") as f:
                        f.write(data)
                hashes.add(h)
                saved.append(os.path.relpath(p, inbox))
                files.append(p)
            doc, fpath, status = "PDF from the message", "; ".join(saved), "PDF → invoice check (your AI assistant reads it)"
        else:
            p = os.path.join(folder, stem + "_message_copy.pdf")
            made = ""
            if not a.dry_run:
                os.makedirs(folder, exist_ok=True)
                made = receipt_pdf(m, p, a.test, color)
                if not made:  # no reportlab: keep the message itself
                    p = p[:-4] + ".eml"
                    with open(p, "wb") as f:
                        f.write(m["raw"])
                    made = p
                files.append(made)
            doc, fpath, status = "copy of the message (not an invoice)", os.path.relpath(made or p, inbox), "Business invoice needed from the portal"
            by_gw.setdefault(m["gw"], []).append((rid, m))
            if not a.dry_run and m["gw"] not in ("Apple", "Google Play"):  # Apple / Google: the document is in their portal
                lp = os.path.join(out_dir, "requests", f'{m["dt"]:%Y-%m-%d}_{safe_name(m["seller"], 30)}_request_EN.txt')
                os.makedirs(os.path.dirname(lp), exist_ok=True)
                with open(lp, "w", encoding="utf-8") as f:
                    f.write(("TEST · FICTIONAL\n\n" if a.test else "") + "DRAFT — not sent. Take the support address from the seller's website.\n\n"
                            + request_letter(m, co))
                files.append(lp)
        if t and not m["fake"]:
            status += " · payment found"
        rows.append([rid, today.isoformat(), f'mail · {m["box"]}', f'{m["dt"]:%Y-%m-%d}', m["gw"], plain(m["seller"]), m["amount"], m["cur"],
                     t["eur"] if t else None, plain(m["number"]), doc, plain(fpath),
                     plain("" if m["fake"] or m["gw"] not in GW else GW[m["gw"]]["b2b"] + (" · " + m["portal"] if m["portal"] else "")),
                     plain(paid), status, "", m["mid"], plain(tag + f'subject: {m["subject"][:80]}' + (f'; found in {m["box"]}' if m["box"] != "INBOX" else ""))])
        seen.add(m["mid"])
    for g, items in by_gw.items():
        lst = "; ".join(f'{m["seller"]} {m["amount"]:.2f} {m["cur"]} ({m["dt"]:%d.%m})' for _, m in items)
        tasks.append(dict(text=f"Download the business invoices from {g} ({len(items)}): {lst}. How: {GW[g]['b2b']}. Company: {co['name']}"
                               + (f", VAT {co['vat']}" if co["vat"] else "") + ". Put the PDF into data/invoices/inbox/<seller>/ — the invoice check takes it from there",
                          due=workday(today, 3), rid=",".join(r for r, _ in items)))

    orphans, acts = [], []
    for t in sorted(cards, key=lambda x: x["date"]):
        if t["key"] in links or t["key"] in have:
            continue
        age = (today - t["date"]).days
        rid = f"{pre}-{seq:04d}"
        seq += 1
        fx = f' ({t["orig"]:.2f} {t["cur"]}, rate {t["rate"]}, fee {t["fee"]:.2f} EUR)' if t["cur"] != "EUR" else ""
        doc, fpath = "—", ""
        if age >= int(gcfg.get("act_days", 30)):
            ap = os.path.join(out_dir, "acts", f'{t["date"]:%Y-%m-%d}_{safe_name(t["desc"], 30)}_internal_act.pdf')
            if not a.dry_run:
                os.makedirs(os.path.dirname(ap), exist_ok=True)
                made = act_pdf(t, ap, co, a.test, color)
                if made:
                    files.append(made)
                    doc, fpath = "draft internal act", os.path.relpath(made, os.path.dirname(out_dir))
            status = f"No document for {age} days → draft internal act"
            acts.append((rid, t))
        else:
            status = "Payment without a document — find the receipt"
            orphans.append((rid, t))
        rows.append([rid, today.isoformat(), "statement · card", t["date"].isoformat(), gw_of_desc(t["desc"]) or "—", plain(t["desc"][:40]),
                     t["orig"], t["cur"], t["eur"], "", doc, plain(fpath), plain(where_hint(t["desc"])),
                     plain(f'{t["date"]:%d.%m.%Y} · {(t["eur"] or 0):.2f} EUR{fx}'), status, "", t["key"], plain(tag + f'statement: {t["file"]}')])
    if orphans:
        tasks.append(dict(text="Find the documents for these card payments: " + "; ".join(f'{t["date"]:%d.%m} {t["desc"][:24]} {t["orig"]:.2f} {t["cur"]}' for _, t in orphans)
                               + ". Where to look: sheet Gateways, column 'How to get the business invoice'", due=workday(today, 5), rid=",".join(r for r, _ in orphans)))
    if acts:
        tasks.append(dict(text=f"{len(acts)} card payments older than {gcfg.get('act_days', 30)} days have no document ("
                               + "; ".join(f'{t["date"]:%d.%m} {t["desc"][:20]} {(t["eur"] or 0):.2f} EUR' for _, t in acts)
                               + "). Draft internal acts in data/gateways/acts/: check, write the purpose, sign, give to the accountant (ESTIMATE: no input VAT)",
                          due=workday(today, 5), rid=",".join(r for r, _ in acts)))
    stamp = today.strftime("%Y%m%d")
    for n, t in enumerate(tasks, 1):
        t["id"] = f"{'TG' if a.test else 'G'}{stamp}-{n:02d}"
        for r in rows:
            if r[0] in t["rid"].split(","):
                r[15] = (str(r[15]) + ", " if r[15] else "") + t["id"]

    print(f"Statements: card payments {len(cards)} since {since:%d.%m.%Y}" + (f" · ⚠ {'; '.join(gaps)}" if gaps else ""))
    print(f"Gateway messages: {len(mails)} new, duplicates {dupes} · rows for '{SHEET}': {len(rows)} · tasks for {ray}: {len(tasks)}")
    for r in rows:
        print(f"  {r[0]} {r[3]} {str(r[4])[:13]:13} {str(r[5])[:26]:26} {r[6] if r[6] is not None else '':>8} {r[7]:3}  {r[14]}")
    for t in tasks:
        print(f"  {t['id']} due {t['due']:%d.%m}: {t['text'][:150]}")
    if a.dry_run:
        print("DRY RUN — nothing written or sent.")
        return dict(rows=len(rows), tasks=len(tasks), files=0)
    for r in rows:
        ws.append(r)
    if "Tasks" in wb.sheetnames:
        for t in tasks:
            wb["Tasks"].append([t["id"], today.isoformat(), ray, ("TEST: " if a.test else "") + t["text"], "gateways → documents",
                                t["due"].isoformat(), "New", None, None, "Ray", None, None])
    wb.save(base)
    hours = str(gcfg.get("quiet_hours") or "22-07").split("-")
    q0, q1 = int(hours[0]), int(hours[1])
    hr = dt.datetime.now(tz).hour if not a.today else 12
    quiet = (hr >= q0 or hr < q1) if q0 > q1 else (q0 <= hr < q1)
    err = ""
    need = [r for r in rows if not str(r[14]).startswith("PDF")]
    if need and not quiet and not a.no_notify and task_notice.via_telegram(cfg, gcfg):
        # one payment without a document = one message with ✅ Found / ⛔ Not needed; at most 5 per run
        for r in need[:5]:
            d = str(r[3] or "")[:10]
            d = f"{d[8:10]}.{d[5:7]}" if len(d) == 10 else d
            amount = f" · {r[6]} {r[7]}" if r[6] is not None else ""
            text = ("[TEST] " if a.test else "") + f"🧾 {str(r[5])[:40]}{amount} · {d}\n{r[14]}" + (f"\n→ {r[12]}" if r[12] else "")
            err = task_notice.send(cfg, text, "gw", r[0], lang, a.outbox) or err
        if len(need) > 5:
            err = task_notice.info(cfg, f"🧾 +{len(need) - 5} · FLOKTRON gateways — more payments without a document, see the dashboard.", a.outbox) or err
    elif need and not quiet and not a.no_notify:
        T = TX.get(lang, TX["en"])
        text = "\n".join([T["head"].format(n=len(rows))] + [f"• {r[5]} {r[6]} {r[7]} — {r[14]}" for r in need[:10]] + [T["foot"]])
        err = notify(cfg, gcfg, text, T["subj"].format(n=len(rows)), a.outbox)
    st["seen"] = sorted(seen)[-20000:]
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, state_path)
    print(f"gateways {VERSION}: rows {len(rows)}, tasks {len(tasks)}, files {len(files)}" + (f"; ⚠ {err}" if err else "")
          + (f"; ⚠ {'; '.join(errs)}" if errs else ""))
    return dict(rows=len(rows), tasks=len(tasks), files=len(files), err=err)


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON gateways: card payments through Stripe, Paddle, Apple, Google … — receipts, business invoices, what is missing")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--base", default=os.path.join(DATA, "floktron_base.xlsx"))
    ap.add_argument("--state", default="")
    ap.add_argument("--mail-folder", help="read .eml files from this folder (sub-folders = mail folders) instead of the mailbox")
    ap.add_argument("--statements", help="bank statements folder (default: invoices.statements)")
    ap.add_argument("--outbox", help="write the notice as .txt here instead of sending it")
    ap.add_argument("--today", help="YYYY-MM-DD (tests)")
    ap.add_argument("--since", help="card payments from this day (default: card_days back)")
    ap.add_argument("--days", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-mail", action="store_true")
    ap.add_argument("--no-notify", action="store_true")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_yaml(a.config)
    cfg["_path"] = a.config
    if not (cfg.get("gateways") or {}).get("enabled", False) and not (a.test or a.dry_run):
        print("gateways.enabled is false in config.yaml — nothing to do (docs/GATEWAYS.md).")
        return 0
    run(cfg, a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
