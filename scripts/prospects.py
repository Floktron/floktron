#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prospects.py - new customers that look like your best ones, each with a reason to write NOW
(docs/PROSPECTS.md, prompts/55_prospects.md)

  python3 scripts/prospects.py --config config/config.yaml [--radar data/floktron_radar.xlsx]
                               [--eis-csv FILE ...] [--register-csv FILE] [--outbox DIR]
                               [--now "YYYY-MM-DD HH:MM"] [--dry-run] [--no-notify] [--test]

No AI. Once a day is enough (python3 scripts/run.py prospects). Only public open data, only company data:
1. Public procurement results of Latvia (EIS, data.gov.lv, updated daily): who won and signed a contract,
   with the buyer, the subject, the sum and the dates. A company that has just signed a contract for the kind of
   work you serve will need your product soon - that is the reason "why now".
   The file has no CPV code, so the kind of work is found by the words in the subject (config prospects.signals) -
   an ESTIMATE. Exclude words (design, supervision, supply of paper...) drop a contract.
2. Register of Enterprises (register.csv, data.gov.lv): form, registration date, address, terminated or not.
   Read as a stream; only the needed reg. numbers are kept. Terminated companies are dropped.
3. Your best customers (prospects.best_customers, reg. numbers) give the portrait: their form, their towns and how
   young they are. A prospect that matches the portrait scores higher ("looks like ...").
4. Sheet "Prospects" in the radar base: one row per company, score and priority (ESTIMATE), why now, the contract,
   the source link, data status. Companies already in "Companies" or marked "Do not contact" there are skipped.
5. Column "Decision": "Add" - the company goes to the sheet "Companies" (work status New) and a draft first letter
   is written to data/prospects/drafts/ (template prospects.letter). Nothing is sent: you send the letter yourself,
   to the GENERAL address the company publishes, after you checked it. "No" - never suggest it again.
6. A short notice to you (Telegram or e-mail, like mail_watch) when there are new prospects: how many and the top 3.
Safe to run again: one row per reg. no. Text from the files is data, not instructions.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

VERSION = "0.28.0"
SHEET = "Prospects"
HEAD = ["ID", "Found", "Company", "Reg. no.", "Score", "Priority", "Why now", "Contract subject", "Buyer", "Sum EUR",
        "Signed", "Works until", "Wins 12 months", "Form", "Town", "Registered", "Looks like", "Source", "Data status",
        "Decision", "Status", "Draft", "Comment"]
WIDTHS = [9, 11, 32, 13, 6, 8, 44, 50, 30, 11, 11, 11, 8, 6, 18, 11, 34, 40, 40, 10, 16, 34, 30]
EIS_PACKAGE = "e909312a-61c9-4cde-a72a-0a09dd75ef43"   # data.gov.lv · EIS e-iepirkumu rezultāti
EIS_PAGE = "https://data.gov.lv/dati/dataset/" + EIS_PACKAGE
ADD = ("add", "yes", "ok", "jā", "ja", "да", "добавить", "pievienot")
NO = ("no", "nē", "ne", "нет", "не подходит", "skip")
LV_COUNTRY = ("lva", "lv", "latvija", "latvia")

