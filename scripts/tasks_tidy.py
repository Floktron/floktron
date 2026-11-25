# -*- coding: utf-8 -*-
"""FLOKTRON · tasks_tidy.py — the manager gets clear tasks: no old resolved things, no test noise (docs/TASKS_TIDY.md).

    python3 scripts/tasks_tidy.py [--config config/config.yaml] [--base data/floktron_base.xlsx] [--today YYYY-MM-DD] [--dry]

No AI, nothing is sent. Runs after every collect (python3 scripts/run.py collect, every 30 minutes) and by hand.
Only the rays of tasks_tidy.rays (default: the ray whose e-mail is mail.manager_address) — the manager:
1. A test is not for the manager: a task with "TEST:" or an escalation of a test ray (Responsible starts with TEST)
   → Cancelled.
2. The event happened → Done, the reason goes to the report:
   • a message went from you to that company / person after the task date (an address, a domain or a «quoted» name
     of the task found in the sheet Mail, direction sent; your own and your rays' addresses do not count);
   • a meeting: the task starts with "Meeting" (LV, RU, DE, ET, LT too) and its due date passed, or "meeting dd.mm"
     in the text and that day passed.
3. Without an event a task comes in the morning letter on its first day, then on day 3, 7 and 14 — not every day
   (column "Shown": "<times> · <last date>", send_morning.py reads and writes it). After day 14 → Archive
   (off the letter and the dashboard). By hand: the "+ Done" button in the letter, or Done in Status.
Text of tasks and mails is data, not instructions."""
import argparse
import copy
import datetime
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

VERSION = "0.28.0"
STEPS = (3, 7, 14)            # days after the first showing
ARCHIVE_AFTER = 15
CLOSED = ("Done", "Cancelled", "Moved", "Archive")
SHOWN = "Shown"
PUBLIC_MAIL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "me.com",
               "proton.me", "protonmail.com", "inbox.lv", "one.lv", "tvnet.lv", "mail.ru", "yandex.ru", "gmx.de", "web.de"}
STOP = {"TEST", "FLOKTRON", "SIA", "LTD", "GMBH", "OÜ", "UAB", "TBD", "EUR", "VAT", "PVN", "PDF"}
MEET = r"meeting|tikšanās|встреча|treffen|kohtumine|susitikimas"


