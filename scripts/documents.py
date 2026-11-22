#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
documents.py - branded outgoing documents (docs/DOCUMENTS.md, prompts/52_documents.md)

Types:  invoice  - invoice (LV: Rēķins)
        advance  - advance invoice (Avansa rēķins)
        act      - delivery and acceptance act (Pieņemšanas-nodošanas akts)
        offer    - commercial offer (Komercpiedāvājums)
Languages: lv | en | lv+en

  python3 scripts/documents.py --doc data/documents/in/X.json [--config config.yaml | --seller seller.json]
                               [--out data/documents/out] [--base data/floktron_base.xlsx] [--apply]

No AI, no network. Default is a DRY RUN for the register: the PDF is written, the base is NOT touched.
--apply writes one row to the sheet "Issued" of the base given in --base (explicit path only); the row keeps the
language and the buyer e-mail, so scripts/followups.py can remind about an offer (0.21.0).
Number: "number" in the document file, else the next free <prefix>-<R|AR|A|P>-<year>-NNN from the sheet "Issued".
Colours: the "colors" section of config.yaml (same as the messages); logo and bank details: section "documents".
Needs: reportlab (pip install reportlab) and a TTF font with Latvian letters (Liberation Sans, Arial or DejaVu Sans).
"""
import argparse, datetime as dt, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

VERSION = "0.21.0"

# ---------------------------------------------------------------- brand
C = {                              # defaults = FLOKTRON message colours; config.yaml "colors" overrides
    "blue": HexColor("#1A365D"),   # colors.main
    "green": HexColor("#4A9928"),  # colors.ok
    "grey": HexColor("#717171"),   # colors.neutral
    "light": HexColor("#F3F3F3"),  # colors.background
    "line": HexColor("#D9DEE5"),
    "text": HexColor("#1F2933"),
}

FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def register_fonts():
    for reg, bold in FONT_CANDIDATES:
        if os.path.exists(reg) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("Doc", reg))
            pdfmetrics.registerFont(TTFont("Doc-Bold", bold))
            return
    sys.exit("No TTF font with Latvian letters found (Liberation/Arial/DejaVu).")


# ---------------------------------------------------------------- texts
T = {
    "lv": {
        "invoice": "RĒĶINS", "advance": "AVANSA RĒĶINS",
        "act": "PIEŅEMŠANAS-NODOŠANAS AKTS", "offer": "KOMERCPIEDĀVĀJUMS",
        "nr": "Nr.", "date": "Datums", "due": "Apmaksas termiņš",
        "supply": "Piegādes datums", "valid": "Derīgs līdz", "basis": "Pamatojums",
        "place": "Vieta", "seller": "PIEGĀDĀTĀJS", "buyer": "PIRCĒJS",
        "reg": "Reģ. Nr.", "vat": "PVN Nr.", "addr": "Adrese", "bank": "Banka",
        "col_nr": "Nr.", "col_desc": "Nosaukums", "col_qty": "Daudz.",
        "col_unit": "Mērv.", "col_price": "Cena, EUR", "col_sum": "Summa, EUR",
        "net": "Summa bez PVN", "vatl": "PVN {r} %", "total": "Kopā apmaksai",
        "total_act": "Kopā", "total_offer": "Kopā ar PVN",
        "words": "Summa vārdiem",
        "pay": "Lūdzam apmaksāt līdz {d}. Maksājuma mērķī norādiet dokumenta numuru.",
        "pay_adv": "Avanss apmaksājams līdz {d}. Pēc preču piegādes tiks izrakstīts gala rēķins, ieskaitot avansu.",
        "einv": "Dokuments sagatavots elektroniski un ir derīgs bez paraksta.",
        "act_text": "Piegādātājs nodod un Pircējs pieņem zemāk norādītās preces / pakalpojumus. "
                     "Pircējam nav pretenziju par daudzumu, kvalitāti un komplektāciju.",
        "offer_text": "Piedāvājums sagatavots pēc Jūsu pieprasījuma. Cenas norādītas EUR bez PVN, ja nav norādīts citādi.",
        "handed": "Nodeva (Piegādātājs)", "received": "Pieņēma (Pircējs)",
        "sign": "paraksts, vārds, uzvārds", "notes": "Piezīmes",
        "page": "lpp.",
    },
    "en": {
        "invoice": "INVOICE", "advance": "ADVANCE INVOICE",
        "act": "DELIVERY AND ACCEPTANCE ACT", "offer": "COMMERCIAL OFFER",
        "nr": "No.", "date": "Date", "due": "Due date",
        "supply": "Delivery date", "valid": "Valid until", "basis": "Reference",
        "place": "Place", "seller": "SUPPLIER", "buyer": "BUYER",
        "reg": "Reg. No.", "vat": "VAT No.", "addr": "Address", "bank": "Bank",
        "col_nr": "No.", "col_desc": "Description", "col_qty": "Qty",
        "col_unit": "Unit", "col_price": "Price, EUR", "col_sum": "Amount, EUR",
        "net": "Total excl. VAT", "vatl": "VAT {r} %", "total": "Total due",
        "total_act": "Total", "total_offer": "Total incl. VAT",
        "words": "Amount in words",
        "pay": "Please pay by {d}. Quote the document number in the payment reference.",
        "pay_adv": "Advance payable by {d}. A final invoice, net of this advance, follows delivery.",
        "einv": "This document was prepared electronically and is valid without a signature.",
        "act_text": "The Supplier hands over and the Buyer accepts the goods / services listed below. "
                     "The Buyer has no claims regarding quantity, quality or completeness.",
        "offer_text": "Offer prepared at your request. Prices in EUR excluding VAT unless stated otherwise.",
        "handed": "Handed over (Supplier)", "received": "Accepted (Buyer)",
        "sign": "signature, name", "notes": "Notes",
        "page": "page",
    },
}

PREFIX = {"invoice": "R", "advance": "AR", "act": "A", "offer": "P"}


def tr(lang, key, **kw):
    """lv+en -> 'LV / EN' for short labels."""
    if lang == "lv+en":
        a, b = T["lv"][key], T["en"][key]
        s = a if a == b else f"{a} / {b}"
    else:
        s = T[lang][key]
    return s.format(**kw) if kw else s


# ---------------------------------------------------------------- numbers
def D(x):
    return Decimal(str(x))


def r2(x):
    return D(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money(x):
    s = f"{r2(x):,.2f}"
    return s.replace(",", " ").replace(".", ",")


def qty_fmt(x):
    x = D(x)
    s = f"{x.normalize():f}" if x != x.to_integral() else str(int(x))
    return s.replace(".", ",")


LV_1 = ["nulle", "viens", "divi", "trīs", "četri", "pieci", "seši", "septiņi", "astoņi", "deviņi",
        "desmit", "vienpadsmit", "divpadsmit", "trīspadsmit", "četrpadsmit", "piecpadsmit",
        "sešpadsmit", "septiņpadsmit", "astoņpadsmit", "deviņpadsmit"]
LV_10 = ["", "", "divdesmit", "trīsdesmit", "četrdesmit", "piecdesmit", "sešdesmit",
         "septiņdesmit", "astoņdesmit", "deviņdesmit"]


def _lv_999(n):
    out = []
    h, rest = divmod(n, 100)
    if h == 1:
        out.append("simts")
    elif h > 1:
        out.append(LV_1[h] + " simti")
    if rest:
        if rest < 20:
            out.append(LV_1[rest])
        else:
            t, u = divmod(rest, 10)
            out.append(LV_10[t] + ((" " + LV_1[u]) if u else ""))
    return " ".join(out)


def _lv_scale(n, one, many):
    # singular when ends in 1 but not 11
    return one if (n % 10 == 1 and n % 100 != 11) else many


def lv_words(n):
    if n == 0:
        return "nulle"
    parts = []
    mil, rest = divmod(n, 1_000_000)
    th, u = divmod(rest, 1000)
    if mil:
        parts.append(_lv_999(mil) + " " + _lv_scale(mil, "miljons", "miljoni"))
    if th:
        parts.append(("" if th == 1 else _lv_999(th) + " ") + _lv_scale(th, "tūkstotis", "tūkstoši"))
    if u:
        parts.append(_lv_999(u))
    return " ".join(parts)


EN_1 = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
        "nineteen"]
EN_10 = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _en_999(n):
    out = []
    h, rest = divmod(n, 100)
    if h:
        out.append(EN_1[h] + " hundred")
    if rest:
        if rest < 20:
            out.append(EN_1[rest])
        else:
            t, u = divmod(rest, 10)
            out.append(EN_10[t] + (("-" + EN_1[u]) if u else ""))
    return " ".join(out)


def en_words(n):
    if n == 0:
        return "zero"
    parts = []
    mil, rest = divmod(n, 1_000_000)
    th, u = divmod(rest, 1000)
    if mil:
        parts.append(_en_999(mil) + " million")
    if th:
        parts.append(_en_999(th) + " thousand")
    if u:
        parts.append(_en_999(u))
    return " ".join(parts)


def amount_words(total, lang):
    total = r2(total)
    eur = int(total)
    ct = int((total - eur) * 100)
    lv = f"{lv_words(eur)} eiro un {ct:02d} {_lv_scale(ct, 'cents', 'centi')}"
    en = f"{en_words(eur)} euro and {ct:02d} cent{'s' if ct != 1 else ''}"
    lv, en = lv[0].upper() + lv[1:], en[0].upper() + en[1:]
    return {"lv": lv, "en": en, "lv+en": f"{lv} / {en}"}[lang]


def calc(doc):
    rate = D(doc.get("vat_rate", 21))
    lines = []
    net = Decimal("0")
    for ln in doc["lines"]:
        s = r2(D(ln["qty"]) * D(ln["price"]))
        if ln.get("discount_pct"):
            s = r2(s * (1 - D(ln["discount_pct"]) / 100))
        lines.append({**ln, "sum": s})
        net += s
    vat = r2(net * rate / 100)
    return lines, r2(net), vat, r2(net + vat), rate


# ---------------------------------------------------------------- register
SHEET = "Issued"
HEAD = ["Number", "Type", "Date", "Due", "Buyer", "Buyer reg. no.", "Net", "VAT", "Total", "Currency",
        "Status", "Reference", "File", "Created", "TEST", "Language", "E-mail"]


def next_number(doc, base, prefix="DOC"):
    year = doc["date"][:4]
    pre = f"{prefix}-{PREFIX[doc['type']]}-{year}-"
    n = 0
    if base and os.path.exists(base):
        from openpyxl import load_workbook
        wb = load_workbook(base, read_only=True)
        if SHEET in wb.sheetnames:
            for row in wb[SHEET].iter_rows(min_row=2, values_only=True):
                v = str(row[0] or "")
                if v.startswith(pre):
                    m = re.search(r"(\d+)$", v)
                    if m:
                        n = max(n, int(m.group(1)))
    return f"{pre}{n + 1:03d}"


def register(base, doc, number, net, vat, total, pdf_path):
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill
    wb = load_workbook(base)
    if SHEET not in wb.sheetnames:
        ws = wb.create_sheet(SHEET)
        ws.append(HEAD)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1A365D")
    ws = wb[SHEET]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] == number:
            sys.exit(f"Number {number} already in register - refusing to duplicate.")
    status = {"invoice": "Issued", "advance": "Issued", "act": "To be signed",
              "offer": "To be sent"}[doc["type"]]
    ws.append([number, doc["type"], doc["date"], doc.get("due", "") or doc.get("valid_until", ""), doc["buyer"]["name"],
               doc["buyer"].get("reg_no", ""), float(net), float(vat), float(total), "EUR", status,
               doc.get("basis", ""), os.path.basename(pdf_path),
               dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "TEST" if doc.get("test") else "",
               doc.get("lang", "lv"), doc["buyer"].get("email", "")])
    wb.save(base)


# ---------------------------------------------------------------- drawing
W, H = A4
ML, MR = 18 * mm, 18 * mm
CW = W - ML - MR


def wrap(text, font, size, width):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


class Doc:
    def __init__(self, path, seller, doc, number):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.s, self.d, self.no = seller, doc, number
        self.lang = doc.get("lang", "lv")
        self.page = 1
        title = f"{tr(self.lang, doc['type'])} {number}"
        self.c.setTitle(title)
        self.c.setAuthor(seller["name"])
        self.c.setSubject(title)
        self.c.setCreator(f"FLOKTRON documents {VERSION}")

    # -- page furniture
    def header(self):
        c, s = self.c, self.s
        c.setFillColor(C["blue"])
        c.rect(0, H - 4 * mm, W, 4 * mm, stroke=0, fill=1)
        c.setFillColor(C["green"])
        c.rect(0, H - 5.2 * mm, W, 1.2 * mm, stroke=0, fill=1)
        logo = s.get("logo")
        if logo and os.path.exists(logo):
            img = ImageReader(logo)
            iw, ih = img.getSize()
            h = 17 * mm
            c.drawImage(img, ML, H - 12 * mm - h, width=min(h * iw / ih, 75 * mm), height=h,
                        mask="auto", preserveAspectRatio=True, anchor="sw")
        else:
            c.setFont("Doc-Bold", 15)
            c.setFillColor(C["blue"])
            c.drawString(ML, H - 22 * mm, s["name"])
        y = H - 13 * mm
        c.setFont("Doc-Bold", 8.5)
        c.setFillColor(C["blue"])
        c.drawRightString(W - MR, y, s["name"])
        c.setFont("Doc", 7.5)
        c.setFillColor(C["grey"])
        for t in [f"{tr(self.lang, 'reg')} {s['reg_no']} · {tr(self.lang, 'vat')} {s['vat_no']}",
                  s["address"],
                  f"{s['email']} · {s['phone']} · {s['web']}"]:
            y -= 3.6 * mm
            c.drawRightString(W - MR, y, t)

    def footer(self):
        c, s = self.c, self.s
        c.setStrokeColor(C["line"])
        c.setLineWidth(0.5)
        c.line(ML, 14 * mm, W - MR, 14 * mm)
        c.setFont("Doc", 7)
        c.setFillColor(C["grey"])
        c.drawString(ML, 10 * mm, f"{s['name']} · {s['web']} · {s['email']}")
        c.drawRightString(W - MR, 10 * mm, f"{self.no} · {tr(self.lang, 'page')} {self.page}")
        if self.d.get("test"):
            c.saveState()
            c.setFillColor(HexColor("#C0392B"))
            c.setFont("Doc-Bold", 8)
            c.drawCentredString(W / 2, 5.5 * mm, "TEST · FICTIONAL — not a real document")
            c.translate(W / 2, H / 2)
            c.rotate(35)
            c.setFillColor(HexColor("#C0392B"), alpha=0.07)
            c.setFont("Doc-Bold", 70)
            c.drawCentredString(0, 0, "TEST · FICTIONAL")
            c.restoreState()

    def new_page(self):
        self.footer()
        self.c.showPage()
        self.page += 1
        self.header()
        return H - 40 * mm

    # -- blocks
    def title(self, y):
        c, d, L = self.c, self.d, self.lang
        c.setFillColor(C["blue"])
        c.setFont("Doc-Bold", 17)
        c.drawString(ML, y, tr(L, d["type"]))
        c.setFont("Doc-Bold", 12)
        c.setFillColor(C["green"])
        c.drawString(ML, y - 6.5 * mm, f"{tr(L, 'nr')} {self.no}")
        # meta on the right
        meta = [(tr(L, "date"), fmt_date(d["date"]))]
        if d["type"] in ("invoice", "advance") and d.get("due"):
            meta.append((tr(L, "due"), fmt_date(d["due"])))
        if d["type"] == "offer" and d.get("valid_until"):
            meta.append((tr(L, "valid"), fmt_date(d["valid_until"])))
        if d.get("supply_date") and d["type"] in ("invoice", "act"):
            meta.append((tr(L, "supply"), fmt_date(d["supply_date"])))
        if d.get("place"):
            meta.append((tr(L, "place"), d["place"]))
        yy = y + 1 * mm
        for k, v in meta:
            c.setFont("Doc", 8)
            c.setFillColor(C["grey"])
            c.drawRightString(W - MR - 32 * mm, yy, k)
            c.setFont("Doc-Bold", 9)
            c.setFillColor(C["text"])
            c.drawRightString(W - MR, yy, v)
            yy -= 4.6 * mm
        return min(y - 12 * mm, yy - 2 * mm)

    def parties(self, y):
        c, L, s, b = self.c, self.lang, self.s, self.d["buyer"]
        gap = 6 * mm
        bw = (CW - gap) / 2
        blocks = [
            (tr(L, "seller"), s["name"], [
                (tr(L, "reg"), s["reg_no"]), (tr(L, "vat"), s["vat_no"]),
                (tr(L, "addr"), s["address"]),
                (tr(L, "bank"), f"{s['bank']}, {s['swift']}"), ("IBAN", s["iban"])]),
            (tr(L, "buyer"), b["name"], [
                (tr(L, "reg"), b.get("reg_no", "")), (tr(L, "vat"), b.get("vat_no", "")),
                (tr(L, "addr"), b.get("address", "")),
                ({"lv": "E-pasts", "en": "E-mail"}.get(L, "E-pasts / E-mail"), b.get("email", ""))]),
        ]
        vx = 34 * mm if L == "lv+en" else 25 * mm
        # measure
        heights = []
        for _, name, rows in blocks:
            h = 13 * mm + 4.2 * mm * (len(wrap(name, "Doc-Bold", 9.5, bw - 8 * mm)) - 1)
            for k, v in rows:
                if v:
                    h += 4.2 * mm * len(wrap(v, "Doc", 8, bw - vx - 5 * mm))
            heights.append(h + 2 * mm)
        bh = max(heights)
        for i, (lab, name, rows) in enumerate(blocks):
            x = ML + i * (bw + gap)
            c.setFillColor(C["light"])
            c.roundRect(x, y - bh, bw, bh, 2 * mm, stroke=0, fill=1)
            c.setFillColor(C["blue"] if i == 0 else C["green"])
            c.rect(x, y - bh, 1.2 * mm, bh, stroke=0, fill=1)
            c.setFont("Doc-Bold", 7.5)
            c.setFillColor(C["grey"])
            c.drawString(x + 5 * mm, y - 5.5 * mm, lab)
            c.setFont("Doc-Bold", 9.5)
            c.setFillColor(C["blue"])
            yy = y - 10 * mm
            for ln in wrap(name, "Doc-Bold", 9.5, bw - 8 * mm):
                c.drawString(x + 5 * mm, yy, ln)
                yy -= 4.2 * mm
            for k, v in rows:
                if not v:
                    continue
                c.setFont("Doc", 7.5)
                c.setFillColor(C["grey"])
                c.drawString(x + 5 * mm, yy, k)
                c.setFont("Doc", 8)
                c.setFillColor(C["text"])
                for ln in wrap(v, "Doc", 8, bw - vx - 5 * mm):
                    c.drawString(x + vx, yy, ln)
                    yy -= 4.2 * mm
        return y - bh - 6 * mm

    def para(self, y, text, size=8.5, color=None, font="Doc"):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(color or C["text"])
        for ln in wrap(text, font, size, CW):
            c.drawString(ML, y, ln)
            y -= size * 0.45 * mm + 2.2 * mm
        return y

    def table(self, y, lines, show_prices=True):
        c, L = self.c, self.lang
        cols = [("col_nr", 9 * mm, "l"), ("col_desc", None, "l"), ("col_qty", 16 * mm, "r"),
                ("col_unit", 16 * mm, "l")]
        if show_prices:
            cols += [("col_price", 24 * mm, "r"), ("col_sum", 26 * mm, "r")]
        fixed = sum(w for _, w, _ in cols if w)
        cols = [(k, w if w else CW - fixed, a) for k, w, a in cols]

        def head(y):
            bi = L == "lv+en"
            hh = 10 * mm if bi else 7 * mm
            c.setFillColor(C["blue"])
            c.rect(ML, y - hh, CW, hh, stroke=0, fill=1)
            x = ML
            for k, w, a in cols:
                labs = [(T["lv"][k], "Doc-Bold", 8, white, 4.4 * mm),
                        (T["en"][k], "Doc", 7, HexColor("#C9D3E0"), 8.0 * mm)] if bi else \
                       [(T[L][k], "Doc-Bold", 8, white, 4.6 * mm)]
                for lab, f, sz, col, dy in labs:
                    c.setFont(f, sz)
                    c.setFillColor(col)
                    if a == "r":
                        c.drawRightString(x + w - 2 * mm, y - dy, lab)
                    else:
                        c.drawString(x + 2 * mm, y - dy, lab)
                x += w
            return y - hh

        y = head(y)
        desc_w = cols[1][1] - 4 * mm
        for i, ln in enumerate(lines, 1):
            dl = wrap(ln["desc"], "Doc", 8.5, desc_w)
            sub = wrap(ln.get("note", ""), "Doc", 7.5, desc_w) if ln.get("note") else []
            rh = 4.4 * mm * len(dl) + 3.8 * mm * len(sub) + 3.2 * mm
            if y - rh < 22 * mm:
                y = self.new_page()
                y = head(y)
            if i % 2 == 0:
                c.setFillColor(C["light"])
                c.rect(ML, y - rh, CW, rh, stroke=0, fill=1)
            yy = y - 4.6 * mm
            x = ML
            vals = {"col_nr": str(i), "col_qty": qty_fmt(ln["qty"]), "col_unit": ln.get("unit", ""),
                    "col_price": money(ln.get("price", 0)), "col_sum": money(ln.get("sum", 0))}
            for k, w, a in cols:
                if k == "col_desc":
                    c.setFont("Doc", 8.5)
                    c.setFillColor(C["text"])
                    t = yy
                    for s_ in dl:
                        c.drawString(x + 2 * mm, t, s_)
                        t -= 4.4 * mm
                    c.setFont("Doc", 7.5)
                    c.setFillColor(C["grey"])
                    for s_ in sub:
                        c.drawString(x + 2 * mm, t + 0.6 * mm, s_)
                        t -= 3.8 * mm
                else:
                    c.setFont("Doc-Bold" if k == "col_sum" else "Doc", 8.5)
                    c.setFillColor(C["text"])
                    if a == "r":
                        c.drawRightString(x + w - 2 * mm, yy, vals[k])
                    else:
                        c.drawString(x + 2 * mm, yy, vals[k])
                x += w
            y -= rh
        c.setStrokeColor(C["blue"])
        c.setLineWidth(0.8)
        c.line(ML, y, W - MR, y)
        return y - 4 * mm

    def totals(self, y, net, vat, total, rate):
        c, L, t = self.c, self.lang, self.d["type"]
        bw = 80 * mm
        x = W - MR - bw
        rows = [(tr(L, "net"), money(net)), (tr(L, "vatl", r=qty_fmt(rate)), money(vat))]
        for k, v in rows:
            c.setFont("Doc", 8.5)
            c.setFillColor(C["grey"])
            c.drawString(x + 3 * mm, y - 4 * mm, k)
            c.setFillColor(C["text"])
            c.drawRightString(W - MR - 2 * mm, y - 4 * mm, v)
            y -= 5.5 * mm
        lab = {"act": "total_act", "offer": "total_offer"}.get(t, "total")
        c.setFillColor(C["green"])
        c.roundRect(x, y - 9.5 * mm, bw, 9 * mm, 1.5 * mm, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Doc-Bold", 9.5)
        c.drawString(x + 3 * mm, y - 6.2 * mm, tr(L, lab))
        c.setFont("Doc-Bold", 11.5)
        c.drawRightString(W - MR - 2 * mm, y - 6.4 * mm, f"{money(total)} EUR")
        y -= 14 * mm
        c.setFont("Doc", 7.5)
        c.setFillColor(C["grey"])
        c.drawString(ML, y, tr(L, "words") + ":")
        y -= 4 * mm
        return self.para(y, amount_words(total, L), 8.5, C["text"])

    def payment(self, y):
        c, L, s, d = self.c, self.lang, self.s, self.d
        y -= 2 * mm
        h = 16 * mm if L != "lv+en" else 20 * mm
        c.setStrokeColor(C["blue"])
        c.setLineWidth(0.6)
        c.roundRect(ML, y - h, CW, h, 2 * mm, stroke=1, fill=0)
        key = "pay_adv" if d["type"] == "advance" else "pay"
        txt = tr(L, key, d=fmt_date(d.get("due", d["date"]))) if L != "lv+en" else \
            T["lv"][key].format(d=fmt_date(d.get("due", d["date"])))
        c.setFont("Doc-Bold", 8.5)
        c.setFillColor(C["blue"])
        c.drawString(ML + 4 * mm, y - 5.5 * mm, f"{s['bank']} · SWIFT {s['swift']} · IBAN {s['iban']}")
        yy = self.para_at(ML + 4 * mm, y - 10.5 * mm, txt, CW - 8 * mm, 8)
        if L == "lv+en":
            self.para_at(ML + 4 * mm, yy, T["en"][key].format(d=fmt_date(d.get("due", d["date"]))),
                         CW - 8 * mm, 7.5, C["grey"])
        return y - h - 5 * mm

    def para_at(self, x, y, text, width, size, color=None):
        c = self.c
        c.setFont("Doc", size)
        c.setFillColor(color or C["text"])
        for ln in wrap(text, "Doc", size, width):
            c.drawString(x, y, ln)
            y -= size * 0.45 * mm + 2 * mm
        return y

    def signatures(self, y):
        c, L = self.c, self.lang
        if y < 50 * mm:
            y = self.new_page()
        gap = 12 * mm
        bw = (CW - gap) / 2
        y -= 6 * mm
        for i, (k, name) in enumerate([("handed", self.s["name"]), ("received", self.d["buyer"]["name"])]):
            x = ML + i * (bw + gap)
            c.setFont("Doc-Bold", 8.5)
            c.setFillColor(C["blue"])
            c.drawString(x, y, tr(L, k))
            c.setFont("Doc", 8)
            c.setFillColor(C["text"])
            c.drawString(x, y - 4.5 * mm, name)
            c.setStrokeColor(C["grey"])
            c.setLineWidth(0.5)
            c.line(x, y - 20 * mm, x + bw, y - 20 * mm)
            c.setFont("Doc", 7)
            c.setFillColor(C["grey"])
            c.drawString(x, y - 23.5 * mm, tr(L, "sign") + " · " + tr(L, "date").lower())
        return y - 30 * mm

    def build(self):
        d, L = self.d, self.lang
        lines, net, vat, total, rate = calc(d)
        self.header()
        y = H - 42 * mm
        y = self.title(y)
        y = self.parties(y)
        if d.get("basis"):
            c = self.c
            c.setFont("Doc", 7.5)
            c.setFillColor(C["grey"])
            c.drawString(ML, y, tr(L, "basis") + ":")
            c.setFont("Doc-Bold", 8.5)
            c.setFillColor(C["text"])
            c.drawString(ML + 28 * mm, y, d["basis"])
            y -= 6 * mm
        if d["type"] == "act":
            y = self.para(y, tr_long(L, "act_text"), 8.5) - 1 * mm
        if d["type"] == "offer":
            y = self.para(y, d.get("intro") or tr_long(L, "offer_text"), 8.5) - 1 * mm
        show_prices = d.get("show_prices", True)
        y = self.table(y, lines, show_prices)
        if y < 75 * mm:
            y = self.new_page()
        if show_prices:
            y = self.totals(y, net, vat, total, rate)
        if d.get("notes"):
            y -= 2 * mm
            self.c.setFont("Doc", 7.5)
            self.c.setFillColor(C["grey"])
            self.c.drawString(ML, y, tr(L, "notes") + ":")
            y = self.para(y - 4 * mm, d["notes"], 8.5)
        if d["type"] in ("invoice", "advance"):
            if y < 45 * mm:
                y = self.new_page()
            y = self.payment(y)
            self.para(y, tr_long(L, "einv"), 7.5, C["grey"])
        elif d["type"] == "act":
            self.signatures(y)
        elif d["type"] == "offer":
            sig = d.get("signed_by")
            if sig:
                y = self.para(y - 2 * mm, sig, 8.5, C["blue"], "Doc-Bold")
        self.footer()
        self.c.save()
        return net, vat, total


def tr_long(lang, key):
    if lang == "lv+en":
        return T["lv"][key] + " / " + T["en"][key]
    return T[lang][key]


def fmt_date(s):
    try:
        return dt.date.fromisoformat(s).strftime("%d.%m.%Y")
    except Exception:
        return s


def safe_name(s):
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE)
    return re.sub(r"_+", "_", s).strip("_")[:40]


# ---------------------------------------------------------------- main
def load_yaml(path):
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML is needed to read config.yaml (pip install -r requirements.txt).")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def seller_from(a):
    """--seller JSON/YAML file, or the 'documents' section of config.yaml (+ company.name, colors)."""
    if a.seller:
        p = a.seller
        s = load_yaml(p) if p.endswith((".yaml", ".yml")) else json.load(open(p, encoding="utf-8"))
        base = os.path.dirname(os.path.abspath(p))
        cfg_colors = s.pop("colors", None)
    else:
        if not os.path.exists(a.config):
            sys.exit(f"No seller: give --seller file.json or fill the 'documents' section of {a.config}.")
        cfg = load_yaml(a.config)
        d = cfg.get("documents") or {}
        s = {"name": d.get("legal_name") or (cfg.get("company") or {}).get("name", ""), **d}
        base = os.path.dirname(os.path.abspath(a.config))
        cfg_colors = cfg.get("colors")
    for k in ("name", "reg_no", "address", "bank", "iban"):
        if not s.get(k):
            sys.exit(f"Seller field '{k}' is empty - fill it in (docs/DOCUMENTS.md).")
    for k in ("vat_no", "email", "phone", "web", "swift"):
        s.setdefault(k, "")
    if s.get("logo") and not os.path.isabs(os.path.expanduser(s["logo"])):
        s["logo"] = os.path.join(base, s["logo"])
    elif s.get("logo"):
        s["logo"] = os.path.expanduser(s["logo"])
    if cfg_colors:
        for key, name in (("blue", "main"), ("green", "ok"), ("grey", "neutral"), ("light", "background")):
            if cfg_colors.get(name):
                C[key] = HexColor(cfg_colors[name])
    return s


def main():
    ap = argparse.ArgumentParser(description="FLOKTRON branded documents: invoice, advance invoice, act, offer")
    ap.add_argument("--doc", required=True, help="document file (JSON), see tests/fixtures/documents/")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--seller", help="seller file (JSON or YAML) instead of config.yaml")
    ap.add_argument("--out", default=os.path.join("data", "documents", "out"))
    ap.add_argument("--base", help="base .xlsx: numbering + sheet 'Issued'")
    ap.add_argument("--apply", action="store_true", help="write the register row to --base")
    a = ap.parse_args()

    register_fonts()
    seller = seller_from(a)
    doc = json.load(open(a.doc, encoding="utf-8"))
    if doc.get("type") not in PREFIX:
        sys.exit(f"Unknown type {doc.get('type')!r}: invoice | advance | act | offer")
    if doc.get("lang", "lv") not in ("lv", "en", "lv+en"):
        sys.exit("lang: lv | en | lv+en")
    doc.setdefault("date", dt.date.today().isoformat())
    if doc["type"] in ("invoice", "advance") and not doc.get("due"):
        doc["due"] = (dt.date.fromisoformat(doc["date"]) +
                      dt.timedelta(days=int(doc.get("due_days", 10)))).isoformat()

    number = doc.get("number") or next_number(doc, a.base, seller.get("prefix") or "DOC")
    os.makedirs(a.out, exist_ok=True)
    fname = f"{doc['date']}_{number}_{safe_name(doc['buyer']['name'])}.pdf"
    if doc.get("test"):
        fname = "TEST_" + fname
    path = os.path.join(a.out, fname)
    net, vat, total = Doc(path, seller, doc, number).build()
    print(f"PDF: {path}")
    print(f"  {doc['type']} {number} · net {money(net)} · VAT {money(vat)} · total {money(total)} EUR")
    if a.apply:
        if not a.base:
            sys.exit("--apply needs --base (explicit path).")
        register(a.base, doc, number, net, vat, total, path)
        print(f"  register: row added to '{SHEET}' in {a.base}")
    else:
        print("  register: dry run (add --base ... --apply to record)")
    return path


if __name__ == "__main__":
    main()
