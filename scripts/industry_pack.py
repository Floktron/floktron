# -*- coding: utf-8 -*-
"""FLOKTRON · industry_pack.py — a ready set of radar keywords and sources for one industry.

A new company should not invent 30 search words from scratch. An industry pack (templates/industry/<id>.json)
gives a neutral starting set: keywords in several languages, typical public sources, registry queries and
supply-chain examples. The setup wizard asks three things — industry, country/city, 3–5 competitors — and
this script adds everything to the radar. The company then adds or removes words itself: in the "Keywords"
sheet, or in Telegram (/words, /addword, /delword — managers only).

Nothing is overwritten: rows already in the radar stay, the same keyword is never added twice.

Usage:
    python3 scripts/industry_pack.py list
    python3 scripts/industry_pack.py show construction
    python3 scripts/industry_pack.py apply construction --country LV --city Rīga --competitor "Name 1" --competitor "Name 2"
    python3 scripts/industry_pack.py words                      # priority-A keywords now in the radar
    python3 scripts/industry_pack.py add "fasādes siltināšana"   # one own keyword (first language column)
    python3 scripts/industry_pack.py off "cementa cena"          # switch a keyword off (priority → off, row stays)
Options: --radar <file>  --dry (apply: show what would be added, change nothing)
"""
import argparse
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "templates", "industry")
RADAR = os.path.join(ROOT, "data", "floktron_radar.xlsx")
OFF = "off"


def list_packs():
    out = []
    for f in sorted(os.listdir(PACKS)) if os.path.isdir(PACKS) else []:
        if f.endswith(".json"):
            with open(os.path.join(PACKS, f), encoding="utf-8") as fh:
                p = json.load(fh)
            out.append(p)
    return out


def load_pack(name):
    if not re.fullmatch(r"[a-z0-9_-]{1,40}", name or ""):
        sys.exit(f"Unknown pack: {name!r}")
    path = os.path.join(PACKS, name + ".json")
    if not os.path.exists(path):
        sys.exit(f"No pack {name!r}. Packs: " + ", ".join(p["id"] for p in list_packs()))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def header_row(ws):
    for r in range(1, 6):
        if str(ws.cell(r, 1).value or "").strip() in ("ID", "Type", "Company", "Date", "Region"):
            return r
    return 1


def head(ws):
    h = header_row(ws)
    return h, [str(c.value or "") for c in ws[h]]


def lang_columns(names):
    out = {}
    for i, t in enumerate(names):
        m = re.match(r"Keyword (\w+)", t)
        if m:
            out[m.group(1).lower()] = i
    return out


def norm(t):
    return re.sub(r"\s+", " ", str(t or "")).strip().casefold()


def next_id(ws, prefix, h):
    n = 0
    for (v,) in ws.iter_rows(min_row=h + 1, max_col=1, values_only=True):
        m = re.fullmatch(re.escape(prefix) + r"(\d+)", str(v or ""))
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


def existing_words(ws, h, cols):
    have = set()
    for row in ws.iter_rows(min_row=h + 1, values_only=True):
        for i in cols.values():
            if i < len(row) and row[i]:
                have.add(norm(row[i]))
    return have


def keyword_row(names, cols, kid, cluster, texts, priority, signal, comment):
    row = [""] * len(names)
    row[0], row[1] = kid, cluster
    for lang, i in cols.items():
        row[i] = texts.get(lang, "")
    for col, val in (("Priority", priority), ("Signal type", signal), ("Comment", comment)):
        if col in names:
            row[names.index(col)] = val
    return row


