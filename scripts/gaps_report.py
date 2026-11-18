# -*- coding: utf-8 -*-
"""FLOKTRON · gaps_report.py — weekly list of what FLOKTRON could not do, for the client and the support person.

Reads the "Gaps" sheet of the radar (and run errors from data/run.log): new gaps of the period, grouped by kind
(source blocked · needs subscription · function missing · client wish · data quality), with the proposed fix.
Saved to data/reports/<date>-gaps.html and sent to the manager. Sent gaps get status "Reported".

Usage:
    python3 scripts/gaps_report.py            # last 7 days, send
    python3 scripts/gaps_report.py --dry
"""
import argparse
import datetime
import html
import os
import re
import sys
from collections import defaultdict
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from news_slice import header_row  # noqa: E402

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")


def run_errors(since):
    """Runs that ended with an error (exit ≠ 0) in data/run.log."""
    p = os.path.join(ROOT, "data", "run.log")
    out, job = [], None
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as f:
        for ln in f:
            m = re.match(r"=== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) (\w+)", ln)
            if m:
                job = m.groups()
            m2 = re.match(r"--- exit (\d+)", ln)
            if m2 and job and m2.group(1) != "0" and job[0][:10] >= since.isoformat():
                out.append(job)
    return out


def main():
    ap = argparse.ArgumentParser(description="Weekly gaps report.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--radar", default=os.path.join(ROOT, "data", "floktron_radar.xlsx"))
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    cfg = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    mail = cfg.get("mail") or {}
    company = (cfg.get("company") or {}).get("name") or "FLOKTRON"
    now = datetime.datetime.now()
    since = (now - datetime.timedelta(days=a.days)).date()

    groups = defaultdict(list)
    rows = []
    if os.path.exists(a.radar):
        wb = openpyxl.load_workbook(a.radar)
        ws = wb["Gaps"]
        for r in ws.iter_rows(min_row=header_row(ws) + 1):
            v = [c.value for c in r]
            if v[0] and str(v[0])[:10] >= since.isoformat() and v[6] != "Reported":
                groups[v[4] or "other"].append(v)
                rows.append(r)
    errors = run_errors(since)

    li = lambda v: (f"<li><b>{html.escape(str(v[1]))}</b> — {html.escape(str(v[3]))}"
                    f"<br><small>source: {html.escape(str(v[2]))} · fix: {html.escape(str(v[5] or '—'))}</small></li>")
    parts = "".join(f"<h3>{html.escape(k)} ({len(v)})</h3><ul>{''.join(li(x) for x in v)}</ul>" for k, v in groups.items())
    err = "".join(f"<li>{d} · {j}</li>" for d, j in errors) or "<li>none</li>"
    body = f"""<div style="font-family:Arial;max-width:720px;color:#1A365D">
<div style="background:#1A365D;color:#fff;padding:12px 16px;border-radius:8px 8px 0 0"><b>{html.escape(company)} · FLOKTRON gaps</b><br>
<small>{since:%d.%m} – {now:%d.%m.%Y} · what FLOKTRON could not do and what to do about it</small></div>
<div style="background:#f3f3f3;padding:12px 16px">{parts or "<p>No gaps this week.</p>"}
<h3>Runs that ended with an error</h3><ul>{err}</ul></div></div>"""
    plain = f"{company} · FLOKTRON gaps {since:%d.%m}–{now:%d.%m.%Y}\n" + "\n".join(
        f"[{k}] {x[1]} — {x[3]} · fix: {x[5] or '—'}" for k, v in groups.items() for x in v) + \
        ("\nRun errors: " + ", ".join(f"{d} {j}" for d, j in errors) if errors else "")
    out = os.path.join(ROOT, "data", "reports")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{now:%Y-%m-%d}-gaps.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print(plain)
    print("saved:", path)
    to = mail.get("support_address") or mail.get("manager_address")
    if a.dry or not to or not (rows or errors):
        return
    from mail.send import MailError, Sender
    msg = EmailMessage()
    msg["From"], msg["To"] = mail.get("from") or mail.get("user"), to
    msg["Subject"] = f"[{company}] FLOKTRON gaps {now:%d.%m.%Y} — {len(rows)} new, {len(errors)} run errors"
    msg.set_content(plain)
    msg.add_alternative(body, subtype="html")
    try:
        with Sender(mail) as s:
            s.send(msg)
        if rows:
            for r in rows:
                r[6].value = "Reported"
            wb.save(a.radar)
        print("sent →", to)
    except MailError as e:
        print("MAIL ERROR:", e)


if __name__ == "__main__":
    main()