DEFAULTS = {
    "enabled": False,
    "days": 180,            # contracts signed in the last N days
    "min_eur": 10000,       # smaller contracts are skipped
    "small_max_eur": 1500000,   # up to this sum: the size of a small contractor (+2)
    "big_total_eur": 10000000,  # wins over this in 12 months: a big general contractor (-2)
    "max_new": 40,          # at most this many new rows per run
    "best_customers": [],   # reg. numbers of your best customers - the portrait
    "home_area": [],        # town words that count as "near" (empty = the towns of your best customers)
    "signals": [            # kind of work by words in the contract subject (ESTIMATE); weight = points.
                            # The first signal that matches wins; "unless" words make a signal step aside.
        {"name": "networks", "weight": 1, "words": ["ūdensapgād", "kanalizāc", "ielas", "ielu ", "ceļa", "ceļu", "tilta"],
         "unless": ["flīz", "sanmezgl", "iekšdarb", "iekštelp", "apdar", "ēkas", "ēku "]},
        {"name": "finishing", "weight": 3, "words": ["flīz", "apdar", "iekšdarb", "iekštelp", "remont", "sanmezgl",
                                                     "vannas", "grīd", "apmet", "betona", "fasād", "siltināš"]},
        {"name": "building", "weight": 2, "words": ["būvdarb", "būvniecīb", "pārbūv", "rekonstrukc", "izbūv",
                                                    "atjaunoš", "renovāc", "jumta", "ēkas"]},
    ],
    "exclude_words": ["projektēš", "būvprojekt", "būvuzraudz", "autoruzraudz", "ekspertīz", "konsultāc", "izpēt",
                      "piegāde", "noma", "apdrošin", "uzkopš", "mācīb"],
    "keep_if": ["būvdarb", "remontdarb", "pārbūv"],   # a contract with these words stays even with an exclude word
    "letter": "",           # file with your first-letter template ({company}, {works}); empty = the built-in English one
}

LETTER = """Subject: {product_line}

Hello,

I am writing to you as a contractor: public procurement data shows that {company} has recently signed a new
contract for {works}. {pitch}

If this could be useful, I will gladly send a sample for one of your sites or tell you more by phone.

Best regards,
{signature}

If you do not want to hear from us again, just reply - we will not write again.
"""


# ---------------------------------------------------------------- values
def low(s):
    return str(s or "").strip().lower()


def regno(s):
    return re.sub(r"\D", "", str(s or ""))


def to_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v or "")
    try:
        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
        if m:
            return dt.date(int(m[1]), int(m[2]), int(m[3]))
        m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", s)
        if m:
            return dt.date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        pass
    return None


