# -*- coding: utf-8 -*-
"""FLOKTRON · content_check.py — every morning: posts of the day, missed posts, duplicate pictures.

1. Published posts with a link → the picture is marked as used on that platform in "Media".
2. A planned post whose picture/video was ALREADY published on the same platform → status "Duplicate"
   (the same picture is never posted twice on one platform).
3. A post whose date has passed and that was not published → moved to today (no day is skipped),
   the "Check" column says from which day.
4. A short message with today's posts (text ready to copy) goes to content.notify (or the manager).

Usage:
    python3 scripts/content_check.py           # check, update, send
    python3 scripts/content_check.py --dry     # show only
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

DATE, TIME, PLAT, LANG, RUB, HOOK, TEXT, FIRST, FILE, ALT, WHY, FIG, ST, LINK, CHECK = range(15)


def as_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description="FLOKTRON morning content check.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--content", default=os.path.join(ROOT, "data", "floktron_content.xlsx"))
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
    today = now.date()
    if not os.path.exists(a.content):
        sys.exit(f"No content plan at {a.content} — run scripts/content_create.py first.")

    wb = openpyxl.load_workbook(a.content)
    plan, media = wb["Plan"], wb["Media"]
    plats = [c.value for c in media[1]][2:]
    used = {}  # (file, platform) → "dd.mm link"
    rows_by_file = {}
    for r in media.iter_rows(min_row=2):
        if r[0].value:
            rows_by_file[str(r[0].value)] = r
            for i, p in enumerate(plats):
                if r[2 + i].value:
                    used[(str(r[0].value), p)] = str(r[2 + i].value)

    marked = dup = moved = 0
    todays = []
    rows = [r for r in plan.iter_rows(min_row=2, max_col=15) if r[PLAT].value]
    for r in rows:                                                    # 1. remember what was published
        v = [c.value for c in r]
        f, p, d = str(v[FILE] or "").strip(), v[PLAT], as_date(v[DATE])
        if v[ST] == "Published" and f and (f, p) not in used:
            stamp = (f"{d:%d.%m.%Y} " if d else "") + str(v[LINK] or "")
            mr = rows_by_file.get(f)
            if mr is None:
                media.append([f, ""] + [""] * len(plats))
                mr = media[media.max_row]
                rows_by_file[f] = mr
            if p in plats:
                mr[2 + plats.index(p)].value = stamp.strip()
            used[(f, p)] = stamp.strip()
            marked += 1
    for r in rows:
        v = [c.value for c in r]
        f, p, st, d = str(v[FILE] or "").strip(), v[PLAT], v[ST], as_date(v[DATE])
        if st not in ("Ready", "Draft"):
            continue
        if f and (f, p) in used:                                      # 2. never the same picture twice
            r[ST].value, r[CHECK].value = "Duplicate", f"ALREADY ON {p}: {used[(f, p)]}"
            dup += 1
            continue
        if d and d < today:                                           # 3. missed → today
            r[DATE].value, r[CHECK].value = today.isoformat(), f"moved from {d:%d.%m}"
            moved += 1
            d = today
        if d == today:
            todays.append(v[:])

    todays.sort(key=lambda x: str(x[TIME] or ""))
    plain = f"{company} · posts today {today:%d.%m.%Y}: {len(todays)}\n\n" + "\n\n".join(
        f"{x[TIME] or ''} · {x[PLAT]} · {x[LANG] or ''} · {x[RUB] or ''}\n{x[TEXT] or ''}\n"
        f"Picture: {x[FILE] or '—'}" + (f"\nFirst comment: {x[FIRST]}" if x[FIRST] else "") for x in todays)
    print(plain)
    print(f"\nmarked as used: {marked} · duplicates stopped: {dup} · missed → today: {moved}")
    if a.dry:
        return
    wb["Run_log"].append([now.strftime("%Y-%m-%d %H:%M"), "content_check",
                          f"today {len(todays)}, duplicates {dup}, moved {moved}, marked {marked}", ""])
    wb.save(a.content)
    to = (cfg.get("content") or {}).get("notify") or mail.get("manager_address")
    if not (to and todays):
        return
    from mail.send import MailError, Sender
    items = "".join(
        f"<div style='background:#fff;padding:10px;margin:8px 0;border-radius:6px'><b>{html.escape(str(x[TIME] or ''))} · "
        f"{html.escape(str(x[PLAT]))} · {html.escape(str(x[LANG] or ''))}</b><br><pre style='white-space:pre-wrap;"
        f"font-family:Arial'>{html.escape(str(x[TEXT] or ''))}</pre><small>Picture: {html.escape(str(x[FILE] or '—'))}"
        f"</small></div>" for x in todays)
    msg = EmailMessage()
    msg["From"], msg["To"] = mail.get("from") or mail.get("user"), to
    msg["Subject"] = f"[{company}] posts today {today:%d.%m}: {len(todays)}"
    msg.set_content(plain)
    msg.add_alternative(f"<div style='font-family:Arial;max-width:640px;background:#f3f3f3;padding:12px'>{items}"
                        f"<p style='font-size:12px;color:#717171'>After publishing put status Published and the link "
                        f"in the plan — FLOKTRON then never repeats that picture on that platform.</p></div>", subtype="html")
    try:
        with Sender(mail) as s:
            s.send(msg)
        print("sent →", to)
    except MailError as e:
        print("MAIL ERROR:", e)


if __name__ == "__main__":
    main()
