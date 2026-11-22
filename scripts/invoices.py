# -*- coding: utf-8 -*-
"""FLOKTRON · invoices.py — supplier invoices -> accounting, checked against your bank statement.

Two steps, like everywhere in FLOKTRON:
  1. Your AI assistant READS each document (PDF, photo, scan; any language) and writes one record per document
     into data/invoices/extraction.json (format: docs/INVOICES.md, rules: prompts/50_invoices.md).
     The assistant never invents a number: what it cannot read stays empty and the document is flagged.
  2. This script (no AI, no network) does the bookkeeping logic:
       - skips duplicates (same file content, or same supplier + type + number) — also inside one batch;
       - reads your bank statements (CSV from any bank; Swedbank-style PDF if `pypdf` is installed) and finds the
         payment of every document: amount + date window + invoice number or supplier name in the payment;
         a payment with the same amount but neither number nor name is NOT taken (shown as "similar payment");
       - sets a status and writes tasks for the finance ray:
           paid and found                     -> no task (goes into the hand-over task)
           proforma closed by a final invoice -> no task
           proforma / order / advance paid, no final invoice -> "request the final invoice"
           not paid, due in the future        -> "pay by <date>"
           not found in the statement         -> "check the payment"
           foreign VAT charged / reverse charge -> one task for the accountant (ESTIMATE, to confirm)
         plus one hand-over task: "pass N documents to accounting".
Dry run by default (prints only). --apply writes the sheet "Invoices" and rows in "Tasks" of data/floktron_base.xlsx.
Nothing is paid, sent or deleted. Your bank login is never needed: you download the statement yourself.

Usage:
    python3 scripts/invoices.py                       # dry run with config.yaml → invoices
    python3 scripts/invoices.py --apply               # write to the base
    python3 scripts/invoices.py --test --apply        # fictional data: tasks get the prefix "TEST:"
Options: --folder <dir>  --extraction <json>  --statements <dir>  --base <xlsx>  --iban <IBAN>  --ray L7  --today YYYY-MM-DD
Try it on the fictional set:  python3 scripts/invoices.py --folder tests/fixtures/invoices/docs \\
    --extraction tests/fixtures/invoices/extraction.json --statements tests/fixtures/invoices/docs/statements \\
    --iban LV80BANK0000435195001 --today 2026-11-22 --test
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

HEAD = ["ID", "Added", "Supplier", "Reg. / VAT no.", "Type", "Document no.", "Date", "Due", "Net", "VAT", "Total",
        "Currency", "Payment method", "Status", "Payment in statement", "Linked to", "Category", "File", "Hash",
        "Tasks", "Checked", "Comment"]
TYPES = {"invoice": "Invoice", "proforma": "Proforma", "advance": "Advance invoice", "order": "Order (not an invoice)",
         "delivery": "Delivery note (not an invoice)", "credit": "Credit note"}
PAY = {"bank": "transfer", "card": "card", "advance": "advance set-off", "cash": "cash"}
SKIP_DIRS = {"statements", "Bankas izraksti", "_done", "_archive"}


def d(s):
    return dt.date.fromisoformat(s) if s else None


def fmt(x):
    return x.strftime("%d.%m.%Y") if x else "—"


def money(x):
    return f"{x:,.2f}".replace(",", " ")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def workday(day, n):
    while n > 0:
        day += dt.timedelta(days=1)
        if day.weekday() < 5:
            n -= 1
    return day


def nfc(s):
    return unicodedata.normalize("NFC", s)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def to_float(v):
    s = str(v or "").strip().replace(" ", "").replace(" ", "")
    if re.search(r",\d{1,2}$", s):
        s = s.replace(".", "").replace(",", ".")
    s = s.replace(",", "")
    try:
        return abs(float(s))
    except ValueError:
        return None


def to_date(v):
    s = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------- bank statements
CSV_COLS = {  # header aliases (lower case) → field
    "date": ("date", "booking date", "datums", "trx.date", "op.datums", "data", "kuupäev", "datum"),
    "cp": ("counterparty", "payee", "beneficiary", "saņēmējs/maksātājs", "partner", "name", "gavėjas/mokėtojas", "saaja/maksja"),
    "amount": ("amount", "summa", "suma", "summa eur", "betrag"),
    "details": ("details", "description", "informācija saņēmējam", "reference", "paskirtis", "selgitus", "verwendungszweck"),
    "dc": ("debit/credit", "debets/kredīts", "d/k", "type"),
}


def read_csv(path):
    raw = open(path, encoding="utf-8-sig", errors="replace").read()
    dialect = csv.Sniffer().sniff(raw[:4000], delimiters=";,\t")
    rows = list(csv.reader(raw.splitlines(), dialect))
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]
    ix = {k: next((head.index(a) for a in al if a in head), None) for k, al in CSV_COLS.items()}
    if ix["date"] is None or ix["amount"] is None:
        return []
    out = []
    for n, r in enumerate(rows[1:]):
        def g(k):
            return r[ix[k]] if ix[k] is not None and ix[k] < len(r) else ""
        date, amt = to_date(g("date")), to_float(g("amount"))
        if not date or amt is None:
            continue
        if g("dc").strip().upper() in ("K", "C", "CREDIT", "KREDĪTS"):
            continue  # money in, not a payment
        out.append(dict(date=date, cp=g("cp"), amount=amt, details=g("details"), code="CSV", arch=f"{os.path.basename(path)}:{n}"))
    return out


def read_pdf(path, our_iban):
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    text = "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
    head = text[:1500]
    m = re.search(r"IBAN:\s*([A-Z0-9 ]{20,34})", head)
    if not re.search(r"(Account statement|Konta pārskats)", head) or not m:
        return []
    if our_iban and not m.group(1).replace(" ", "").startswith(our_iban):
        return []  # another account
    blocks, cur = [], None
    for ln in text.split("\n"):
        if re.match(r"^\d\d\.\d\d\.\d{4}\s", ln) and not re.search(r"balance|atlikums", ln, re.I):
            cur = [ln]
            blocks.append(cur)
        elif cur is not None:
            cur.append(ln)
    out = []
    for b in blocks:
        body = "\n".join(b)
        m = re.search(r"(\d{16})\s+(\w{3})\s", body)
        if not m or m.group(2) == "KOM":
            continue  # no transaction / bank fee
        arch, code = m.group(1), m.group(2)
        date = dt.datetime.strptime(b[0][:10], "%d.%m.%Y").date()
        cp = b[0][10:].strip()
        if code == "CTX":
            c = re.search(r"CTX PIRKUMS \S+ (\d\d\.\d\d\.\d{4}) ([\d.]+) (\w{3}) \(\d+\)\s*(.*)", body, re.S)
            if not c or c.group(3) != "EUR":
                continue
            amount, date = float(c.group(2)), dt.datetime.strptime(c.group(1), "%d.%m.%Y").date()
            cp = " ".join(x for x in c.group(4).split("\n")[:2] if not re.fullmatch(r"[\d.]+", x.strip()))
            details = "card"
        else:
            a = re.search(arch + r".*?(\d+\.\d\d)\s*$", body, re.M)
            if not a:
                continue
            amount = float(a.group(1))
            after = body.split(a.group(0), 1)[1].strip().split("\n")
            details = after[0] if after else ""
        out.append(dict(date=date, cp=cp, amount=amount, details=details, code=code, arch=arch))
    return out


def read_statements(folder, our_iban="", gaps=None):
    txns, used = {}, []
    if not folder or not os.path.isdir(folder):
        return [], used
    for root, _, files in os.walk(folder):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            low = fn.lower()
            if "privat" in low:
                continue
            got = read_csv(p) if low.endswith(".csv") else read_pdf(p, our_iban) if low.endswith(".pdf") else []
            if got is None:
                if gaps is not None:
                    gaps.append(f"{fn}: PDF statements need 'pip install pypdf' — or download the statement as CSV")
                continue
            if got:
                used.append(os.path.relpath(p, folder))
            for t in got:
                txns[(t["arch"], t["code"], round(t["amount"], 2))] = t
    return list(txns.values()), used


# ---------------------------------------------------------------- matching and rules
def match_payments(docs, txns):
    free = list(txns)
    payable = [x for x in docs if x["type"] not in ("delivery", "credit") and x.get("to_pay", x["total"]) > 0]
    for doc in sorted(payable, key=lambda x: x["date"]):
        best, best_s = None, -1.0
        for t in free:
            if abs(t["amount"] - doc["total"]) > 0.005:
                continue
            lag = (t["date"] - d(doc["date"])).days
            if lag < -5 or lag > 90:
                continue
            txt = norm(t["cp"] + " " + t["details"])
            s = (10 if norm(doc["number"]) and norm(doc["number"]) in txt else 0) \
                + (2 if any(norm(k) in txt for k in doc.get("bank_kw", []) if norm(k)) else 0) + max(0, 1 - abs(lag) / 90)
            if s > best_s:
                best, best_s = t, s
        if best is None:
            continue
        if best_s < 2:
            doc["similar"] = best
            continue
        doc["pay"] = dict(best, how="number in payment" if best_s >= 10 else "name + amount + date")
        free.remove(best)
    by_sup = {}
    for doc in payable:
        if not doc.get("pay"):
            by_sup.setdefault(doc["reg"], []).append(doc)
    for group in by_sup.values():
        if len(group) < 2:
            continue
        total = round(sum(x["total"] for x in group), 2)
        for t in free:
            txt = norm(t["cp"] + " " + t["details"])
            if abs(t["amount"] - total) < 0.005 and any(norm(k) in txt for k in group[0].get("bank_kw", []) if norm(k)):
                for x in group:
                    x["pay"] = dict(t, how=f"one payment for {len(group)} documents")
                    x.pop("similar", None)
                free.remove(t)
                break


def decide(docs, today, home="LV"):
    by_num = {(x["reg"], x["number"]): x for x in docs}
    tasks, foreign, rc, final = [], [], [], {}
    for x in docs:
        x.update(link="", status="", comment=x.get("note", ""))
        if x.get("settles") and (x["reg"], x["settles"]) in by_num:
            by_num[(x["reg"], x["settles"])]["closed_by"] = x["number"]
    for x in docs:
        pay = x.get("pay")
        if x["type"] == "delivery":
            x["status"] = "Not a payment document"
            x["link"] = f"invoice {x['ref']}" if x.get("ref") else ""
            continue
        if x["type"] == "credit":
            x["status"] = "Credit note — check it is set off"
            tasks.append(dict(doc=x, due=workday(today, 3), text=f"Credit note {x['supplier']} no. {x['number']} ({money(x['total'])} EUR): check that it is set off or refunded"))
            continue
        if x["type"] == "invoice" and x.get("settles"):
            p = by_num.get((x["reg"], x["settles"]))
            x["link"] = f"proforma {x['settles']}"
            if p and p.get("pay"):
                x["status"] = f"Paid by advance {fmt(p['pay']['date'])}"
            else:
                x["status"] = "Advance set-off — advance not found in statement"
                tasks.append(dict(doc=x, due=workday(today, 2), text=f"Check the advance {x['settles']} ({x['supplier']}): final invoice {x['number']} is set off against it, but the payment is not in the statement"))
        elif x["type"] == "proforma" and x.get("closed_by"):
            x["status"] = f"Closed by invoice {x['closed_by']}" + (f" · paid {fmt(pay['date'])}" if pay else "")
            x["link"] = f"invoice {x['closed_by']}"
        elif pay and (x["type"] in ("proforma", "order") or (x["type"] == "advance" and not x.get("counts_as_tax_invoice"))):
            x["status"] = f"Paid {fmt(pay['date'])} · no final invoice"
            final.setdefault(x["reg"], []).append(x)
        elif pay:
            x["status"] = f"Paid {fmt(pay['date'])}"
        else:
            due = d(x.get("due"))
            if due and due >= today:
                x["status"] = f"To pay by {fmt(due)}"
                tasks.append(dict(doc=x, due=due, text=f"Pay {x['supplier']} {TYPES[x['type']].lower()} no. {x['number']} of {fmt(d(x['date']))}: {money(x['total'])} EUR by {fmt(due)}"))
            else:
                sim = x.get("similar")
                hint = f"; similar payment {fmt(sim['date'])} {sim['amount']:.2f} to '{sim['cp'][:25]}' — another payee?" if sim else ""
                x["status"] = "Not found in statement" + (" (similar payment)" if sim else "")
                tasks.append(dict(doc=x, due=workday(today, 2), text=f"Check the payment: {x['supplier']} no. {x['number']} of {fmt(d(x['date']))}, {money(x['total'])} EUR — not found in the statement" + (f", was due {fmt(due)}" if due else "") + hint))
        vc = x.get("vat_country") or home
        if vc != home and x["vat"] > 0 and not x.get("closed_by"):
            foreign.append(x)
            x["comment"] = "; ".join(filter(None, [x["comment"], f"VAT of {vc} {money(x['vat'])} EUR — not {home} VAT (ESTIMATE: not deductible at home, confirm with the accountant)"]))
        if vc != home and x["vat"] == 0 and x.get("reverse_charge"):
            rc.append(x)
            x["comment"] = "; ".join(filter(None, [x["comment"], f"reverse charge: self-account the VAT in the {home} return (ESTIMATE)"]))
    for grp in final.values():
        x, nums = grp[0], ", ".join(z["number"] for z in grp)
        kind = {"proforma": "proforma", "order": "order", "advance": "advance invoice"}[x["type"]]
        order = f" (order {x['order']})" if x.get("order") else ""
        tasks.append(dict(doc=grp, due=workday(today, 3), text=(
            f"Ask {x['supplier']} for the final invoice for {kind} no. {nums}{order}: paid {money(sum(z['total'] for z in grp))} EUR "
            f"on {fmt(x['pay']['date'])} ({PAY.get(x['pay_method'], x['pay_method'])}); without it the cost cannot be booked")))
    if foreign or rc:
        t = "For the accountant (ESTIMATE, to confirm): "
        if foreign:
            t += (f"foreign VAT in {len(foreign)} invoices ({'/'.join(sorted({z['vat_country'] for z in foreign}))}), "
                  f"{money(sum(z['vat'] for z in foreign))} EUR — usually not deductible at home; give your own VAT number when ordering in the EU. ")
        if rc:
            t += f"Reverse charge in {len(rc)} invoices (no. {', '.join(z['number'] for z in rc)}, {money(sum(z['net'] for z in rc))} EUR) — self-account the VAT."
        tasks.append(dict(doc=foreign + rc, due=workday(today, 5), text=t.strip()))
    return tasks


# ---------------------------------------------------------------- main
def load_cfg(path):
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get("invoices") or {}
    except (OSError, ImportError):
        return {}


def run(a):
    cfg = load_cfg(a.config)
    inv = os.path.join(DATA, "invoices")
    folder = a.folder or cfg.get("folder") or os.path.join(inv, "inbox")
    extraction = a.extraction or cfg.get("extraction") or os.path.join(inv, "extraction.json")
    statements = a.statements or cfg.get("statements") or os.path.join(inv, "statements")
    our_iban = (a.iban or cfg.get("our_iban") or "").replace(" ", "")
    home = (cfg.get("home_country") or (cfg.get("our_vat") or "LV")[:2]).upper()
    ray = a.ray or cfg.get("ray") or "L7"
    base = a.base or os.path.join(DATA, "floktron_base.xlsx")
    today = d(a.today) if a.today else dt.date.today()
    if not os.path.exists(extraction):
        print(f"No extraction file yet: {extraction}\nAsk your AI assistant to read the documents (prompts/50_invoices.md).")
        return 1
    recs = {nfc(r["file"]): dict(r, file=nfc(r["file"])) for r in json.load(open(extraction, encoding="utf-8"))["docs"]}

    wb, have_hash, have_key = None, set(), set()
    if a.apply or os.path.exists(base):
        import openpyxl
        sys.path.insert(0, HERE)
        import safe_xlsx  # noqa: F401  (supplier names and numbers come from outside: never let them become formulas)
        if os.path.exists(base):
            wb = openpyxl.load_workbook(base)
            if "Invoices" in wb.sheetnames:
                ws = wb["Invoices"]
                h = [c.value for c in ws[1]]
                for r in ws.iter_rows(min_row=2, values_only=True):
                    row = dict(zip(h, r))
                    have_hash.add(row.get("Hash"))
                    have_key.add((row.get("Reg. / VAT no."), row.get("Type"), str(row.get("Document no."))))
        elif a.apply:
            sys.exit(f"Base not found: {base} (run scripts/base_create.py first)")

    new, dup, unread, seen = [], [], [], {}
    forwarded = re.compile(r"(^|/)(FW|FWD|RE)[_: ]|\(\d\)\.pdf$", re.I)
    for rel, rec in sorted(recs.items(), key=lambda kv: (bool(forwarded.search(kv[0])), kv[0])):
        p = os.path.join(folder, rel)
        if not os.path.exists(p):
            print("! file not found:", rel)
            continue
        rec["hash"] = sha(p)
        if rec["hash"][:12] in have_hash or (rec["reg"], TYPES[rec["type"]], rec["number"]) in have_key:
            dup.append(f"{rel} (already in the base)")
        elif rec["hash"] in seen:
            dup.append(f"{rel} = copy of {seen[rec['hash']]}")
        else:
            seen[rec["hash"]] = rel
            new.append(rec)
    for root, dirs, files in os.walk(folder):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for fn in files:
            rel = nfc(os.path.relpath(os.path.join(root, fn), folder))
            if fn.lower().endswith((".pdf", ".jpg", ".jpeg", ".png", ".heic")) and rel not in recs:
                unread.append(rel)

    gaps = []
    txns, used = read_statements(statements, our_iban, gaps)
    match_payments(new, txns)
    tasks = decide(new, today, home)

    pre, tpre = ("TINV", "TI") if a.test else ("INV", "I")
    seq = (wb["Invoices"].max_row if wb is not None and "Invoices" in wb.sheetnames else 1)
    for x in sorted(new, key=lambda z: z["date"]):
        x["id"] = f"{pre}-{seq:04d}"
        seq += 1
    if new:
        fin = [x for x in new if x["type"] not in ("delivery",)]
        tot = sum(x["total"] for x in fin if not x.get("closed_by") and x["type"] != "credit")
        paid = sum(1 for x in fin if x["status"].startswith(("Paid", "Closed")))
        dates = [d(x["date"]) for x in new]
        tasks.append(dict(doc=new, due=workday(today, 3), text=(
            f"Pass {len(new)} supplier documents ({fmt(min(dates))}–{fmt(max(dates))}) to accounting, {money(tot)} EUR; "
            f"payment found in the statement: {paid} of {len(fin)}. Sheet 'Invoices', {min(x['id'] for x in new)}…{max(x['id'] for x in new)}")))
    stamp = today.strftime("%Y%m%d")
    for i, t in enumerate(tasks, 1):
        t["id"] = f"{tpre}{stamp}-{i:02d}"
        for z in (t["doc"] if isinstance(t["doc"], list) else [t["doc"]]):
            z.setdefault("task_ids", []).append(t["id"])

    print(f"Statements: {len(txns)} payments from " + ("; ".join(used) or "— none —"))
    for g in gaps:
        print("  gap:", g)
    print(f"New documents: {len(new)} · duplicates / already in base: {len(dup)} · not read yet: {len(unread)}")
    for u in dup:
        print("  duplicate:", u)
    for u in unread:
        print("  not read yet (no record in the extraction file):", u)
    for x in sorted(new, key=lambda z: z["date"]):
        p = x.get("pay")
        print(f"  {x['id']} {x['date']} {x['supplier'][:30]:30} {TYPES[x['type']][:15]:15} {x['number']:13} {x['total']:9.2f}  {x['status']}"
              + (f"  [{p['how']}]" if p else ""))
    print(f"Tasks for {ray}: {len(tasks)}")
    for t in tasks:
        print(f"  {t['id']} due {fmt(t['due'])}: {t['text']}")
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            f.write("| ID | Date | Supplier | Type | No. | Total, EUR | Status | Payment |\n|---|---|---|---|---|---:|---|---|\n")
            for x in sorted(new, key=lambda z: z["date"]):
                p = x.get("pay")
                f.write(f"| {x['id']} | {fmt(d(x['date']))} | {x['supplier']} | {TYPES[x['type']]} | {x['number']} | {money(x['total'])} | {x['status']} | "
                        + (f"{fmt(p['date'])} · {p['how']}" if p else "—") + " |\n")
            f.write("\n| Task | Due | Text |\n|---|---|---|\n" + "".join(f"| {t['id']} | {fmt(t['due'])} | {t['text']} |\n" for t in tasks))
    if not a.apply:
        print("DRY RUN — nothing written. Add --apply to write to the base.")
        return 0

    from openpyxl.styles import Font, PatternFill
    if "Invoices" not in wb.sheetnames:
        ws = wb.create_sheet("Invoices")
        ws.append(HEAD)
        for c in ws[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1A365D")
        ws.freeze_panes = "A2"
    ws = wb["Invoices"]
    for x in sorted(new, key=lambda z: z["date"]):
        p = x.get("pay")
        ws.append([x["id"], today.isoformat(), x["supplier"], x["reg"], TYPES[x["type"]], x["number"], x["date"], x.get("due") or "",
                   x["net"], x["vat"], x["total"], x.get("currency", "EUR"), PAY.get(x["pay_method"], x["pay_method"]), x["status"],
                   f"{fmt(p['date'])} · {p['amount']:.2f} · {p['cp'][:30]} · {p['how']}" if p else "", x["link"],
                   x.get("category", "Purchase"), x["file"], x["hash"][:12], ", ".join(x.get("task_ids", [])), "no",
                   ("TEST · fictional company; " if a.test else "") + x["comment"]])
    wt = wb["Tasks"]
    for t in tasks:
        wt.append([t["id"], today.isoformat(), ray, ("TEST: " if a.test else "") + t["text"], "invoices → accounting",
                   t["due"].isoformat(), "New", "", "", "", ""])
    tmp = base + ".tmp"
    wb.save(tmp)
    os.replace(tmp, base)
    print(f"WRITTEN to {base}: Invoices +{len(new)}, Tasks +{len(tasks)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON invoices → accounting")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--folder")
    ap.add_argument("--extraction")
    ap.add_argument("--statements")
    ap.add_argument("--base")
    ap.add_argument("--iban")
    ap.add_argument("--ray")
    ap.add_argument("--today")
    ap.add_argument("--report")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--test", action="store_true")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
