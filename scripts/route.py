# -*- coding: utf-8 -*-
"""FLOKTRON · route.py — turns answers into the next tasks, using the "Routes" sheet of the base.

For every task that got an answer and was not routed yet:
    Done      → every matching "+" rule creates a new task for its "To ray"
    Not done  → matching "-" rule (or the "*" rule): the task is repeated (status of the old one = Moved);
                the second failure goes to the manager (ray L0) instead of a third try
New tasks get status New and go out with the next morning message. The old task is marked in column "Route".
collect_replies.py runs this automatically after reading replies.

Usage:
    python3 scripts/route.py           # process
    python3 scripts/route.py --dry     # show what would be created, change nothing
Options: --base <file>
"""
import argparse
import datetime
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")

C_ID, C_DATE, C_RAY, C_TASK, C_SRC, C_DUE, C_ST, C_REP, C_UPD, C_LETTER, C_ROUTE = range(11)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendar_days import next_working  # noqa: E402


def short(t, n=140):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def run(wb, dry=False, now=None, cfg=None):
    """Process the workbook in place. Returns a list of (new_id, to_ray, text)."""
    now = now or datetime.datetime.now()
    today = now.date()
    rules = [r for r in wb["Routes"].iter_rows(min_row=2, values_only=True)
             if r[0] and str(r[8]).strip().lower() in ("yes", "да", "jā")]
    wt = wb["Tasks"]
    if wt.cell(1, C_ROUTE + 1).value != "Route":
        wt.cell(1, C_ROUTE + 1, "Route")
    ids = {r[0] for r in wt.iter_rows(min_row=2, values_only=True)}

    def new_id():
        i = 1
        while f"R{today:%m%d}-{i}" in ids:
            i += 1
        ids.add(f"R{today:%m%d}-{i}")
        return f"R{today:%m%d}-{i}"

    created = []
    for row in list(wt.iter_rows(min_row=2, max_col=C_ROUTE + 1)):
        v = [c.value for c in row]
        tid, ray, text, src, st, rep, mark = v[C_ID], v[C_RAY], v[C_TASK], str(v[C_SRC] or ""), v[C_ST], v[C_REP], v[C_ROUTE]
        if not tid or mark:
            continue
        ev = "+" if st == "Done" else "-" if st in ("Not done", "Cannot") else None
        if not ev:
            continue
        answer = re.sub(r"^[+\-−]\s*", "", str(rep or ""))

        def matches(r):
            kws = [k.strip().lower() for k in str(r[3] or "").split(";") if k.strip()]
            return not kws or any(k in answer.lower() for k in kws)

        hits = [r for r in rules if r[2] in (ev, "−" if ev == "-" else ev) and r[1] == ray and matches(r)]
        if not hits and ev == "-":
            hits = [r for r in rules if r[1] == "*" and r[2] in ("-", "−")]
        out = []
        for r in hits:
            to = ray if r[4] == "=" else r[4]
            m = re.search(r"try (\d+)", src)
            attempt = int(m.group(1)) + 1 if m else 2
            if ev == "-" and attempt > 2:  # failed twice → manager decides
                to, txt, level, due = "L0", f"Decide: not done twice ({ray}) — {short(text)}. Answer: {short(answer) or '—'}", \
                    "Company", next_working(today, 1, cfg)
                source = f"Route {r[0]} → escalation ← {tid}"
            else:
                txt = str(r[5]).replace("{task}", short(text, 400)).replace("{report}", short(answer) or "no comment")
                level, due = r[7] or "Ray", next_working(today, int(r[6] or 1), cfg)
                source = f"Route {r[0]} ← {tid}" + (f" · try {attempt}" if ev == "-" else "")
            nid = new_id()
            out.append(f"{nid}→{to}")
            created.append((nid, to, txt))
            if not dry:
                wt.append([nid, due.isoformat(), to, txt, f"{source} · level {level}", due.isoformat(),
                           "New", None, None, None, None])
        if not dry:
            row[C_ROUTE].value = f"{now:%d.%m %H:%M}: " + (", ".join(out) if out else "no route")
            if ev == "-" and out:
                row[C_ST].value = "Moved"  # the old task stops going out; the new one replaces it
    return created


def main():
    ap = argparse.ArgumentParser(description="Turn answers into next tasks.")
    ap.add_argument("--base", default=os.path.join(ROOT, "data", "floktron_base.xlsx"))
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    a = ap.parse_args()
    cfg = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    now = datetime.datetime.now()
    wb = openpyxl.load_workbook(a.base)
    created = run(wb, a.dry, now, cfg)
    for nid, to, txt in created:
        print(f"{'(dry) ' if a.dry else ''}{nid} → {to}: {short(txt, 90)}")
    if a.dry:
        return
    if created:
        shutil.copy(a.base, a.base.replace(".xlsx", "_backup.xlsx"))
    wb["Run_log"].append([now.strftime("%Y-%m-%d %H:%M"), "route", f"new tasks: {len(created)}", "OK"])
    wb.save(a.base)
    print(f"new tasks: {len(created)}")


if __name__ == "__main__":
    main()
