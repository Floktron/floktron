# -*- coding: utf-8 -*-
"""FLOKTRON · weekly_summary.py — one page for the manager: what each ray did this week.

Per ray: tasks done · not done (with reasons) · still open · messages without any reply.
Plus: tasks open longer than 24 hours, and replies from unknown addresses.
Saved to data/reports/<date>-weekly.html and sent to the manager (mail.manager_address).

Usage:
    python3 scripts/weekly_summary.py            # last 7 days, send
    python3 scripts/weekly_summary.py --dry      # build only
Options: --days N  --config <file>  --base <file>
"""
import argparse
import datetime
import html
import os
import sys
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")

OPEN = ("New", "Sent", "Accepted", "Question", "Cannot")


def as_dt(v):
    if isinstance(v, datetime.datetime):
        return v
    if isinstance(v, datetime.date):
        return datetime.datetime.combine(v, datetime.time())
    try:
        return datetime.datetime.fromisoformat(str(v)[:16])
    except ValueError:
        return None


def build(wb, days, company, now):
    since = now - datetime.timedelta(days=days)
    rays = [r for r in wb["Rays"].iter_rows(min_row=2, values_only=True) if r[0]]
    tasks = [r for r in wb["Tasks"].iter_rows(min_row=2, values_only=True) if r[0]]
    receipts = list(wb["Receipts"].iter_rows(min_row=2, values_only=True))
    rows, stale, total = [], [], {"done": 0, "not": 0, "open": 0, "silent": 0}
    for ray in rays:
        rid, name = ray[0], ray[1]
        mine = [t for t in tasks if t[2] == rid and (as_dt(t[1]) or now) >= since]
        done = [t for t in mine if t[6] == "Done"]
        nd = [t for t in mine if t[6] in ("Not done", "Moved")]
        op = [t for t in mine if t[6] in OPEN]
        silent = [x for x in receipts if x[2] == rid and x[3] == "No reply" and (as_dt(x[0]) or now) >= since]
        if not (mine or silent):
            continue
        reasons = "; ".join(str(t[7] or "").lstrip("+- ")[:60] for t in nd if t[7])
        rows.append((rid, name, len(done), len(nd), len(op), len(silent), reasons))
        for k, v in (("done", done), ("not", nd), ("open", op), ("silent", silent)):
            total[k] += len(v)
        for t in op:
            upd = as_dt(t[8]) or as_dt(t[1])
            if upd and now - upd > datetime.timedelta(hours=24):
                stale.append((rid, t[0], t[3], t[6], upd))
    unknown = [x for x in receipts if str(x[3]).startswith("Unknown sender") and (as_dt(x[0]) or now) >= since]

    td = "padding:6px 8px;border-bottom:1px solid #ddd"
    table = "".join(
        f"<tr><td style='{td}'><b>{html.escape(str(n))}</b> <small>{r}</small></td><td style='{td};color:#4A9928'>{d}</td>"
        f"<td style='{td};color:#B00020'>{x}</td><td style='{td}'>{o}</td><td style='{td}'>{s}</td>"
        f"<td style='{td};font-size:12px'>{html.escape(why)}</td></tr>"
        for r, n, d, x, o, s, why in rows)
    stale_html = "".join(f"<li>{r} · {html.escape(str(t))} — {html.escape(str(txt))[:90]} ({st}, since {u:%d.%m %H:%M})</li>"
                         for r, t, txt, st, u in stale) or "<li>none</li>"
    unknown_html = "".join(f"<li>{html.escape(str(x[5]))} · {x[0]}</li>" for x in unknown) or "<li>none</li>"
    body = f"""<div style="font-family:Arial;max-width:720px;color:#1A365D">
<div style="background:#1A365D;color:#fff;padding:12px 16px;border-radius:8px 8px 0 0"><b>{html.escape(company)} · FLOKTRON weekly summary</b><br>
<small>{since:%d.%m} – {now:%d.%m.%Y}</small></div>
<div style="background:#f3f3f3;padding:12px 16px">
<p><b>Done {total['done']}</b> · not done {total['not']} · still open {total['open']} · messages without any reply {total['silent']}</p>
<table style="border-collapse:collapse;width:100%;background:#fff;font-size:14px">
<tr><th align=left style='{td}'>Ray</th><th style='{td}'>Done</th><th style='{td}'>Not done</th><th style='{td}'>Open</th>
<th style='{td}'>No reply</th><th align=left style='{td}'>Reasons</th></tr>{table}</table>
<p><b>Open longer than 24 hours</b></p><ul>{stale_html}</ul>
<p><b>Replies from unknown addresses (ignored)</b></p><ul>{unknown_html}</ul>
</div></div>"""
    plain = (f"{company} · FLOKTRON weekly summary {since:%d.%m}–{now:%d.%m.%Y}\n"
             f"Done {total['done']}, not done {total['not']}, open {total['open']}, no reply {total['silent']}\n\n" +
             "\n".join(f"{n} ({r}): done {d}, not done {x}, open {o}, no reply {s}" + (f" — {why}" if why else "")
                       for r, n, d, x, o, s, why in rows))
    return body, plain, total


def main():
    ap = argparse.ArgumentParser(description="FLOKTRON weekly summary for the manager.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--base", default=os.path.join(ROOT, "data", "floktron_base.xlsx"))
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
    wb = openpyxl.load_workbook(a.base)
    body, plain, total = build(wb, a.days, company, now)
    out = os.path.join(ROOT, "data", "reports")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{now:%Y-%m-%d}-weekly.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print(plain)
    print("saved:", path)
    to = mail.get("manager_address")
    if a.dry or not to:
        if not to:
            print("mail.manager_address is empty — summary not sent")
        return
    from mail.send import MailError, Sender
    msg = EmailMessage()
    msg["From"], msg["To"] = mail.get("from") or mail.get("user"), to
    msg["Subject"] = f"[{company}] FLOKTRON weekly summary {now:%d.%m.%Y} — done {total['done']}, open {total['open']}"
    msg.set_content(plain)
    msg.add_alternative(body, subtype="html")
    try:
        with Sender(mail) as s:
            s.send(msg)
        print("sent →", to)
    except MailError as e:
        print("MAIL ERROR:", e)


if __name__ == "__main__":
    main()