def to_eur(v):
    s = str(v or "").replace("\xa0", "").replace(" ", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def reader(lines):
    """csv.DictReader with the separator guessed from the header line."""
    it = iter(lines)
    head = next(it, "")
    delim = ";" if head.count(";") > head.count(",") else ","
    cols = [c.strip().strip("﻿") for c in next(csv.reader([head], delimiter=delim))]
    return csv.DictReader(it, fieldnames=cols, delimiter=delim)


# ---------------------------------------------------------------- 1) contracts
def contracts(sources, log):
    from registry_lv import lines
    out = []
    for src in sources:
        try:
            for r in reader(lines(src)):
                out.append({k: str(v or "").strip() for k, v in r.items() if k})
        except Exception as e:  # noqa: BLE001 — one year may be missing; the other still counts
            log(f"prospects: ⚠ {os.path.basename(str(src))}: {str(e)[:100]}")
    return out


def kind_of(text, pc):
    t = " " + low(text) + " "
    if any(w in t for w in pc["exclude_words"]) and not any(w in t for w in pc["keep_if"]):
        return None, 0, []
    for s in pc["signals"]:
        hits = [w for w in s["words"] if w in t]
        if hits and not any(w in t for w in s.get("unless") or []):
            return s["name"], int(s.get("weight", 1)), hits
    return None, 0, []


def candidates(rows, pc, today):
    by = {}
    since = today - dt.timedelta(days=365)
    for c in rows:
        reg = regno(c.get("Uzvaretaja_registracijas_numurs"))
        if len(reg) != 11 or (c.get("Uzvaretaja_valsts") and low(c["Uzvaretaja_valsts"]) not in LV_COUNTRY):
            continue
        if c.get("Izbeigsanas_datums") or "pārtraukt" in low(c.get("Iepirkuma_statuss")):
            continue
        d = to_date(c.get("Liguma_dok_noslegsanas_datums")) or to_date(c.get("Liguma_dok_publicesanas_datums"))
        if not d or d < since or d > today + dt.timedelta(days=1):
            continue
        cur = low(c.get("Aktuala_liguma_summas_valuta"))
        if cur and cur not in ("eur", "euro"):
            continue
        eur = to_eur(c.get("Aktuala_liguma_summa")) or to_eur(c.get("Sakotneja_liguma_summa"))
        e = by.setdefault(reg, {"reg": reg, "name": c.get("Uzvaretaja_nosaukums") or reg, "wins": 0, "total": 0.0, "best": None})
        e["wins"] += 1
        e["total"] += eur
        name, part = c.get("Iepirkuma_nosaukums") or "", c.get("Iepirkuma_dalas_nosaukums") or ""
        kind, weight, hits = kind_of(name + " " + part, pc)
        if not kind or eur < float(pc["min_eur"]):
            continue
        link = c.get("Hipersaite_EIS_kura_pieejams_zinojums") or ""
        x = {"kind": kind, "weight": weight, "hits": hits, "eur": eur, "date": d,
             "till": to_date(c.get("Liguma_izpilde_lidz")), "buyer": c.get("Pasutitaja_nosaukums") or "",
             "subject": (name + (" · " + part if part and part not in name else ""))[:240],
             "link": link if link.startswith("http") else EIS_PAGE}
        b = e["best"]
        if b is None or (x["weight"], x["date"]) > (b["weight"], b["date"]):
            e["best"] = x
    days = int(pc["days"])
    return {k: v for k, v in by.items() if v["best"] and (today - v["best"]["date"]).days <= days}


# ---------------------------------------------------------------- 2) register
def register(regs, source, log):
    """{reg: {type, registered, town, gone}} for the given reg. numbers only (stream)."""
    if not regs:
        return {}
    from registry_lv import lines
    out = {}
    try:
        for r in reader(lines(source)):
            rc = regno(r.get("regcode"))
            if rc in regs:
                out[rc] = {"type": (r.get("type") or "").strip(), "registered": (r.get("registered") or "")[:10],
                           "town": (r.get("city") or "").strip() or (r.get("address") or "").split(",")[-1].strip(),
                           "gone": bool((r.get("terminated") or "").strip() or (r.get("closed") or "").strip())}
    except Exception as e:  # noqa: BLE001
        log(f"prospects: ⚠ register not read ({str(e)[:100]}) - no form / registration date")
    return out


def portrait(best, reg_info, pc, today):
    """What the best customers have in common: forms, towns, the oldest age in years."""
    rows = [reg_info[r] for r in best if r in reg_info]
    forms = {x["type"].upper() for x in rows if x["type"]}
    towns = [low(w) for w in pc.get("home_area") or []] or sorted({low(x["town"]) for x in rows if x["town"]})
    ages = [(today - to_date(x["registered"])).days / 365.25 for x in rows if to_date(x["registered"])]
    return {"forms": forms, "towns": towns, "max_age": (max(ages) + 3) if ages else None, "n": len(rows)}


def score(e, u, pt, pc, today):
    b = e["best"]
    s = b["weight"]
    days = (today - b["date"]).days
    s += 3 if days <= 30 else 2 if days <= 90 else 1
    eur = f"{round(b['eur']):,}".replace(",", " ")
    why = [f"signed {b['date']:%d.%m.%Y} · {eur} EUR · {', '.join(b['hits'][:2]).strip()}"]
    if b["till"] and b["till"] >= today:
        s += 1
        why.append("works under way")
    s += 2 if b["eur"] <= float(pc["small_max_eur"]) else 1 if b["eur"] <= 5 * float(pc["small_max_eur"]) else 0
    if e["total"] > float(pc["big_total_eur"]):
        s -= 2
    if e["wins"] >= 2:
        s += 1
    like = []
    if u.get("type") and u["type"].upper() in pt["forms"]:
        s += 1
        like.append(u["type"])
    if u.get("town") and any(t and t in low(u["town"]) for t in pt["towns"]):
        s += 1
        like.append(u["town"])
    reg = to_date(u.get("registered"))
    if reg and pt["max_age"] and (today - reg).days / 365.25 <= pt["max_age"]:
        s += 1
        like.append(f"young (since {reg.year})")
    if b["weight"] >= 3:
        like.append(b["kind"])
    pr = 1 if s >= 9 else 2 if s >= 6 else 3
    return s, pr, "; ".join(why), ", ".join(like) + (" - like your best customers" if len(like) >= 2 and pt["n"] else "")


# ---------------------------------------------------------------- 3) sheets
def ensure(wb):
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    if SHEET not in wb.sheetnames:
        ws = wb.create_sheet(SHEET)
        ws.append(HEAD)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1A365D")
        for n, w in enumerate(WIDTHS):
            ws.column_dimensions[get_column_letter(n + 1)].width = w
        ws.freeze_panes = "D2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(HEAD))}1"
    return wb[SHEET]


def companies(wb):
    """(sheet, header row, column index by name, {reg: work status})"""
    if "Companies" not in wb.sheetnames:
        return None, 0, {}, {}
    ws = wb["Companies"]
    hr = next((r for r in range(1, 6) if str(ws.cell(r, 1).value or "").strip() == "Found"), 1)
    head = {str(ws.cell(hr, c).value or ""): c for c in range(1, ws.max_column + 1)}
    known = {}
    for r in ws.iter_rows(min_row=hr + 1, values_only=True):
        rg = regno(r[head["Reg. no."] - 1]) if "Reg. no." in head else ""
        if rg:
            known[rg] = low(r[head["Work status"] - 1]) if "Work status" in head else ""
    return ws, hr, head, known


def letter_text(cfg, pc, company, works):
    tpl = LETTER
    path = pc.get("letter")
    if path:
        p = path if os.path.isabs(path) else os.path.join(os.path.dirname(cfg.get("_path") or ROOT), path)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                tpl = f.read()
    co = cfg.get("company") or {}
    sig = "\n".join(x for x in [co.get("manager_name") or co.get("contact_name"), co.get("name"),
                                 co.get("phone"), (cfg.get("documents") or {}).get("email") or co.get("email")] if x)
    vals = {"company": company, "works": works, "signature": sig or "(your name, company, phone)",
            "product_line": pc.get("product_line") or f"{co.get('name') or 'Our company'} - for your new contract",
            "pitch": pc.get("pitch") or "(two sentences: what you offer and the one fact that proves it)"}
    return re.sub(r"\{(\w+)\}", lambda m: str(vals.get(m[1], m[0])), tpl)


WORKS = {"finishing": "finishing / renovation works", "building": "construction works", "networks": "construction works"}


# ---------------------------------------------------------------- run
def run(cfg, radar, eis, reg_src, now, outbox=None, dry=False, test=False, no_notify=False, log=print):
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
    from mail_watch import notify
    pc = dict(DEFAULTS)
    pc.update(cfg.get("prospects") or {})
    today = now.date()
    wb = openpyxl.load_workbook(radar)
    ws = ensure(wb)
    head = [str(c.value or "") for c in ws[1]]
    H = {h: i for i, h in enumerate(head)}
    rows = [r for r in ws.iter_rows(min_row=2) if r[H["Reg. no."]].value]
    mine = {regno(r[H["Reg. no."]].value): r for r in rows}
    wc, hr, ch, known = companies(wb)
    drafts = os.path.join(os.path.dirname(os.path.abspath(radar)), "prospects", "drafts")
    state_path = os.path.join(os.path.dirname(os.path.abspath(radar)), ".prospects_state.json")
    st = {}
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            st = json.load(f)

    # presses in Telegram (✅ Add / ⛔ Not a fit, data/task_actions.jsonl) → column "Decision", handled right below
    import task_notice
    acts, off = task_notice.read_actions(task_notice.actions_path(cfg), st.get("tg_offset", 0), "prospect")
    by_id = {str(r[H["ID"]].value): r for r in mine.values()}
    for a in acts:
        r = by_id.get(str(a["key"]))
        if r is not None:
            r[H["Decision"]].value = "Add" if a["ans"] == "y" else "No"
            old = str(r[H["Comment"]].value or "")
            r[H["Comment"]].value = (old + "; " if old else "") + task_notice.note(a)
    st["tg_offset"] = off

    # decisions
    added_to = []
    for rg, r in mine.items():
        dec, status = low(r[H["Decision"]].value), low(r[H["Status"]].value)
        if dec in ADD and not status.startswith("in companies") and wc is not None:
            if rg not in known:
                line = {"Found": today.isoformat(), "Country": "LV", "Reg. no.": rg, "Name": r[H["Company"]].value,
                        "Type": r[H["Form"]].value, "Registered": r[H["Registered"]].value, "Address": r[H["Town"]].value,
                        "Matched": r[H["Why now"]].value, "Goal": "Client", "Query": r[H["ID"]].value,
                        "Contacts (public, company only)": "", "Data status": "PUBLIC (EIS, UR) · score ESTIMATE",
                        "Work status": "New"}
                wc.append([line.get(h, "") for h, _ in sorted(ch.items(), key=lambda x: x[1])])
                known[rg] = "new"
            kind = (st.get("kind") or {}).get(rg, "building")
            os.makedirs(drafts, exist_ok=True)
            fn = os.path.join(drafts, f"{r[H['ID']].value}_{re.sub(r'[^A-Za-z0-9]+', '_', str(r[H['Company']].value))[:40]}.txt")
            if not dry:
                with open(fn, "w", encoding="utf-8") as f:
                    f.write("DRAFT · not sent. Send it yourself, to the GENERAL address the company publishes, after you checked it.\n"
                            + ("TEST · FICTIONAL\n" if test else "") + "- " * 30 + "\n"
                            + letter_text(cfg, pc, r[H["Company"]].value, WORKS.get(kind, "construction works")))
            r[H["Status"]].value = "In Companies"
            r[H["Draft"]].value = os.path.relpath(fn, os.path.dirname(os.path.abspath(radar)))
            added_to.append(r[H["ID"]].value)
        elif dec in NO and status != "not suitable":
            r[H["Status"]].value = "Not suitable"

    # new prospects
    cand = candidates(contracts(eis, log), pc, today)
    best = [regno(x) for x in pc.get("best_customers") or [] if regno(x)]
    stop = {k for k, v in known.items() if "do not contact" in v or "не беспокоить" in v}
    new = {k: v for k, v in cand.items() if k not in mine and k not in known and k not in best and k not in stop}
    info = register(set(new) | set(best), reg_src, log) if (new or best) and reg_src else {}
    pt = portrait(best, info, pc, today)
    scored = []
    for rg, e in new.items():
        u = info.get(rg, {})
        if u.get("gone"):
            continue
        s, pr, why, like = score(e, u, pt, pc, today)
        scored.append((s, rg, e, u, pr, why, like))
    scored.sort(key=lambda x: (-x[0], -x[2]["best"]["date"].toordinal()))
    nums = [int(m[1]) for r in rows if (m := re.match(r"P-(\d+)", str(r[H["ID"]].value or "")))]
    n = max(nums or [0])
    new_rows = []
    for s, rg, e, u, pr, why, like in scored[:int(pc["max_new"])]:
        n += 1
        b = e["best"]
        st.setdefault("kind", {})[rg] = b["kind"]
        v = {"ID": f"P-{n:04d}", "Found": today.isoformat(), "Company": e["name"], "Reg. no.": rg, "Score": s, "Priority": pr,
             "Why now": why, "Contract subject": b["subject"], "Buyer": b["buyer"], "Sum EUR": round(b["eur"], 2),
             "Signed": b["date"].strftime("%d.%m.%Y"), "Works until": b["till"].strftime("%d.%m.%Y") if b["till"] else "",
             "Wins 12 months": e["wins"], "Form": u.get("type", ""), "Town": u.get("town", ""),
             "Registered": u.get("registered", ""), "Looks like": like, "Source": b["link"],
             "Data status": "Contract and register - PUBLIC (EIS, UR · data.gov.lv); kind of work and score - ESTIMATE",
             "Decision": "", "Status": "New", "Draft": "", "Comment": "TEST · FICTIONAL" if test else ""}
        ws.append([v.get(h, "") for h in head])
        new_rows.append(v)
    if not dry:
        wb.save(radar)
        tmp = state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f)
        os.replace(tmp, state_path)
    err = ""
    lang = (cfg.get("company") or {}).get("language", "en")
    if new_rows and not no_notify and task_notice.via_telegram(cfg, cfg.get("prospects")):
        # one company = one message with ✅ Add / ⛔ Not a fit; only the top 3, the rest is one line without buttons
        top3 = sorted(new_rows, key=lambda x: x["Priority"])[:3]
        for v in top3:
            fact = f"{v['Signed']} · {round(v['Sum EUR'] or 0):,} EUR".replace(",", " ") + (f" · {str(v['Contract subject'])[:70]}" if v["Contract subject"] else "")
            err = task_notice.send(cfg, ("[TEST] " if test else "") + f"🔎 {v['Company']}\n{fact}\n{v['Why now'].split(';')[0]}",
                                   "prospect", v["ID"], lang, outbox) or err
        if len(new_rows) > 3:
            err = task_notice.info(cfg, f"🔎 +{len(new_rows) - 3} · FLOKTRON prospects (radar base) — nothing to do now.", outbox) or err
    elif new_rows and not no_notify:
        top = "\n".join(f"• {v['Company']} - {v['Why now'].split(';')[0]}" for v in sorted(new_rows, key=lambda x: x["Priority"])[:3])
        text = (f"🔎 FLOKTRON · new prospects: {len(new_rows)}\n{top}\n"
                "Sheet \"Prospects\" in the radar base. Write \"Add\" in the column \"Decision\" - the company goes to "
                "\"Companies\" and a draft letter is written (nothing is sent). \"No\" - never suggest it again.")
        err = notify(cfg, cfg.get("prospects") or {}, text, ("[TEST] " if test else "") + "FLOKTRON · new prospects", outbox, log)
    log(f"prospects {VERSION}: winners with a matching contract {len(cand)}, new {len(new_rows)}, "
        f"added to Companies {len(added_to)}, portrait from {pt['n']} best customers" + (f"; ⚠ {err}" if err else ""))
    return dict(new=len(new_rows), added=added_to, candidates=len(cand), portrait=pt, rows=new_rows)


