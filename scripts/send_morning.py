# -*- coding: utf-8 -*-
"""FLOKTRON · send_morning.py — builds and sends the morning message to every active ray.

Every task gets its own "+ Done" / "− Did not work out" buttons. A button opens a ready reply:
subject  FLOKTRON#<message-id> T:<task-id> + · <short task name>
body     the task line on top, the answer goes at the very end after ✍️
The reply collector (collect_replies.py, next step) reads these subjects.

Usage:
    python3 scripts/send_morning.py --dry               # build only, save copies, send nothing
    python3 scripts/send_morning.py                     # send to all active rays
    python3 scripts/send_morning.py --only L1,L3        # some rays only
    python3 scripts/send_morning.py --test me@mail.com  # send to a test address, base is not changed
Options: --config <file>  --base <file>
The manager's ray (tasks_tidy.rays, default: the ray with mail.manager_address) gets a task on its first day and then
on day 3, 7 and 14 only, not every morning (column "Shown", scripts/tasks_tidy.py) — no old resolved things.
"""
import argparse
import datetime
import html
import os
import re
import sys
import time
from email.message import EmailMessage
from email.utils import make_msgid
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")
from i18n import texts  # noqa: E402
from calendar_days import is_working  # noqa: E402

DONE = {"Done", "Cancelled", "Moved", "Archive"}
NL = "\r\n"  # mobile mail apps keep line breaks better with CRLF
DEFAULT_COLORS = {"main": "#1A365D", "ok": "#4A9928", "neutral": "#717171", "background": "#f3f3f3"}


def load_config(path):
    if not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def as_date(v, default):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return default


def short(t, n=60):
    return re.sub(r"\s+", " ", str(t)).strip()[:n]


def button(label, color, to, subject, body, small=False):
    href = "mailto:%s?subject=%s&body=%s" % (to, quote(subject), quote(body))
    pad, size = ("6px 12px", "13px") if small else ("10px 16px", "14px")
    return (f'<a href="{href}" style="display:inline-block;padding:{pad};margin:6px 6px 0 0;'
            f'background:{color};color:#fff;text-decoration:none;border-radius:6px;font-weight:bold;'
            f'font-size:{size};font-family:Arial">{html.escape(label)}</a>')


def build_message(company, ray_name, owner, lang, lid, rows, reply_to, today, test=False, marker="FLOKTRON#", colors=None,
                  evening=False, agenda=None, due_file=False):
    L = dict(texts(lang))
    if evening:  # same buttons, evening words
        L["hello"], L["subject"] = L["e_hello"], L["e_subject"]
    col = dict(DEFAULT_COLORS, **(colors or {}))
    C_BLUE, C_GREEN, C_GREY, C_LIGHT = col["main"], col["ok"], col["neutral"], col["background"]
    M = marker
    tag = " TEST" if test else ""
    ctx_all = L["ctx_all"] + " " + "; ".join(f"{i+1}. {short(r['task'])}" for i, r in enumerate(rows)) + NL + NL
    items = ""
    for i, r in enumerate(rows):
        head = f"{L['ctx']} {i+1}: {short(r['task'], 220)}" + NL + NL
        items += (
            "<tr><td style='padding:8px 10px;border-bottom:1px solid #ddd;color:%s;vertical-align:top'>%d</td>"
            "<td style='padding:8px 10px;border-bottom:1px solid #ddd'>%s<br><small style='color:%s'>%s %s</small><br>%s%s</td></tr>"
            % (C_GREY, i + 1, html.escape(str(r["task"])), C_GREY, L["due"], r["due"].strftime("%d.%m"),
               button(L["plus"], C_GREEN, reply_to, f"{M}{lid}{tag} T:{r['id']} + · {short(r['task'], 40)}",
                      head + L["plus_body"], small=True),
               button(L["minus"], C_GREY, reply_to, f"{M}{lid}{tag} T:{r['id']} - · {short(r['task'], 40)}",
                      head + L["minus_body"], small=True)))
    confirm = (button(L["ok"], C_GREEN, reply_to, f"{M}{lid}{tag} OK", ctx_all + L["ok_body"])
               + button(L["q"], C_BLUE, reply_to, f"{M}{lid}{tag} Q", ctx_all + L["q_body"])
               + button(L["no"], C_GREY, reply_to, f"{M}{lid}{tag} NO", ctx_all + L["no_body"]))
    confirm_block = "" if evening else "<p style='margin-top:14px'><b>%s</b><br>%s</p>" % (L["confirm"], confirm)
    evening_title = "" if evening else L["evening"]
    cal_block = ""
    if agenda:
        cal_block = ("<p style='margin:0 0 10px 0'><b>%s</b><br>%s</p>"
                     % (html.escape(L["cal_title"]), "<br>".join(html.escape(x) for x in agenda)))
    due_note = f"<p style='font-size:13px'>📅 {html.escape(L['cal_file'])}</p>" if due_file else ""
    body = f"""<div style="font-family:Arial;max-width:640px;color:{C_BLUE}">
<div style="background:{C_BLUE};color:#fff;padding:12px 16px;border-radius:8px 8px 0 0"><b>{html.escape(company)} · {html.escape(ray_name)}</b><br><small>{today:%d.%m.%Y} · {L['letter']} {lid}</small></div>
<div style="background:{C_LIGHT};padding:12px 16px"><p>{html.escape(L['hello'].format(o=owner or ''))}</p>
{cal_block}<table style="border-collapse:collapse;width:100%;background:#fff">{items}</table>
{confirm_block}{due_note}
<p><b>{evening_title}</b><br><span style="font-size:13px">{html.escape(L['task_note'])}</span></p>
<p style="color:{C_GREY};font-size:12px">{html.escape(L['note'])}</p></div></div>"""
    cal_plain = f"{L['cal_title']} " + "; ".join(agenda) + "\n" if agenda else ""
    plain = f"{company} · {ray_name} · {today:%d.%m.%Y}\n" + cal_plain + "\n".join(
        f"{i+1}. {r['task']}" for i, r in enumerate(rows))
    subject = (("[TEST] " if test else "") + L["subject"].format(c=company, n=ray_name, d=f"{today:%d.%m}", k=len(rows))
               + f" · {M}{lid}{tag}")
    return subject, body, plain


