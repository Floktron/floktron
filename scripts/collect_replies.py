# -*- coding: utf-8 -*-
"""FLOKTRON · collect_replies.py — reads button replies, updates the base, escalates.

Reply subjects (made by send_morning.py buttons):
    FLOKTRON#<YYYYMMDD-ray> T:<task-id> +   → task Done, answer saved in the task
    FLOKTRON#<YYYYMMDD-ray> T:<task-id> -   → task Not done → escalation to the team lead
    FLOKTRON#<YYYYMMDD-ray> OK | Q | NO     → whole message Accepted | Question | Cannot (Q and NO escalate)
    FLOKTRON#<YYYYMMDD-ray> R  or plain «Reply» with a written report → each line / table row
        «<N> + | - | * <comment>» closes task N of that message (N = its number in the letter, or the task ID).
        A table pasted from a spreadsheet works too (number, sign and comment in different cells).
        + ✅ * → Done · - − ❌ → Not done. A report that matches no task is flagged «report not recognised».
    ... TEST ...                         → only recorded, tasks are not touched
Every reply is also saved as a file: data/replies/<date>/<message>_<code>_<HHMM>.eml
Running twice is safe: replies are recognised by their Message-ID.

Afterwards route.py turns the answers into next tasks (unless --no-route).

Usage:
    python3 scripts/collect_replies.py                 # read the mailbox, last 2 days
    python3 scripts/collect_replies.py --days 5
    python3 scripts/collect_replies.py --deadline      # also: who got a message today and did not answer
    python3 scripts/collect_replies.py --from-dir DIR  # read .eml files instead of the mailbox
    python3 scripts/collect_replies.py --no-escalation # record only, send nothing
Options: --config <file>  --base <file>
"""
import argparse
import datetime
import email
import email.utils
import os
import re
import sys
from email.header import decode_header, make_header
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")

CODES = {"OK": "Accepted", "Q": "Question", "NO": "Cannot", "R": "Report"}
SIGNS = {"+": "+", "✅": "+", "*": "+", "-": "-", "−": "-", "–": "-", "❌": "-"}
OPEN = ("New", "Sent", "Accepted", "Question", "Cannot")


def load_config(path):
    if not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def hdr(v):
    return str(make_header(decode_header(v or "")))


def text_of(msg):
    for part in msg.walk():
        if part.get_content_type() == "text/plain" and not part.get_filename():
            return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            h = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
            return re.sub(r"<[^>]+>", " ", h)
    return ""


def html_of(msg):
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
    return ""


