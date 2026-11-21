# -*- coding: utf-8 -*-
"""FLOKTRON · content_check.py — every morning: posts of the day, missed posts, duplicate pictures.

0. Links from data/published_links.txt (pasted by a person, e.g. from the phone) → the matching post in
   "Plan" gets status Published and its link. "Published" is checked in this order: links file → plan →
   (AI agent only) the live profile, prompts/41_published_check.md. A post is never called missed
   before the links file has been read.
1. Published posts with a link → the picture is marked as used on that platform in "Media".
2. A planned post whose picture/video was ALREADY published on the same platform → status "Duplicate"
   (the same picture is never posted twice on one platform).
3. A post whose date has passed and that was not published:
   - status "Scheduled" (set in the platform's scheduler) → NOT moved: "waiting for a link"
     (the post probably went out; paste the link or let the agent find it on the profile);
   - "Ready"/"Draft" → moved to today (no day is skipped), the "Check" column says from which day;
   - already moved once and missed again → still today, but flagged "missed twice": a person decides
     (publish by hand or cancel) — no silent moving from day to day.
4. A short message with today's posts (text ready to copy) and what needs a person goes to
   content.notify (or the manager).

Usage:
    python3 scripts/content_check.py           # check, update, send
    python3 scripts/content_check.py --dry     # show only

Links file format (data/published_links.txt, created by content_create.py): one link per line under
"## NEW", optionally with a note ("personal profile", "20.11"). Matched lines move under "## DONE".
"""
import argparse
import datetime
import html
import os
import re
import sys
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
    from post_link import date_in_text, first_url, platform_of, time_of
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")

DATE, TIME, PLAT, LANG, RUB, HOOK, TEXT, FIRST, FILE, ALT, WHY, FIG, ST, LINK, CHECK = range(15)
OPEN = ("Ready", "Draft", "Scheduled", "Moved")
NEW_MARK, DONE_MARK = "## NEW", "## DONE"


def as_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def local(t):
    """UTC naive → local naive (the computer's time zone)."""
    return t.replace(tzinfo=datetime.timezone.utc).astimezone().replace(tzinfo=None) if t else None


def read_links(path):
    """(head, new_lines, done_lines) of the links file; missing file → nothing to do."""
    if not os.path.exists(path):
        return None
    head, new, done, part = [], [], [], 0
    with open(path, encoding="utf-8") as f:
        for line in f.read().splitlines():
            if line.strip().startswith(NEW_MARK):
                part = 1
            elif line.strip().startswith(DONE_MARK):
                part = 2
            [head, new, done][part].append(line)
    return head, new, done


def match_links(rows, path, today):
    """Paste-in links → Published. Returns (matched, unmatched, notes)."""
    got = read_links(path)
    if not got:
        return 0, 0, []
    head, new, done = got
    keep, notes, matched, unmatched = [], [], 0, 0
    for line in new:
        s = line.strip()
        if not s or s.startswith(NEW_MARK) or s.startswith("#"):
            keep.append(line)
            continue
        url = first_url(s)
        plat = platform_of(url or s)
        when = local(time_of(url)) if url else None
        day = when.date() if when else date_in_text(s, today.year)
        cands = []
        for r in rows:
            d = as_date(r[DATE].value)
            if r[PLAT].value != plat or r[ST].value not in OPEN or r[LINK].value:
                continue
            gap = abs((d - day).days) if (d and day) else (abs((d - today).days) if d else 99)
            if day and gap > 1:
                continue
            cands.append((gap, str(r[DATE].value or ""), str(r[TIME].value or ""), r))
        if not plat or not cands:
            keep.append(line + ("" if "← no matching post" in line else "   ← no matching post: check platform and date"))
            notes.append(f"link not matched: {s[:90]}")
            unmatched += 1
            continue
        cands.sort(key=lambda c: c[:3])
        r = cands[0][3]
        r[ST].value, r[LINK].value = "Published", url or s
        r[CHECK].value = "link from published_links.txt" + (f" · out {when:%d.%m %H:%M}" if when else "")
        if len(cands) > 1 and cands[0][0] == cands[1][0]:
            notes.append(f"matched {url or s} → {r[DATE].value} {r[PLAT].value} «{str(r[HOOK].value or r[TEXT].value or '')[:40]}» — please check")
        done.append(f"{s} — matched to {r[DATE].value} {r[PLAT].value} ({today:%d.%m})")
        matched += 1
    if matched or len(keep) != len(new):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(head + keep + done) + "\n")
    return matched, unmatched, notes