def sources(today, log):
    """EIS CSV links for this and last year and the register link, from the data.gov.lv catalogue."""
    from registry_lv import csv_url, resources
    eis = []
    try:
        for x in resources(EIS_PACKAGE):
            u = x.get("url") or ""
            if u.lower().endswith(".csv") and any(str(y) in u for y in (today.year, today.year - 1)):
                eis.append(u)
    except Exception as e:  # noqa: BLE001
        log(f"prospects: ⚠ EIS catalogue: {str(e)[:100]}")
    try:
        reg = csv_url()
    except Exception as e:  # noqa: BLE001
        log(f"prospects: ⚠ register: {str(e)[:100]}")
        reg = ""
    return sorted(eis), reg


def main(argv=None):
    from mail_watch import load_yaml
    ap = argparse.ArgumentParser(description="FLOKTRON prospects: companies like your best customers, with a reason to write now")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--radar", default=os.path.join(DATA, "floktron_radar.xlsx"))
    ap.add_argument("--eis-csv", nargs="*", default=[], help="procurement results CSV files instead of the internet")
    ap.add_argument("--register-csv", default="", help="register.csv instead of the internet")
    ap.add_argument("--outbox", help="write the notice as .txt here instead of sending it")
    ap.add_argument("--now", help='"YYYY-MM-DD HH:MM" (tests)')
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-notify", action="store_true")
    ap.add_argument("--test", action="store_true", help="fictional data: rows marked TEST")
    a = ap.parse_args(argv)
    cfg = load_yaml(a.config)
    cfg["_path"] = a.config
    if not (cfg.get("prospects") or {}).get("enabled", False) and not (a.test or a.dry_run):
        print("prospects.enabled is false in config.yaml - nothing to do (docs/PROSPECTS.md).")
        return 0
    if not os.path.exists(a.radar):
        print(f"No radar base {a.radar} - create it first: python3 scripts/radar_create.py")
        return 1
    now = dt.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else dt.datetime.now()
    eis, reg = (a.eis_csv, a.register_csv) if a.eis_csv else sources(now.date(), print)
    if a.register_csv:
        reg = a.register_csv
    if not eis:
        print("prospects: no procurement data (offline?) - the next run tries again")
        return 1
    run(cfg, os.path.abspath(a.radar), eis, reg, now, outbox=a.outbox, dry=a.dry_run, test=a.test, no_notify=a.no_notify)
    return 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    sys.exit(main())