def apply(wb, pack, country="", city="", competitors=(), today=None):
    """Add the pack to an open radar workbook. Returns {what: count}."""
    today = today or datetime.date.today().isoformat()
    added = {"keywords": 0, "competitors": 0, "sources": 0, "registry": 0, "watch": 0}
    ws = wb["Keywords"]
    h, names = head(ws)
    cols = lang_columns(names)
    have = existing_words(ws, h, cols)
    missing = sorted(set(cols) - {k for kw in pack["keywords"] for k in kw if len(k) == 2})
    tail = f"pack {pack['id']}" + (f" · translate {', '.join(m.upper() for m in missing)}" if missing else "")
    rows = [(kw["cluster"], {k: kw.get(k, "") for k in cols}, kw["priority"], kw.get("signal", ""))
            for kw in pack["keywords"]]
    if city and pack.get("city_keyword"):
        rows.append(("Place", {k: v.replace("{city}", city) for k, v in pack["city_keyword"].items() if k in cols},
                     "A", "Demand"))
    n = next_id(ws, pack["prefix"], h)
    for cluster, texts, prio, signal in rows:
        texts = {k: v for k, v in texts.items() if v}
        if not texts or any(norm(v) in have for v in texts.values()):
            continue
        ws.append(keyword_row(names, cols, f"{pack['prefix']}{n:02d}", cluster, texts, prio, signal, tail))
        have.update(norm(v) for v in texts.values())
        n, added["keywords"] = n + 1, added["keywords"] + 1
    c = next_id(ws, "CO", h)
    for name in [x.strip() for x in competitors if x and x.strip()]:
        if norm(name) in have:
            continue
        # the same name in every language column: news in any language can mention it
        ws.append(keyword_row(names, cols, f"CO{c:02d}", "Competitor", {k: name for k in cols}, "A",
                              "Competitor", "named at setup · INTERNAL"))
        have.add(norm(name))
        c += 1
        added["competitors"] += 1
        if "Players" in wb.sheetnames:
            wp = wb["Players"]
            ph = header_row(wp)
            if norm(name) not in {norm(r[0]) for r in wp.iter_rows(min_row=ph + 1, values_only=True) if r and r[0]}:
                wp.append([name, country, "", "Competitor", "named at setup", "", "", "competitor", "PUBLIC",
                           "watch the news"])

    if "Sources" in wb.sheetnames:
        wsrc = wb["Sources"]
        sh = header_row(wsrc)
        seen = {norm(r[2]) for r in wsrc.iter_rows(min_row=sh + 1, values_only=True) if r and len(r) > 2 and r[2]}
        for s in pack.get("sources", []):
            if country and s[1] not in (country, "EU", "EU/EEA", "All"):
                continue
            if norm(s[2]) not in seen:
                wsrc.append(list(s) + [""])
                seen.add(norm(s[2]))
                added["sources"] += 1

    if "Registry_queries" in wb.sheetnames and pack.get("registry_queries") and (not country or country == "LV"):
        wr = wb["Registry_queries"]
        rh = header_row(wr)
        rows_r = list(wr.iter_rows(min_row=rh + 1, values_only=True))
        seen = {norm(r[2]) for r in rows_r if r and r[2]}
        r = next_id(wr, "R", rh)
        for q in pack["registry_queries"]:
            if norm(q["words"]) in seen:
                continue
            wr.append([f"R{r:02d}", "LV", q["words"], q["goal"], q.get("exclude", ""), q.get("types", ""), "Yes"])
            r += 1
            added["registry"] += 1

    if "Watchlist" in wb.sheetnames:
        ww = wb["Watchlist"]
        wh = header_row(ww)
        seen = {norm(r[2]) for r in ww.iter_rows(min_row=wh + 1, values_only=True) if r and len(r) > 2 and r[2]}
        w = next_id(ww, "IP", wh)
        for row in pack.get("watch", []):
            if norm(row[1]) not in seen:
                ww.append([f"IP{w:02d}"] + list(row))
                w += 1
                added["watch"] += 1

    if "Run_log" in wb.sheetnames:
        wb["Run_log"].append([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "industry_pack",
                              f"pack {pack['id']} {pack.get('version', '')} applied ({today})",
                              0, ", ".join(f"{k} +{v}" for k, v in added.items())])
    return added