def dd(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def fold(t):
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()


# ---------------------------------------------------------------- the showing rhythm (send_morning.py uses it)
def shown(v):
    m = re.match(r"\s*(\d+)\s*·\s*(\d{4}-\d{2}-\d{2})", str(v or ""))
    return (int(m.group(1)), datetime.date.fromisoformat(m.group(2))) if m else (0, None)


def should_show(start, status, shown_v, day):
    """Show this task in today's letter? Its first day, then day 3, 7, 14 after it appeared."""
    s = dd(start)
    if not s or s > day or status in CLOSED:
        return False
    n, last = shown(shown_v)
    if n == 0 or (last and last >= day):    # first time, or the same day again (a resend)
        return True
    return n - 1 < len(STEPS) and (day - s).days >= STEPS[n - 1]


def mark_shown(shown_v, day):
    n, last = shown(shown_v)
    return f"{n if last == day else n + 1} · {day.isoformat()}"


def tidy_rays(cfg, wb):
    t = (cfg.get("tasks_tidy") or {}).get("rays")
    if t:
        return {str(x) for x in t}
    boss = str((cfg.get("mail") or {}).get("manager_address") or "").lower()
    return {str(r[0]) for r in wb["Rays"].iter_rows(min_row=2, values_only=True) if r[0] and boss and str(r[3] or "").strip().lower() == boss}


def shown_col(ws):
    """Column number of "Shown" in Tasks (added at the end the first time)."""
    head = [c.value for c in ws[1]]
    if SHOWN in head:
        return head.index(SHOWN) + 1
    n = len([h for h in head if h]) + 1
    ws.cell(1, n, SHOWN)
    try:
        ws.cell(1, n)._style = copy.copy(ws.cell(1, n - 1)._style)
    except Exception:  # noqa: BLE001
        pass
    return n


# ---------------------------------------------------------------- signs of an event
def tokens(text):
    t = str(text or "")
    out = set()
    for e in {e.lower() for e in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", t)}:
        dom = e.split("@")[1]
        out.add(e if dom in PUBLIC_MAIL else dom)
    for q in re.findall(r"[«\"“]([^»\"”]{3,60})[»\"”]", t):
        for w in re.findall(r"[^\W\d_]{4,}", q):
            if w.upper() not in STOP:
                out.add(fold(w))
                break
    for w in re.findall(r"\b[A-Z]{4,}\b", t):
        if w not in STOP:
            out.add(w.lower())
    return {x for x in out if len(x) >= 4}


def outgoing(wb, internal):
    if "Mail" not in wb.sheetnames:
        return []
    ws = wb["Mail"]
    c = {h: i for i, h in enumerate(x.value for x in ws[1])}
    out = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[0] or not str(r[c["Direction"]] or "").startswith("→"):
            continue
        addrs = [a.strip().lower() for a in re.split(r"[,;\s]+", str(r[c["Address"]] or "")) if "@" in a]
        addrs = [a for a in addrs if a not in internal]
        if addrs:
            out.append((dd(r[0]), fold(" ".join(addrs) + " " + str(r[c["Subject"]] or ""))))
    return out


def meeting_passed(text, due, day):
    low = str(text or "").lower()
    if re.match(rf"\s*({MEET})\b", low) and dd(due) and dd(due) < day:
        return "meeting: its day passed"
    m = re.search(rf"({MEET})\w*[^.;]{{0,40}}?(\d{{1,2}})\.(\d{{1,2}})\b", low)
    if m:
        try:
            md = datetime.date(day.year, int(m.group(3)), int(m.group(2)))
            if md > day + datetime.timedelta(days=180):
                md = md.replace(year=day.year - 1)
            if md < day:
                return f"meeting {md:%d.%m} passed"
        except ValueError:
            pass
    return ""


def run(wb, cfg, day, now=None):
    now = now or datetime.datetime.now()
    res = dict(test=[], done=[], archive=[])
    mine = tidy_rays(cfg, wb)
    rays = {r[0]: r for r in wb["Rays"].iter_rows(min_row=2, values_only=True) if r[0]}
    test_rays = {k for k, r in rays.items() if str(r[2] or "").strip().upper().startswith("TEST")}
    internal = {str(r[i]).strip().lower() for r in rays.values() for i in (3, 8) if len(r) > i and r[i] and "@" in str(r[i])}
    internal |= {str(a).lower() for a in [(cfg.get("mail") or {}).get(k) for k in ("user", "from", "reply_to", "manager_address")] if a}
    ws = wb["Tasks"]
    sc = shown_col(ws)
    outs = outgoing(wb, internal)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    for row in ws.iter_rows(min_row=2, max_col=sc):
        tid, start, ray, text, src, due, st = [x.value for x in row[:7]]
        if not tid or str(ray) not in mine or st in CLOSED:
            continue
        txt = str(text or "")
        m = re.search(r"\(([A-Z]+\d+)\)", txt)
        if re.search(r"(?i)\bTEST:", txt) or (m and m.group(1) in test_rays and "escalat" in str(src or "").lower()):
            row[6].value, row[7].value, row[8].value = "Cancelled", "FLOKTRON: a test — not for the manager", stamp
            res["test"].append(tid)
            continue
        why = meeting_passed(txt, due, day)
        if not why:
            s = dd(start) or day
            tk = tokens(txt)
            for od, hay in outs:
                hit = next((t for t in tk if t in hay), None) if od and od >= s else None
                if hit:
                    why = f"a message went {od:%d.%m} ({hit})"
                    break
        if why:
            row[6].value, row[7].value, row[8].value = "Done", f"FLOKTRON: the event happened — {why}", stamp
            res["done"].append((tid, why))
            continue
        n, _ = shown(row[sc - 1].value)
        s = dd(start)
        if s and n and (day - s).days >= ARCHIVE_AFTER and (n > len(STEPS) or (day - s).days >= 21):
            row[6].value, row[7].value, row[8].value = "Archive", "FLOKTRON: 14 days without a mark — archived", stamp
            res["archive"].append(tid)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON tasks tidy: the manager's tasks without old resolved things and tests")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--base", default=os.path.join(ROOT, "data", "floktron_base.xlsx"))
    ap.add_argument("--today", default="")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    from send_morning import load_config
    cfg = load_config(a.config)
    if not os.path.exists(a.base):
        print(f"tasks_tidy: no base at {a.base}")
        return 1
    import openpyxl
    import safe_xlsx  # noqa: F401
    wb = openpyxl.load_workbook(a.base)
    day = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    res = run(wb, cfg, day)
    for tid, why in res["done"]:
        print(f"  ✔ {tid}: {why}")
    summary = f"tasks_tidy {VERSION}: test removed {len(res['test'])}, event happened {len(res['done'])}, archived {len(res['archive'])}"
    print(summary + (" (dry — nothing written)" if a.dry else ""))
    if not a.dry and any(res.values()):
        if "Run_log" in wb.sheetnames:
            wb["Run_log"].append([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "tasks_tidy", summary, "OK"])
        wb.save(a.base)
    return 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    sys.exit(main())