def main():
    ap = argparse.ArgumentParser(description="FLOKTRON morning content check.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--content", default=os.path.join(ROOT, "data", "floktron_content.xlsx"))
    ap.add_argument("--links", default=None, help="links file (default: content.links_file or data/published_links.txt)")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    cfg = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    mail = cfg.get("mail") or {}
    if not a.links:
        lf = (cfg.get("content") or {}).get("links_file") or "data/published_links.txt"
        a.links = lf if os.path.isabs(lf) else os.path.join(ROOT, lf)
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
    todays, waiting, twice = [], [], []
    rows = [r for r in plan.iter_rows(min_row=2, max_col=15) if r[PLAT].value]
    linked, unmatched, notes = (0, 0, []) if a.dry else match_links(rows, a.links, today)   # 0. pasted links
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
        if st not in OPEN:
            continue
        if f and (f, p) in used:                                      # 2. never the same picture twice
            r[ST].value, r[CHECK].value = "Duplicate", f"ALREADY ON {p}: {used[(f, p)]}"
            dup += 1
            continue
        if d and d < today and st == "Scheduled":                     # 3a. scheduled → probably out, ask for link
            r[CHECK].value = f"scheduled {d:%d.%m} {v[TIME] or ''} — waiting for a link".replace("  ", " ")
            waiting.append(v[:])
            continue
        if d and d < today:                                           # 3. missed → today
            before = str(v[CHECK] or "")
            if before.startswith("moved from") or before.startswith("MISSED TWICE"):
                m = re.search(r"\d{2}\.\d{2}", before)
                first = m.group(0) if m else f"{d:%d.%m}"
                r[CHECK].value = f"MISSED TWICE (first {first}, then {d:%d.%m}) — publish by hand or cancel"
                twice.append(v[:])
            else:
                r[CHECK].value = f"moved from {d:%d.%m}"
            r[DATE].value = today.isoformat()
            moved += 1
            d = today
        if d == today:
            todays.append(v[:])

    todays.sort(key=lambda x: str(x[TIME] or ""))
    plain = f"{company} · posts today {today:%d.%m.%Y}: {len(todays)}\n\n" + "\n\n".join(
        f"{x[TIME] or ''} · {x[PLAT]} · {x[LANG] or ''} · {x[RUB] or ''}\n{x[TEXT] or ''}\n"
        f"Picture: {x[FILE] or '—'}" + (f"\nFirst comment: {x[FIRST]}" if x[FIRST] else "") for x in todays)
    attention = ([f"waiting for a link: {x[DATE]} {x[TIME] or ''} · {x[PLAT]} · {str(x[HOOK] or x[TEXT] or '')[:50]} "
                  f"— paste the link into data/published_links.txt" for x in waiting]
                 + [f"missed twice: {x[PLAT]} · {str(x[HOOK] or x[TEXT] or '')[:50]} — publish by hand today or cancel"
                    for x in twice] + notes)
    if attention:
        plain += "\n\nNeeds you:\n" + "\n".join("• " + t for t in attention)
    print(plain)
    print(f"\nlinks from file: {linked} · marked as used: {marked} · duplicates stopped: {dup} · "
          f"missed → today: {moved} · waiting for a link: {len(waiting)} · missed twice: {len(twice)}")
    if a.dry:
        return
    wb["Run_log"].append([now.strftime("%Y-%m-%d %H:%M"), "content_check",
                          f"today {len(todays)}, links {linked}, duplicates {dup}, moved {moved}, marked {marked}, "
                          f"waiting {len(waiting)}, twice {len(twice)}", f"unmatched links {unmatched}" if unmatched else ""])
    wb.save(a.content)
    to = (cfg.get("content") or {}).get("notify") or mail.get("manager_address")
    if not (to and (todays or attention)):
        return
    from mail.send import MailError, Sender
    items = "".join(
        f"<div style='background:#fff;padding:10px;margin:8px 0;border-radius:6px'><b>{html.escape(str(x[TIME] or ''))} · "
        f"{html.escape(str(x[PLAT]))} · {html.escape(str(x[LANG] or ''))}</b><br><pre style='white-space:pre-wrap;"
        f"font-family:Arial'>{html.escape(str(x[TEXT] or ''))}</pre><small>Picture: {html.escape(str(x[FILE] or '—'))}"
        f"</small></div>" for x in todays)
    msg = EmailMessage()
    msg["From"], msg["To"] = mail.get("from") or mail.get("user"), to
    need = "".join(f"<li>{html.escape(t)}</li>" for t in attention)
    if need:
        items += f"<div style='background:#fff;padding:10px;margin:8px 0;border-radius:6px'><b>Needs you</b><ul>{need}</ul></div>"
    msg["Subject"] = f"[{company}] posts today {today:%d.%m}: {len(todays)}" + (f" · needs you: {len(attention)}" if attention else "")
    msg.set_content(plain)
    msg.add_alternative(f"<div style='font-family:Arial;max-width:640px;background:#f3f3f3;padding:12px'>{items}"
                        f"<p style='font-size:12px;color:#717171'>After publishing paste the post link into "
                        f"data/published_links.txt (one line, from the phone is fine) — or put status Published and the "
                        f"link in the plan. Scheduled in the platform? Status Scheduled. FLOKTRON then never calls it "
                        f"missed and never repeats that picture on that platform.</p></div>", subtype="html")
    try:
        with Sender(mail) as s:
            s.send(msg)
        print("sent →", to)
    except MailError as e:
        print("MAIL ERROR:", e)


if __name__ == "__main__":
    main()
