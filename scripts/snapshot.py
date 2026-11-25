# -*- coding: utf-8 -*-
"""FLOKTRON · company snapshot — the state of your company on one date, in two files.

  snapshot_<date>_<profile>_<lang>.pdf    readable, branded (EN / LV / RU)
  snapshot_<date>_<profile>_<lang>.json   machine-readable: every figure with its status and source,
                                          plus the SHA-256 of the PDF, so both files prove to be one snapshot

You choose what goes out with a profile, then add or remove sections:
  partner   a partner or investor, after an NDA. The company valuation is off unless --plus valuation
  no_bank   the same, without bank details and balances
  tax       for the tax office: only PUBLIC and DEAL figures — no estimates, no plans
  public    only PUBLIC figures marked "public"

LOCK — not a switch. A fact marked "secret" never leaves, in any profile. When the snapshot is built, its whole
text is checked for locked words (built-in: passwords, keys, tokens, recipes, formulations; add your own in
config.yaml → snapshot.locked_words). One hit stops the run and nothing is written.
Names of clients and sites in the base are never read.

Sources (read only, nothing is changed):
  data/snapshot/facts.json     your facts: section, label, value, status, source, date, sensitivity (docs/SNAPSHOT.md)
  data/floktron_base.xlsx      sheets Stock, Orders, Purchases, Invoices, Rentals — counts and totals only

Usage:
  python3 scripts/snapshot.py --test --profile partner --lang en --out /tmp/snapshot     # fictional Demo SIA
  python3 scripts/snapshot.py --profile tax --lang lv                                   # your data → data/snapshot/out/
  python3 scripts/snapshot.py --profile partner --plus valuation --minus bank
  python3 scripts/snapshot.py --test --all --out /tmp/snapshot                          # every profile x language

No AI, no network. Optional package: reportlab (for the PDF). Without it the JSON is still written.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
SCHEMA = "floktron.snapshot/1"
LANGS = ("en", "lv", "ru")

STATUS = {
    "PUBLIC": {"en": "PUBLIC", "lv": "PUBLISKS", "ru": "ПУБЛИЧНО"},
    "DEAL": {"en": "DEAL", "lv": "DARĪJUMS", "ru": "СДЕЛКА"},
    "ESTIMATE": {"en": "ESTIMATE", "lv": "APLĒSE", "ru": "ОЦЕНКА"},
    "SCENARIO": {"en": "SCENARIO", "lv": "SCENĀRIJS", "ru": "СЦЕНАРИЙ"},
}
STATUS_ALIASES = {"ПУБЛИЧНО": "PUBLIC", "СДЕЛКА": "DEAL", "ОЦЕНКА": "ESTIMATE", "СЦЕНАРИЙ": "SCENARIO",
                  "PUBLISKS": "PUBLIC", "DARĪJUMS": "DEAL", "APLĒSE": "ESTIMATE", "SCENĀRIJS": "SCENARIO"}
SENSITIVITY = ("public", "nda", "bank", "valuation", "internal", "secret")

SECTIONS = ["company", "people", "product_ip", "operations", "invoices", "finance", "contracts", "bank", "valuation"]
SECTION_TITLE = {
    "company": {"en": "Company", "lv": "Uzņēmums", "ru": "Компания"},
    "people": {"en": "Shareholders and board", "lv": "Dalībnieki un valde", "ru": "Участники и правление"},
    "product_ip": {"en": "Product and intellectual property", "lv": "Produkts un intelektuālais īpašums", "ru": "Продукт и интеллектуальная собственность"},
    "operations": {"en": "Stock, orders, purchases", "lv": "Noliktava, pasūtījumi, iepirkumi", "ru": "Склад, заказы, закупки"},
    "invoices": {"en": "Supplier invoices", "lv": "Piegādātāju rēķini", "ru": "Счета поставщиков"},
    "finance": {"en": "Finance", "lv": "Finanses", "ru": "Финансы"},
    "contracts": {"en": "Contracts", "lv": "Līgumi", "ru": "Договоры"},
    "bank": {"en": "Bank", "lv": "Banka", "ru": "Банк"},
    "valuation": {"en": "Company valuation", "lv": "Uzņēmuma novērtējums", "ru": "Оценка компании"},
}
PROFILES = {
    "partner": dict(sections=[s for s in SECTIONS if s != "valuation"], status=None, sens={"public", "nda", "bank"}),
    "no_bank": dict(sections=[s for s in SECTIONS if s not in ("bank", "valuation")], status=None, sens={"public", "nda"}),
    "tax": dict(sections=["company", "people", "operations", "invoices", "finance", "contracts", "bank"],
                status={"PUBLIC", "DEAL"}, sens={"public", "nda", "bank"}),
    "public": dict(sections=["company", "people", "product_ip"], status={"PUBLIC"}, sens={"public"}),
}
PROFILE_TITLE = {
    "partner": {"en": "for a partner / investor (under NDA)", "lv": "partnerim / investoram (pēc NDA)", "ru": "для партнёра / инвестора (после NDA)"},
    "no_bank": {"en": "without bank details", "lv": "bez bankas datiem", "ru": "без банковских данных"},
    "tax": {"en": "for the tax office", "lv": "nodokļu administrācijai", "ru": "для налоговой"},
    "public": {"en": "public", "lv": "publisks", "ru": "публичный"},
}
TXT = {
    "title": {"en": "Company snapshot", "lv": "Uzņēmuma stāvokļa kopsavilkums", "ru": "Снимок компании"},
    "as_of": {"en": "as of", "lv": "uz", "ru": "на"},
    "profile": {"en": "Profile", "lv": "Profils", "ru": "Профиль"},
    "cols": {"en": ["Item", "Value", "Status", "Source", "As of"], "lv": ["Rādītājs", "Vērtība", "Statuss", "Avots", "Datums"],
             "ru": ["Показатель", "Значение", "Статус", "Источник", "На дату"]},
    "legend": {"en": "Statuses: PUBLIC — open source; DEAL — signed document or completed transaction; ESTIMATE — the company's own calculation; SCENARIO — a plan, not a fact.",
               "lv": "Statusi: PUBLISKS — atklāts avots; DARĪJUMS — parakstīts dokuments vai veikta operācija; APLĒSE — uzņēmuma aprēķins; SCENĀRIJS — plāns, nevis fakts.",
               "ru": "Статусы: ПУБЛИЧНО — открытый источник; СДЕЛКА — подписанный документ или проведённая операция; ОЦЕНКА — расчёт компании; СЦЕНАРИЙ — план, не факт."},
    "excluded": {"en": "Not in this profile: {n} rows.", "lv": "Šajā profilā nav iekļautas {n} rindas.", "ru": "Не включено в этот профиль: {n} строк."},
    "pair": {"en": "Machine-readable copy: {j} (it stores the SHA-256 of this PDF).", "lv": "Mašīnlasāma kopija: {j} (tajā ir šī PDF SHA-256).",
             "ru": "Машиночитаемая копия: {j} (в ней записан SHA-256 этого PDF)."},
    "tax_note": {"en": "This is not a tax return. It can be attached to an application in the tax office's e-service (in Latvia: EDS, Iesniegums).",
                 "lv": "Šī nav nodokļu deklarācija. To var pievienot iesniegumam VID EDS.",
                 "ru": "Это не налоговая декларация. Файл можно приложить к заявлению в e-сервисе налоговой (в Латвии: EDS, Iesniegums)."},
    "page": {"en": "p.", "lv": "lpp.", "ru": "стр."},
    "made": {"en": "made", "lv": "sagatavots", "ru": "сформировано"},
}
# label, value of the rows the script adds from the base
BASE_T = {
    "stock": {"en": "Stock: {x}", "lv": "Atlikums: {x}", "ru": "Остаток: {x}"},
    "orders": {"en": "Customer orders (count, by status)", "lv": "Klientu pasūtījumi (gab., pēc statusa)", "ru": "Заказы клиентов (шт., по статусу)"},
    "purchases": {"en": "Purchases (total / open)", "lv": "Iepirkumi (kopā / atvērti)", "ru": "Закупки (всего / открыто)"},
    "rentals": {"en": "Rental items (total / out)", "lv": "Nomas vienības (kopā / izsniegtas)", "ru": "Прокат (всего / выдано)"},
    "inv_total": {"en": "Supplier invoices in the base (count / total)", "lv": "Piegādātāju rēķini bāzē (gab. / summa)", "ru": "Счета поставщиков в базе (шт. / сумма)"},
    "inv_open": {"en": "Not paid or not found in the statement (count / total)", "lv": "Nav apmaksāti vai nav atrasti izrakstā (gab. / summa)", "ru": "Не оплачено или не найдено в выписке (шт. / сумма)"},
}

LOCKED = [r"\bpassword", r"\bpasswd\b", r"\bapi[ _-]?key", r"\btoken\b", r"\bPIN\b", r"\bseed phrase", r"\bprivate key",
          r"\brecipe", r"\bformulation", r"парол", r"рецептур", r"parole\b", r"receptūr"]


class Locked(Exception):
    pass


# ---------- helpers ----------
def money(x):
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


def dmy(s):
    try:
        return dt.date.fromisoformat(str(s)[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return str(s)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def status_code(s):
    s = str(s or "").strip().upper()
    s = STATUS_ALIASES.get(s, s)
    return s if s in STATUS else "ESTIMATE"  # an unknown status is never shown as a fact


def label(lbl, lang):
    if isinstance(lbl, dict):
        return lbl.get(lang) or lbl.get("en") or next(iter(lbl.values()), "")
    return str(lbl or "")


def fact(section, fid, lbl, value, status, source, as_of, sensitivity="nda"):
    if section not in SECTIONS:
        raise ValueError(f"unknown section '{section}' in fact '{fid}' — use one of: {', '.join(SECTIONS)}")
    sensitivity = sensitivity if sensitivity in SENSITIVITY else "secret"  # unknown → never leaves
    return dict(section=section, id=str(fid), label=lbl, value=str(value), status=status_code(status),
                source=str(source or ""), as_of=str(as_of or ""), sensitivity=sensitivity)


def load_config(path):
    if not path or not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------- the base: counts and totals only ----------
def read_base(path, as_of):
    import openpyxl
    import safe_xlsx  # noqa: F401 — the demo base is written; outside text never becomes a formula
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    src, out = os.path.basename(path), []

    def sheet(name):
        if name not in wb.sheetnames:
            return [], []
        it = wb[name].iter_rows(values_only=True)
        head = [str(c or "").strip() for c in next(it, [])]
        return head, [r for r in it if any(v not in (None, "") for v in r)]

    def get(head, r, name):
        return r[head.index(name)] if name in head and head.index(name) < len(r) else None

    def lbl(key, x=""):
        return {k: v.format(x=x) for k, v in BASE_T[key].items()}

    h, rows = sheet("Stock")
    for r in rows:
        item, qty = get(h, r, "Item"), get(h, r, "On hand")
        if item in (None, "") or qty in (None, ""):
            continue
        day = get(h, r, "Counted on")
        day = day.date().isoformat() if hasattr(day, "date") else (str(day) if day else as_of)
        out.append(fact("operations", f"stock:{get(h, r, 'Code') or item}", lbl("stock", item),
                        f"{qty} {get(h, r, 'Unit') or ''}".strip(), get(h, r, "Figure status") or "ESTIMATE", f"{src} / Stock", day))
    h, rows = sheet("Orders")  # the Client column is never read
    if rows:
        by = {}
        for r in rows:
            k = str(get(h, r, "Status") or "—")
            by[k] = by.get(k, 0) + 1
        out.append(fact("operations", "orders", lbl("orders"), f"{len(rows)} ({', '.join(f'{k}: {v}' for k, v in sorted(by.items()))})",
                        "DEAL", f"{src} / Orders", as_of))
    h, rows = sheet("Purchases")
    if rows:
        done = ("received", "closed", "done", "saņemts", "получено", "закрыто")
        n_open = sum(1 for r in rows if str(get(h, r, "Status") or "").strip().lower() not in done)
        out.append(fact("operations", "purchases", lbl("purchases"), f"{len(rows)} / {n_open}", "DEAL", f"{src} / Purchases", as_of))
    h, rows = sheet("Rentals")  # the "Where (site)" column is never read
    if rows:
        free = ("in stock", "free", "returned", "noliktavā", "на складе")
        n_out = sum(1 for r in rows if str(get(h, r, "Status") or "").strip().lower() not in free)
        out.append(fact("operations", "rentals", lbl("rentals"), f"{len(rows)} / {n_out}", "DEAL", f"{src} / Rentals", as_of))
    h, rows = sheet("Invoices")
    if rows:
        total = n_open = 0
        open_sum = 0.0
        for r in rows:
            try:
                v = float(get(h, r, "Total") or 0)
            except (TypeError, ValueError):
                v = 0.0
            total += v
            st = str(get(h, r, "Status") or "").lower()
            if not st.startswith("paid") and "closed" not in st and "not a payment" not in st:
                n_open += 1
                open_sum += v
        out.append(fact("invoices", "inv_total", lbl("inv_total"), f"{len(rows)} / {money(total)} EUR", "DEAL", f"{src} / Invoices", as_of))
        out.append(fact("invoices", "inv_open", lbl("inv_open"), f"{n_open} / {money(open_sum)} EUR", "DEAL", f"{src} / Invoices", as_of))
    return out


# ---------- choose ----------
def choose(facts, profile, plus=(), minus=()):
    p = PROFILES[profile]
    sections = [s for s in SECTIONS if (s in p["sections"] or s in plus) and s not in minus]
    sens = set(p["sens"]) | ({"valuation"} if "valuation" in plus else set()) | ({"bank"} if "bank" in plus and profile != "public" else set())
    if "bank" in minus:
        sens.discard("bank")
    keep, dropped = [], 0
    for f in facts:
        if f["sensitivity"] in ("secret", "internal") or f["section"] not in sections or f["sensitivity"] not in sens \
                or (p["status"] and f["status"] not in p["status"]):
            dropped += 1
            continue
        keep.append(f)
    return [s for s in sections if any(f["section"] == s for f in keep)], keep, dropped


def lock_check(company, keep, extra_words=()):
    text = "\n".join([str(v) for v in company.values()] +
                     [f"{label(f['label'], l)}\n{f['value']}\n{f['source']}" for f in keep for l in LANGS])
    hits = []
    for pat in LOCKED + [re.escape(w) for w in extra_words if str(w).strip()]:
        m = re.search(pat, text, re.I)
        if m:
            hits.append(m.group(0))
    if hits:
        raise Locked("locked words found: " + ", ".join(sorted(set(hits))))


# ---------- PDF ----------
def find_font():
    for reg, bold in [
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]:
        if os.path.exists(reg) and os.path.exists(bold):
            return reg, bold
    return None


def make_pdf(path, company, sections, keep, lang, profile, as_of, dropped, json_name, test, colors_cfg):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font = find_font()
    if font:
        pdfmetrics.registerFont(TTFont("F", font[0]))
        pdfmetrics.registerFont(TTFont("FB", font[1]))
        R, B = "F", "FB"
    else:  # no TTF found: Latin only
        R, B = "Helvetica", "Helvetica-Bold"
    c = {"main": "#1A365D", "ok": "#4A9928", "neutral": "#717171", "background": "#f3f3f3"}
    c.update({k: v for k, v in (colors_cfg or {}).items() if isinstance(v, str) and v.startswith("#")})
    MAIN, OK, GREY, LIGHT = (colors.HexColor(c[k]) for k in ("main", "ok", "neutral", "background"))
    st = dict(
        h1=ParagraphStyle("h1", fontName=B, fontSize=18, leading=22, textColor=MAIN),
        sub=ParagraphStyle("sub", fontName=R, fontSize=9.5, leading=13, textColor=GREY),
        h2=ParagraphStyle("h2", fontName=B, fontSize=11.5, textColor=MAIN, spaceBefore=8, spaceAfter=4, keepWithNext=1),
        td=ParagraphStyle("td", fontName=R, fontSize=8, leading=10),
        th=ParagraphStyle("th", fontName=B, fontSize=7.5, leading=10, textColor=colors.white),
        note=ParagraphStyle("note", fontName=R, fontSize=7.5, leading=10, textColor=GREY),
    )
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    name = company.get("name", "")
    made = dt.datetime.now().strftime("%d.%m.%Y %H:%M")
    mark = "TEST · FICTIONAL" if test else ""

    def frame(cv, doc):
        cv.saveState()
        cv.setFillColor(MAIN)
        cv.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, fill=1, stroke=0)
        cv.setFillColor(OK)
        cv.rect(0, A4[1] - 7.2 * mm, A4[0], 1.2 * mm, fill=1, stroke=0)
        cv.setFont(R, 7.5)
        cv.setFillColor(GREY)
        cv.drawString(15 * mm, 9 * mm, f"{name} · {TXT['title'][lang]} {TXT['as_of'][lang]} {dmy(as_of)} · {TXT['made'][lang]} {made}")
        cv.drawRightString(A4[0] - 15 * mm, 9 * mm, f"{TXT['page'][lang]} {doc.page}")
        if mark:
            cv.setFont(B, 46)
            cv.setFillColor(GREY)
            cv.setFillAlpha(0.08)
            cv.translate(A4[0] / 2, A4[1] / 2)
            cv.rotate(35)
            cv.drawCentredString(0, 0, mark)
        cv.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"{TXT['title'][lang]} {dmy(as_of)}", author=name)
    flow = [Paragraph(esc(f"{TXT['title'][lang]} · {name}"), st["h1"]), Spacer(1, 2),
            Paragraph(esc(f"{TXT['as_of'][lang].capitalize()} {dmy(as_of)} · {TXT['profile'][lang]}: {PROFILE_TITLE[profile][lang]}"
                          + (f" · {mark}" if mark else "")), st["sub"]), Spacer(1, 6)]
    widths = [48 * mm, 46 * mm, 22 * mm, 40 * mm, 24 * mm]
    for s in sections:
        flow.append(Paragraph(esc(SECTION_TITLE[s][lang]), st["h2"]))
        data = [[Paragraph(esc(h), st["th"]) for h in TXT["cols"][lang]]]
        for f in (f for f in keep if f["section"] == s):
            data.append([Paragraph(esc(x), st["td"]) for x in
                         (label(f["label"], lang), f["value"], STATUS[f["status"]][lang], f["source"], dmy(f["as_of"]))])
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), MAIN), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        flow.append(t)
    flow += [Spacer(1, 10), Paragraph(esc(TXT["legend"][lang]), st["note"])]
    if dropped:
        flow.append(Paragraph(esc(TXT["excluded"][lang].format(n=dropped)), st["note"]))
    if profile == "tax":
        flow.append(Paragraph(esc(TXT["tax_note"][lang]), st["note"]))
    flow.append(Paragraph(esc(TXT["pair"][lang].format(j=json_name)), st["note"]))
    doc.build(flow, onFirstPage=frame, onLaterPages=frame)


# ---------- one snapshot ----------
def snapshot(facts_doc, base_rows, profile, lang, out, plus=(), minus=(), test=False, as_of=None, cfg=None):
    """Builds one snapshot. Returns (pdf path or None, json path). Raises Locked — then nothing is written."""
    cfg = cfg or {}
    as_of = as_of or dt.date.today().isoformat()
    company = dict(facts_doc.get("company") or {})
    facts = [fact(f["section"], f["id"], f["label"], f["value"], f.get("status"), f.get("source"), f.get("as_of", as_of),
                  f.get("sensitivity", "nda")) for f in facts_doc.get("facts", [])] + list(base_rows)
    sections, keep, dropped = choose(facts, profile, plus, minus)
    lock_check(company, keep, (cfg.get("snapshot") or {}).get("locked_words") or [])
    os.makedirs(out, exist_ok=True)
    stem = f"snapshot_{as_of}_{profile}_{lang}" + ("_TEST" if test else "")
    pdf, js = os.path.join(out, stem + ".pdf"), os.path.join(out, stem + ".json")
    try:
        make_pdf(pdf, company, sections, keep, lang, profile, as_of, dropped, os.path.basename(js), test, cfg.get("colors"))
    except ImportError:
        pdf = None
        print("reportlab is not installed — JSON only (pip install reportlab for the PDF)")
    doc = {
        "schema": SCHEMA, "test_fictional": bool(test), "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "as_of": as_of, "profile": profile, "language": lang, "company": company,
        "sections": [{"id": s, "title": SECTION_TITLE[s][lang], "items": [
            {"id": f["id"], "label": label(f["label"], lang), "value": f["value"], "status": f["status"],
             "status_label": STATUS[f["status"]][lang], "source": f["source"], "as_of": f["as_of"]}
            for f in keep if f["section"] == s]} for s in sections],
        "excluded_rows": dropped,  # only the number — labels of excluded rows are not stored
        "lock_check": "passed",
        "status_legend": {k: v[lang] for k, v in STATUS.items()},
        "pdf": {"name": os.path.basename(pdf), "sha256": sha256(pdf)} if pdf else None,
    }
    with open(js, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return pdf, js


# ---------- fictional demo ----------
def demo_facts(as_of):
    L = lambda en, lv, ru: {"en": en, "lv": lv, "ru": ru}
    reg = "Register of Enterprises, open data (fictional)"
    rows = [
        ("company", "nace", L("Main activity (NACE)", "Pamatdarbība (NACE)", "Основной вид деятельности (NACE)"), "46.75", "PUBLIC", reg, "public"),
        ("company", "capital", L("Share capital", "Pamatkapitāls", "Основной капитал"), "2 800,00 EUR", "PUBLIC", reg, "public"),
        ("company", "vat", L("VAT payer since", "PVN maksātājs kopš", "Плательщик НДС с"), "01.03.2025", "PUBLIC", "public VAT register (fictional)", "public"),
        ("company", "email", L("Official e-mail", "Oficiālais e-pasts", "Официальный e-mail"), "info@demo.example", "PUBLIC", "company website (fictional)", "public"),
        ("people", "board", L("Board member", "Valdes loceklis", "Член правления"), "Demo Person (fictional)", "PUBLIC", reg, "public"),
        ("people", "owner", L("Shareholder, share", "Dalībnieks, daļa", "Участник, доля"), "Demo Person — 100 %", "PUBLIC", reg, "public"),
        ("product_ip", "tm", L("Trademark", "Preču zīme", "Товарный знак"), "DEMOBRAND® (fictional)", "PUBLIC", "trademark register (fictional)", "public"),
        ("product_ip", "patent", L("Patent", "Patents", "Патент"), "application filed (number not disclosed)", "DEAL", "attorney confirmation (fictional)", "nda"),
        ("product_ip", "how", L("Know-how", "Zinātība", "Ноу-хау"), "kept secret — never exported", "DEAL", "internal file", "secret"),
        ("finance", "turnover", L("Turnover last year", "Apgrozījums pērn", "Оборот за прошлый год"), "18 400,00 EUR", "PUBLIC", "annual report (fictional)", "public"),
        ("finance", "turnover_ytd", L("Turnover this year to date", "Apgrozījums šogad", "Оборот с начала года"), "31 250,00 EUR", "DEAL", "accounting (fictional)", "nda"),
        ("finance", "unit_cost", L("Average cost per unit", "Vidējā pašizmaksa par vienību", "Средняя себестоимость единицы"), "0,95 EUR", "ESTIMATE", "financial model (fictional)", "nda"),
        ("finance", "plan", L("Turnover plan next year", "Plānotais apgrozījums nākamgad", "План оборота на следующий год"), "120 000,00 EUR", "SCENARIO", "financial model (fictional)", "nda"),
        ("finance", "grant", L("State aid (contract)", "Valsts atbalsts (līgums)", "Господдержка (договор)"), "5 000,00 EUR", "DEAL", "aid agreement (fictional)", "nda"),
        ("contracts", "clients", L("Active customer contracts", "Spēkā esoši klientu līgumi", "Действующие договоры с клиентами"), "2 (names not disclosed)", "DEAL", "contract register (fictional)", "nda"),
        ("contracts", "suppliers", L("Supply contracts", "Piegādes līgumi", "Договоры поставки"), "3", "DEAL", "contract register (fictional)", "nda"),
        ("bank", "iban", L("Bank account", "Norēķinu konts", "Расчётный счёт"), "LV00DEMO0000000000000 (fictional)", "DEAL", "bank (fictional)", "bank"),
        ("bank", "balance", L("Account balance", "Konta atlikums", "Остаток на счёте"), "7 315,40 EUR", "DEAL", "bank statement (fictional)", "bank"),
        ("valuation", "valuation", L("Valuation for negotiations", "Novērtējums sarunām", "Оценка для переговоров"), "250 000 EUR (fictional)", "ESTIMATE", "own calculation (fictional)", "valuation"),
        ("company", "competitors", L("Competitors", "Konkurenti", "Конкуренты"), "internal list", "ESTIMATE", "internal", "internal"),
    ]
    return {"company": {"name": "TEST · FICTIONAL Demo SIA", "reg_no": "40000000099 (fictional)", "vat_no": "LV40000000099 (fictional)",
                        "address": "Parauga iela 1, Rīga, LV-1001 (fictional)"},
            "facts": [dict(section=s, id=i, label=l, value=v, status=x, source=src, as_of=as_of, sensitivity=se) for s, i, l, v, x, src, se in rows]}


def demo_base(path, as_of):
    import shutil
    import openpyxl
    import safe_xlsx  # noqa: F401
    shutil.copy(os.path.join(ROOT, "templates", "floktron_base_empty.xlsx"), path)
    wb = openpyxl.load_workbook(path)
    add = {
        "Stock": [["Bucket 5 l (TEST)", "D-B5", "pcs", 42, as_of, 10, "DEAL", "TEST · FICTIONAL"],
                  ["Sachet (TEST)", "D-S1", "pcs", 610, as_of, 200, "DEAL", "TEST · FICTIONAL"],
                  ["Raw material, group A (TEST)", "D-RA", "kg", 85, as_of, 30, "ESTIMATE", "TEST · FICTIONAL"]],
        "Orders": [["O-1", as_of, "HIDDEN CLIENT NAME", "bucket", 5, "yes", "shipped", "", ""],
                   ["O-2", as_of, "HIDDEN CLIENT NAME 2", "sachet", 20, "yes", "in progress", "", ""]],
        "Purchases": [["P-1", "Demo supplier", "D-RA", 50, as_of, as_of, "received", "", ""],
                      ["P-2", "Demo supplier", "D-RB", 20, as_of, as_of, "on the way", "", ""]],
        "Rentals": [["R-01", "barrel 200 l", "HIDDEN SITE", as_of, "at customer", ""], ["R-02", "barrel 100 l", "", "", "in stock", ""]],
        "Invoices": [["I-1", as_of, "Demo supplier", "", "invoice", "D-1", as_of, as_of, 100, 21, 121, "EUR", "bank", "Paid 2026-11-20"],
                     ["I-2", as_of, "Demo supplier", "", "invoice", "D-2", as_of, as_of, 200, 42, 242, "EUR", "bank", "To pay by 2026-11-30"]],
    }
    for name, rows in add.items():
        for r in rows:
            wb[name].append(r)
    wb.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON company snapshot → PDF + JSON (docs/SNAPSHOT.md)")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--facts", help="facts file (default: config snapshot.facts or data/snapshot/facts.json)")
    ap.add_argument("--base", help="base workbook (default: data/floktron_base.xlsx)")
    ap.add_argument("--out", help="output folder (default: data/snapshot/out)")
    ap.add_argument("--profile", choices=list(PROFILES), default="partner")
    ap.add_argument("--lang", choices=LANGS)
    ap.add_argument("--plus", default="", help="sections to add, comma-separated, e.g. valuation")
    ap.add_argument("--minus", default="", help="sections to remove, comma-separated, e.g. bank,contracts")
    ap.add_argument("--as-of", dest="as_of", help="date YYYY-MM-DD (default: today)")
    ap.add_argument("--test", action="store_true", help="fictional TEST · FICTIONAL Demo SIA")
    ap.add_argument("--all", action="store_true", help="every profile x language")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    sc = cfg.get("snapshot") or {}
    as_of = a.as_of or dt.date.today().isoformat()
    plus, minus = [s for s in a.plus.split(",") if s], [s for s in a.minus.split(",") if s]
    for s in plus + minus:
        if s not in SECTIONS:
            ap.error(f"unknown section {s} — use: {', '.join(SECTIONS)}")
    out = a.out or os.path.join(ROOT, sc.get("out") or "data/snapshot/out")
    if a.test:
        os.makedirs(out, exist_ok=True)
        facts_doc = demo_facts(as_of)
        base = os.path.join(out, "demo_base_TEST.xlsx")
        demo_base(base, as_of)
    else:
        fp = a.facts or os.path.join(ROOT, sc.get("facts") or "data/snapshot/facts.json")
        if not os.path.exists(fp):
            sys.exit(f"No facts file: {fp} — see docs/SNAPSHOT.md (try --test first)")
        with open(fp, encoding="utf-8") as f:
            facts_doc = json.load(f)
        base = a.base or os.path.join(ROOT, "data", "floktron_base.xlsx")
        base = base if os.path.exists(base) else None
    base_rows = read_base(base, as_of) if base else []
    lang = a.lang or ((cfg.get("company") or {}).get("language") if (cfg.get("company") or {}).get("language") in LANGS else "en")
    combos = [(p, l) for p in PROFILES for l in LANGS] if a.all else [(a.profile, lang)]
    for p, l in combos:
        try:
            pdf, js = snapshot(facts_doc, base_rows, p, l, out, plus, minus, a.test, as_of, cfg)
        except Locked as e:
            sys.exit(f"STOP — {p}/{l}: {e}. Nothing was written. Remove the words or mark the fact as secret.")
        print(f"OK {p}/{l}: {pdf or '(no PDF)'} + {os.path.basename(js)}")


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    main()