def words(wb, priority="A"):
    ws = wb["Keywords"]
    h, names = head(ws)
    cols = lang_columns(names)
    p = names.index("Priority") if "Priority" in names else None
    out = []
    for row in ws.iter_rows(min_row=h + 1, values_only=True):
        if not row or not row[0]:
            continue
        if p is not None and priority and str(row[p] or "").strip().upper() != priority:
            continue
        t = next((str(row[i]) for i in cols.values() if i < len(row) and row[i]), "")
        if t:
            out.append((str(row[0]), str(row[1] or ""), t))
    return out


def add_word(wb, text, cluster="Own"):
    """One own keyword in the first language column, priority A. Returns the new ID or '' if it is already there."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()[:80]
    if not text or text.startswith(("=", "+", "-", "@")):
        return ""
    ws = wb["Keywords"]
    h, names = head(ws)
    cols = lang_columns(names)
    if norm(text) in existing_words(ws, h, cols):
        return ""
    first = min(cols, key=cols.get)
    kid = f"OW{next_id(ws, 'OW', h):02d}"
    other = [l.upper() for l in cols if l != first]
    ws.append(keyword_row(names, cols, kid, cluster, {first: text}, "A", "",
                          "added by the company" + (f" · translate {', '.join(other)}" if other else "")))
    return kid


def switch_off(wb, text):
    """Priority → 'off' for the row with this keyword (any language). The row stays, so it can be switched back."""
    ws = wb["Keywords"]
    h, names = head(ws)
    cols = lang_columns(names)
    if "Priority" not in names:
        return ""
    p = names.index("Priority") + 1
    for r in range(h + 1, ws.max_row + 1):
        for i in cols.values():
            if norm(ws.cell(r, i + 1).value) == norm(text) and norm(text):
                ws.cell(r, p).value = OFF
                return str(ws.cell(r, 1).value or "")
    return ""


def main():
    ap = argparse.ArgumentParser(description="Industry packs: ready radar keywords and sources.")
    ap.add_argument("cmd", choices=["list", "show", "apply", "words", "add", "off"])
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--radar", default=RADAR)
    ap.add_argument("--country", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--competitor", action="append", default=[])
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if a.cmd == "list":
        for p in list_packs():
            print(f"{p['id']:14} {p['title'].get('en', '')} — {p.get('for', '')} ({len(p['keywords'])} keywords)")
        return 0
    if a.cmd == "show":
        p = load_pack(a.arg)
        print(f"{p['title'].get('en')} · {len(p['keywords'])} keywords · {len(p.get('sources', []))} sources")
        for k in p["keywords"]:
            print(f"  {k['priority']}  {k['cluster']:12} " + " | ".join(k.get(l, "") for l in ("lv", "ru", "en")))
        print("Wizard questions:\n  " + "\n  ".join(p.get("questions", [])))
        return 0
    try:
        import openpyxl
        import safe_xlsx  # noqa: F401 — outside text never becomes a formula
    except ImportError:
        sys.exit("Missing package: run  pip install openpyxl")
    if not os.path.exists(a.radar):
        sys.exit(f"No radar yet: {a.radar} — run scripts/radar_create.py first")
    wb = openpyxl.load_workbook(a.radar)
    if a.cmd == "words":
        for kid, cl, t in words(wb):
            print(f"{kid:6} {cl:12} {t}")
        return 0
    if a.cmd == "add":
        kid = add_word(wb, a.arg)
        print(f"✅ {kid}: {a.arg}" if kid else f"ℹ️ already in the radar or empty: {a.arg}")
    elif a.cmd == "off":
        kid = switch_off(wb, a.arg)
        print(f"✅ {kid} switched off: {a.arg}" if kid else f"ℹ️ not found: {a.arg}")
    else:
        added = apply(wb, load_pack(a.arg), a.country.upper(), a.city, a.competitor)
        print(("Would add: " if a.dry else "Added: ") + ", ".join(f"{k} {v}" for k, v in added.items()))
        if a.dry:
            return 0
    try:
        wb.save(a.radar)
    except PermissionError:
        sys.exit("❌ The radar file is open (Excel?) — close it and run again")
    return 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    sys.exit(main())
