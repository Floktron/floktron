# -*- coding: utf-8 -*-
"""FLOKTRON · registry_lv.py — new companies from the Latvian Register of Enterprises (open data) → radar.

Source: data.gov.lv dataset "uz" (register.csv, about 130 MB, updated daily, separator ";").
The file is read as a stream — nothing large is stored. Only companies registered in the period,
not terminated, of the types in Registry_queries, whose NAME matches the query words (by stem),
are written to the "Companies" sheet. Duplicates by reg. no. are skipped.
Goal "Competitor" rows also go to "Players" (internal). Nobody is contacted.

Usage:
    python3 scripts/registry_lv.py                    # period = since the last run (first run: 60 days)
    python3 scripts/registry_lv.py --days 30
    python3 scripts/registry_lv.py --csv register.csv # use a downloaded file instead of the internet
Options: --radar <file>
"""
import argparse
import codecs
import csv
import datetime
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from news_slice import header_row, matches  # noqa: E402

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")

CKAN = "https://data.gov.lv/dati/api/3/action/package_show?id=uz"
UA = {"User-Agent": "FLOKTRON registry reader"}


def csv_url():
    with urllib.request.urlopen(urllib.request.Request(CKAN, headers=UA), timeout=30) as r:
        res = json.load(r)["result"]["resources"]
    for x in res:
        if "register" in (x.get("url") or "").lower() and (x.get("format") or "").upper() == "CSV":
            return x["url"]
    raise RuntimeError("register.csv not found in the dataset")


def lines(source):
    if os.path.exists(source):
        with open(source, encoding="utf-8-sig", newline="") as f:
            yield from f
        return
    with urllib.request.urlopen(urllib.request.Request(source, headers=UA), timeout=120) as r:
        yield from codecs.iterdecode(r, "utf-8-sig")


def main():
    ap = argparse.ArgumentParser(description="New Latvian companies by name words → radar.")
    ap.add_argument("--radar", default=os.path.join(ROOT, "data", "floktron_radar.xlsx"))
    ap.add_argument("--csv", default="")
    ap.add_argument("--days", type=int, default=0)
    a = ap.parse_args()
    now = datetime.datetime.now()

    wb = openpyxl.load_workbook(a.radar)
    wq, wc, wl, wg = wb["Registry_queries"], wb["Companies"], wb["Run_log"], wb["Gaps"]
    queries = []
    for r in wq.iter_rows(min_row=header_row(wq) + 1, values_only=True):
        if r[0] and str(r[1] or "").upper() == "LV" and str(r[6] or "").lower() in ("yes", "jā", "да") and r[2]:
            queries.append({"id": r[0], "words": [w.strip() for w in str(r[2]).split(";") if w.strip()],
                            "goal": r[3] or "Client",
                            "exclude": [w.strip().lower() for w in str(r[4] or "").split(";") if w.strip()],
                            "types": {t.strip().upper() for t in str(r[5] or "SIA").split(";") if t.strip()}})
    if not queries:
        sys.exit("No active LV queries in the Registry_queries sheet — add words first.")

    if a.days:
        since = (now - datetime.timedelta(days=a.days)).date()
    else:
        last = [r[0] for r in wl.iter_rows(min_row=header_row(wl) + 1, values_only=True)
                if r[1] and str(r[1]).startswith("registry_lv")]
        since = (datetime.datetime.fromisoformat(str(last[-1])[:10]).date() if last
                 else (now - datetime.timedelta(days=60)).date())
    hc = header_row(wc)
    known = {str(r[2]) for r in wc.iter_rows(min_row=hc + 1, values_only=True) if r[2]}

    try:
        source = a.csv or csv_url()
        reader = csv.DictReader(lines(source), delimiter=";")
        total = found = 0
        for row in reader:
            reg = (row.get("registered") or "")[:10]
            if not reg or reg < since.isoformat() or (row.get("terminated") or "").strip():
                continue
            total += 1
            name = row.get("name") or ""
            low = name.lower()
            for q in queries:
                if (row.get("type") or "").upper() not in q["types"] or any(x in low for x in q["exclude"]):
                    continue
                hits = [w for w in q["words"] if matches(w, low)]
                if not hits or row.get("regcode") in known:
                    continue
                known.add(row.get("regcode"))
                found += 1
                wc.append([now.strftime("%Y-%m-%d"), "LV", row.get("regcode"), name, row.get("type"), reg,
                           row.get("address"), "; ".join(hits), q["goal"], q["id"], "", "PUBLIC", "New"])
                if q["goal"] == "Competitor":
                    wb["Players"].append([name, "LV", row.get("regcode"), "New registration — check",
                                          f"UR open data, registered {reg}", "", "", "", "ESTIMATE", "DD: website / product"])
                print(f"+ {row.get('regcode')} {name} ({reg}) — {q['goal']} [{', '.join(hits)}]")
                break
        wl.append([now.strftime("%Y-%m-%d %H:%M"), "registry_lv", f"period {since} – {now:%Y-%m-%d}, new LV companies {total}",
                   found, ""])
        print(f"period {since} – {now:%Y-%m-%d} · new LV companies: {total} · matched: {found}")
    except Exception as e:  # noqa: BLE001
        wg.append([now.strftime("%Y-%m-%d"), "New LV companies (UR open data)", "data.gov.lv register.csv",
                   f"error: {str(e)[:120]}", "source blocked", "Retry later or download the CSV by hand (--csv)", "New"])
        print("ERROR:", e, "— written to Gaps")
    wb.save(a.radar)


if __name__ == "__main__":
    main()