def report_lines(msg):
    """Written report → [(number or task ID, '+'/'-', comment)].
    Reads a table pasted from a spreadsheet (cells in <tr>) and plain lines «2 + done» / «T005 - busy»."""
    import html as _h
    out = []
    h = re.split(r"(?i)<blockquote|class=\"?gmail_quote", html_of(msg))[0]
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", h):
        cells = [re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
        cells = [c for c in cells if c]
        if not cells or not re.fullmatch(r"[A-Za-z]{0,3}\d{1,4}(-\d+)?", cells[0]):
            continue
        for i, c in enumerate(cells[1:], 1):
            mm = re.fullmatch(r"([+\-−–*✅❌])\s*(.*)", c)
            if mm:
                com = " ".join(x for x in [mm.group(2)] + cells[i + 1:i + 2] if x)
                out.append((cells[0], SIGNS[mm.group(1)], com.strip()))
                break
    if out:
        return out
    for ln in strip_quote(text_of(msg)).splitlines():
        mm = re.match(r"\s*([A-Za-z]{0,3}\d{1,4}(?:-\d+)?)[.)]?\s*([+\-−–*✅❌])\s*[—:\-]?\s*(.*)", ln)
        if mm:
            out.append((mm.group(1), SIGNS[mm.group(2)], mm.group(3).strip()))
    return out


def strip_quote(t):
    """Cut the quoted original message below the answer."""
    out = []
    for ln in t.splitlines():
        if ln.startswith(">") or re.match(r"^(On|Am|В|Le|Pirmd|Otrd).+(wrote|schrieb|написал|écrit|rakstīja)", ln) \
                or "Original Message" in ln:
            break
        out.append(ln)
    return "\n".join(out)


SIGN_OFF = re.compile(
    r"(best regards|kind regards|regards,|thanks and regards|ar cieņu|ar labām vēlēšanām|с уважением|"
    r"sent from my|отправлено с|nosūtīts no|sūtīts no|get outlook for)", re.I)
BUTTON_TEXT = re.compile(r"✅\s*(Accepted|Pieņemu|Принимаю)\.?", re.I)


def answer_only(t):
    """Remove the task context the button put in, and the ✍️ prompts — what is left is the person's answer.
    Works whether they wrote at the top or at the end (mobile mail apps glue lines together)."""
    t = re.sub(r"(?s)(Tasks in this message:|Uzdevumi šajā vēstulē:|Задачи в этом письме:|"
               r"(Task|Uzdevums|Задача)\s*\d+\s*:).*?(?=✍️|✅|$)", " ", t)
    t = re.sub(r"✍️[^:\n]*:", " ", t)
    t = BUTTON_TEXT.sub(" ", t)
    m = SIGN_OFF.search(t)          # cut the e-mail signature ("Best regards …", "Sent from my iPhone")
    if m:
        t = t[:m.start()]
    t = re.sub(r"(?m)^--\s*$.*", " ", t, flags=re.S)
    return re.sub(r"\s+", " ", t).strip(" .,;")


def parse(raw, own_addresses, marker="FLOKTRON#"):
    """Return a dict describing one FLOKTRON reply, or None if it is not one."""
    msg = email.message_from_bytes(raw)
    subject = hdr(msg["Subject"])
    mk = re.escape(marker)
    m = re.search(mk + r"(\d{8})-(L\d+)", subject)
    if not m:
        return None
    sender = hdr(msg["From"])
    mt = re.search(r"\bT:(\S+)\s*([+\-−])", subject)
    mc = re.search(mk + r"\d{8}-L\d+(?:\s+TEST)?\s+(OK|Q|NO|R)\b", subject)
    addr = email.utils.parseaddr(sender)[1].lower()
    lines = []
    if not (mt or mc):
        if addr in {str(x).lower() for x in own_addresses if x}:
            return None  # our own outgoing morning message
        lines = report_lines(msg)          # plain «Reply»: a written report, or else simply «Accepted»
        code = "R" if lines else "OK"
    else:
        code = mc.group(1) if mc else None
        if code == "R":
            lines = report_lines(msg)
    try:
        when = email.utils.parsedate_to_datetime(msg["Date"]).astimezone()
    except (TypeError, ValueError):
        when = datetime.datetime.now().astimezone()
    return {
        "raw": raw,
        "mid": msg.get("Message-ID", "") or f"{subject}-{when.isoformat()}",
        "lid": f"{m.group(1)}-{m.group(2)}",
        "ray": m.group(2),
        "test": bool(re.search(mk + r"\d{8}-L\d+\s+TEST\b", subject)),
        "task": mt.group(1) if mt else None,
        "sign": ("+" if mt.group(2) == "+" else "-") if mt else None,
        "code": code,
        "lines": lines,
        "from": sender,
        "when": when,
        "answer": answer_only(strip_quote(text_of(msg)))[:500],
    }


def save_eml(r):
    d = os.path.join(ROOT, "data", "replies", r["when"].strftime("%Y-%m-%d"))
    os.makedirs(d, exist_ok=True)
    code = (f"T{r['task']}{'P' if r['sign'] == '+' else 'M'}" if r["task"] else r["code"])
    fn = os.path.join(d, f"{r['lid']}_{'TEST_' if r['test'] else ''}{code}_{r['when']:%H%M}.eml")
    if not os.path.exists(fn):
        with open(fn, "wb") as f:
            f.write(r["raw"])


def main():
    ap = argparse.ArgumentParser(description="Collect FLOKTRON replies.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--base", default=os.path.join(ROOT, "data", "floktron_base.xlsx"))
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--from-dir", default="")
    ap.add_argument("--deadline", action="store_true")
    ap.add_argument("--no-escalation", action="store_true")
    ap.add_argument("--no-route", action="store_true", help="do not create next tasks (route.py)")
    a = ap.parse_args()

    cfg = load_config(a.config)
    mail = cfg.get("mail") or {}
    company = (cfg.get("company") or {}).get("name") or "FLOKTRON"
    own = [mail.get("user"), mail.get("from"), mail.get("reply_to")]
    marker = mail.get("marker") or "FLOKTRON#"
    now = datetime.datetime.now()

    if a.from_dir:
        from mail.read import from_folder
        raws = list(from_folder(a.from_dir))
    else:
        from mail.read import from_imap
        from mail.send import MailError
        try:
            raws = list(from_imap(mail, a.days, marker))
        except MailError as e:
            sys.exit(f"MAIL ERROR: {e}")

    wb = openpyxl.load_workbook(a.base)
    wk, wr, wt = wb["Receipts"], wb["Evening_reports"], wb["Tasks"]
    seen = {r[6] for r in wk.iter_rows(min_row=2, values_only=True)} | \
           {r[5] for r in wr.iter_rows(min_row=2, values_only=True)}
    rays = {r[0]: r for r in wb["Rays"].iter_rows(min_row=2, values_only=True) if r[0]}
    manager = mail.get("manager_address") or (rays.get("L0") or [None] * 4)[3] or ""
    any_sender = bool(mail.get("allow_any_sender"))

    def allowed(ray, sender):
        """A reply counts only if it comes from the ray's own address, its team lead or the manager.
        Anyone can write a subject line — this stops a stranger from closing tasks."""
        if any_sender:
            return True
        addr = email.utils.parseaddr(sender)[1].lower()
        info = rays.get(ray) or []
        ok = {str(x).lower() for x in (info[3] if len(info) > 3 else None,
                                        info[8] if len(info) > 8 else None, manager) if x}
        return addr in ok

    events, new = [], 0
    for raw in raws:
        r = parse(raw, own, marker)
        if not r:
            continue
        save_eml(r)
        if r["mid"] in seen:
            continue
        seen.add(r["mid"])
        new += 1
        got = r["when"].strftime("%Y-%m-%d %H:%M")
        tag = " TEST" if r["test"] else ""
        if not allowed(r["ray"], r["from"]):
            wk.append([got, r["lid"] + tag, r["ray"], "Unknown sender — ignored", r["answer"], r["from"], r["mid"]])
            print(f"{r['ray']}: reply from an unknown address {r['from']} — recorded, tasks not touched")
            continue
        if r["task"]:
            wr.append([got, r["lid"] + tag, r["ray"], f"{r['task']} {r['sign']} {r['answer']}", r["from"], r["mid"]])
            if r["test"]:
                print(f"TEST: {r['task']} {r['sign']} «{r['answer'][:60]}» — tasks not touched")
                continue
            for row in wt.iter_rows(min_row=2, max_col=10):
                if str(row[0].value) == r["task"]:
                    row[6].value = "Done" if r["sign"] == "+" else "Not done"
                    row[7].value = f"{r['sign']} {r['answer']}".strip()
                    row[8].value = got
            print(f"{r['ray']}: task {r['task']} {r['sign']} «{r['answer'][:60]}»")
            if r["sign"] == "-":
                events.append((r["ray"], f"Task {r['task']} not done", r["answer"], r["lid"]))
        elif r["code"] == "R":
            wr.append([got, r["lid"] + tag, r["ray"], r["answer"] or "; ".join(f"{n} {s} {c}" for n, s, c in r["lines"]),
                       r["from"], r["mid"]])
            if r["test"]:
                print(f"TEST: report, {len(r['lines'])} lines — tasks not touched")
                continue
            letter = [row for row in wt.iter_rows(min_row=2, max_col=10)
                      if row[2].value == r["ray"] and row[9].value == r["lid"]]
            hit = 0
            for n, sign, com in r["lines"]:
                row = next((x for x in wt.iter_rows(min_row=2, max_col=10) if str(x[0].value) == n
                            and x[2].value == r["ray"]), None)
                if row is None and n.isdigit() and 0 < int(n) <= len(letter):
                    row = letter[int(n) - 1]
                if row is None:
                    continue
                row[6].value = "Done" if sign == "+" else "Not done"
                row[7].value = f"{sign} {com}".strip()
                row[8].value = got
                hit += 1
                print(f"{r['ray']}: report line {n} {sign} → {row[0].value}")
                if sign == "-":
                    events.append((r["ray"], f"Task {row[0].value} not done", com, r["lid"]))
            if r["lines"] and not hit:
                print(f"{r['ray']}: ⚠ report not recognised ({len(r['lines'])} lines, no task matched) — check by hand")
                wk.append([got, r["lid"] + tag, r["ray"], "Report not recognised", r["answer"], r["from"], r["mid"]])
        else:
            status = CODES[r["code"]]
            wk.append([got, r["lid"] + tag, r["ray"], status + (" (TEST)" if r["test"] else ""),
                       r["answer"], r["from"], r["mid"]])
            if r["test"]:
                print(f"TEST: {r['code']} «{r['answer'][:60]}»")
                continue
            for row in wt.iter_rows(min_row=2, max_col=10):
                if row[2].value == r["ray"] and row[9].value == r["lid"] and row[6].value in OPEN:
                    row[6].value = status
                    row[8].value = got
            print(f"{r['ray']}: {status} «{r['answer'][:60]}»")
            if r["code"] in ("Q", "NO"):
                events.append((r["ray"], status, r["answer"], r["lid"]))

    if a.deadline:  # no reaction at all is tracked separately from a "No"
        answered = {str(x[1]).split()[0] for x in wk.iter_rows(min_row=2, values_only=True) if x[1]} | \
                   {str(x[1]).split()[0] for x in wr.iter_rows(min_row=2, values_only=True) if x[1]}
        letters = os.path.join(ROOT, "data", "letters", now.date().isoformat())
        for rid in rays:
            lid = f"{now:%Y%m%d}-{rid}"
            if os.path.exists(os.path.join(letters, lid + ".html")) and lid not in answered:
                wk.append([now.strftime("%Y-%m-%d %H:%M"), lid, rid, "No reply", "", "", f"deadline-{lid}"])
                events.append((rid, "No reply by deadline", "", lid))
                print(f"{rid}: no reply by deadline")

    if events and not a.no_escalation:
        escalate(events, rays, manager, mail, company, now)

    created = []
    if not a.no_route:
        import route
        created = route.run(wb, now=now, cfg=cfg)
        for nid, to, txt in created:
            print(f"route: {nid} → {to}: {txt[:80]}")

    wb["Run_log"].append([now.strftime("%Y-%m-%d %H:%M"), "collect_replies",
                          f"new replies: {new}, escalations: {len(events)}, new tasks: {len(created)}", "OK"])
    wb.save(a.base)
    print(f"new replies: {new} · escalations: {len(events)} · new tasks: {len(created)}")


def escalate(events, rays, manager, mail, company, now):
    from mail.send import MailError, Sender
    try:
        with Sender(mail) as s:
            for ray, what, body, lid in events:
                info = rays.get(ray) or [ray, ray, "", "", "", "", "", "", ""]
                lead = info[8] if len(info) > 8 and info[8] else manager
                if not lead:
                    print(f"{ray}: no team lead or manager address — escalation not sent")
                    continue
                msg = EmailMessage()
                msg["From"] = mail.get("from") or mail.get("user")
                msg["To"] = lead
                msg["Subject"] = f"⚠️ {company} · {info[1]}: {what}"
                msg.set_content(
                    f"FLOKTRON · escalation · {now:%d.%m.%Y %H:%M}\n\n"
                    f"Ray: {info[1]} ({ray}), responsible: {info[2] or '—'}\n"
                    f"Event: {what}\n" + (f"Answer: {body}\n" if body else "") +
                    f"\nMessage {lid}. Please decide or reassign.")
                s.send(msg)
                print(f"escalation {ray} «{what}» → {lead}")
    except MailError as e:
        print("MAIL ERROR (escalation not sent):", e)


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    main()