def main():
    ap = argparse.ArgumentParser(description="Send FLOKTRON morning messages.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--base", default=os.path.join(ROOT, "data", "floktron_base.xlsx"))
    ap.add_argument("--dry", action="store_true", help="build only, send nothing")
    ap.add_argument("--only", default="", help="comma-separated ray IDs")
    ap.add_argument("--test", default="", help="send to this address; the base is not changed")
    ap.add_argument("--evening", action="store_true", help="evening reminder: today's tasks still open")
    ap.add_argument("--force", action="store_true", help="send even on a weekend or holiday")
    a = ap.parse_args()

    cfg = load_config(a.config)
    company = (cfg.get("company") or {}).get("name") or "FLOKTRON"
    mail = cfg.get("mail") or {}
    reply_to = mail.get("reply_to") or mail.get("user") or ""
    sender_addr = mail.get("from") or mail.get("user") or ""
    if not reply_to and not a.dry:
        sys.exit("Set mail.reply_to (or mail.user) in config.yaml — replies come back there.")
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    now = datetime.datetime.now()
    today = now.date()
    if not (a.force or a.test or is_working(today, cfg)):
        print(f"{today}: weekend or public holiday — no messages (use --force to send anyway)")
        return

    if not os.path.exists(a.base):
        sys.exit(f"No base at {a.base} — run scripts/base_create.py first.")
    wb = openpyxl.load_workbook(a.base)
    rays = [r for r in wb["Rays"].iter_rows(min_row=2, values_only=True)
            if r[0] and str(r[6]).strip().lower() in ("yes", "да", "jā")]
    import tasks_tidy
    tidy = tasks_tidy.tidy_rays(cfg, wb)
    sc = tasks_tidy.shown_col(wb["Tasks"]) if tidy else 0
    tasks = {}
    for row in wb["Tasks"].iter_rows(min_row=2, max_col=max(10, sc)):
        tid, dt, ray, text, _src, due, st = [c.value for c in row[:7]]
        if not (tid and text):
            continue
        if a.evening:
            if as_date(dt, today) == today and st in ("Sent", "Accepted", "Question") and str(ray) not in tidy:
                tasks.setdefault(ray, []).append(row)
        elif str(ray) in tidy:   # the manager: first day, then day 3, 7, 14
            if tasks_tidy.should_show(dt, st, row[sc - 1].value, today):
                tasks.setdefault(ray, []).append(row)
        elif as_date(dt, today) <= today and st not in DONE:
            tasks.setdefault(ray, []).append(row)

    cal = cfg.get("calendar") or {}
    cal_rays = {str(x) for x in (cal.get("rays") or [])}
    agenda_lines = []
    if cal.get("enabled") and cal_rays and not a.evening:
        try:
            from calendar_read import agenda
            agenda_lines = agenda(cfg, today)
            print(f"calendar: {len(agenda_lines)} events today")
        except Exception as e:  # noqa: BLE001 — a calendar problem never stops the letters
            print(f"calendar: not read — {str(e)[:120]} (letters go without it)")
    attach_due = bool(cal.get("enabled") and cal.get("attach_due", True)) and not a.evening

    outdir = os.path.join(ROOT, "data", "letters", today.isoformat())
    os.makedirs(outdir, exist_ok=True)
    jobs = []
    for rid, name, owner, email, lang, *_ in rays:
        if only and rid not in only:
            continue
        rows = tasks.get(rid, [])
        if not rows:
            print(f"{rid}: {'nothing open this evening' if a.evening else 'no tasks today'} — no message")
            continue
        lid = f"{today:%Y%m%d}-{rid}"
        data = [{"id": r[0].value, "task": r[3].value, "due": as_date(r[5].value, today)} for r in rows]
        due_ics = ""
        if attach_due:
            import ics
            due_ics = ics.make_calendar([ics.event(f"{short(d['task'], 80)} · {name}", d["due"],
                                                   uid=f"{d['id']}-{d['due']:%Y%m%d}@floktron")
                                         for d in data], name=f"{company} · {name}")
        subject, body, plain = build_message(company, name, owner, lang, lid, data, reply_to, today, bool(a.test),
                                             mail.get("marker") or "FLOKTRON#", cfg.get("colors"), a.evening,
                                             agenda_lines if rid in cal_rays else None, bool(due_ics))
        fname = f"{lid}{'-evening' if a.evening else ''}{'-TEST' if a.test else ''}.html"
        with open(os.path.join(outdir, fname), "w", encoding="utf-8") as f:
            f.write(body)
        if due_ics:
            with open(os.path.join(outdir, fname[:-5] + ".ics"), "w", encoding="utf-8", newline="") as f:
                f.write(due_ics)
        jobs.append((rid, a.test or email, subject, body, plain, rows, lid, due_ics))
        print(f"{rid}: built → data/letters/{today}/{fname} ({len(rows)} tasks)")

    sent = 0
    if not a.dry and jobs:
        from mail.send import MailError, Sender
        waits = list(mail.get("retry_minutes", [10, 20]))  # mail server not answering → try again later
        pending = list(jobs)
        while pending:
            done = []
            try:
                with Sender(mail) as s:
                    for job in pending:
                        rid, to, subject, body, plain, rows, lid, due_ics = job
                        if not to:
                            print(f"{rid}: no address in Rays — skipped")
                            done.append(job)
                            continue
                        msg = EmailMessage()
                        msg["From"], msg["To"], msg["Subject"] = sender_addr, to, subject
                        msg["Reply-To"] = reply_to
                        msg["Message-ID"] = make_msgid(domain="floktron")
                        msg.set_content(plain)
                        msg.add_alternative(body, subtype="html")
                        if due_ics:
                            msg.add_attachment(due_ics.encode("utf-8"), maintype="text", subtype="calendar",
                                               filename="floktron-due-dates.ics")
                        s.send(msg)
                        done.append(job)
                        sent += 1
                        print(f"{rid}: sent → {to}")
                        if not a.test and not a.evening:
                            for r in rows:
                                if r[6].value == "New":
                                    r[6].value = "Sent"
                                r[8].value = now.strftime("%Y-%m-%d %H:%M")
                                r[9].value = lid
                                if str(rid) in tidy:
                                    r[sc - 1].value = tasks_tidy.mark_shown(r[sc - 1].value, today)
            except MailError as e:
                print("MAIL ERROR:", e)
            pending = [j for j in pending if j not in done]
            if pending and waits:
                w = waits.pop(0)
                print(f"not sent: {', '.join(j[0] for j in pending)} — retry in {w} min")
                time.sleep(float(w) * 60)
            elif pending:
                print(f"NOT SENT after retries: {', '.join(j[0] for j in pending)}")
                break

    if not a.test:
        wb["Run_log"].append([now.strftime("%Y-%m-%d %H:%M"), "send_morning" + (" --evening" if a.evening else "") + (" --dry" if a.dry else ""),
                              f"messages built: {len(jobs)}, sent: {sent}", "OK"])
        wb.save(a.base)


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    main()
