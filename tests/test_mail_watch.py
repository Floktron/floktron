# -*- coding: utf-8 -*-
"""Mail watch (scripts/mail_watch.py): offline checks on a FICTIONAL mailbox (tests/fixtures/mail_watch).
Mail is a folder of .eml files built at test time, notices go to an outbox folder — nothing is sent, no network."""
import json
import os
import shutil
import sys

import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(ROOT, "tests", "fixtures", "mail_watch")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, FX)
import mail_watch as mw  # noqa: E402
import make_fixtures  # noqa: E402

CFG = """company: {name: "Demo SIA (TEST · FICTIONAL)", language: LANG, timezone: Europe/Riga}
mail: {user: office@demo-sia.example.com, manager_address: boss@demo-sia.example.com, marker: "FLOKTRON#"}
invoices: {folder: "INBOX", extraction: "EXTR"}
mail_watch:
  enabled: true
  notify: mail
  important: {biedriba-paraugs.example.com: "Paraugu biedriba (TEST)", vid-demo.example.com: "VID demo (TEST)"}
"""


@pytest.fixture
def world(tmp_path):
    mail = make_fixtures.main(str(tmp_path / "mail"))
    base = tmp_path / "base.xlsx"
    shutil.copy(os.path.join(ROOT, "templates", "floktron_base_empty.xlsx"), base)

    def cfg(lang="en"):
        p = tmp_path / f"cfg_{lang}.yaml"
        p.write_text(CFG.replace("LANG", lang).replace("INBOX", str(tmp_path / "inbox")).replace("EXTR", str(tmp_path / "extraction.json")),
                     encoding="utf-8")
        return str(p)

    def run(now, lang="en", *extra):
        args = ["--config", cfg(lang), "--base", str(base), "--mail-folder", mail, "--outbox", str(tmp_path / "out"),
                "--now", now, "--test", *extra]
        assert mw.main(args) == 0
        wb = openpyxl.load_workbook(base)
        return {r[5]: dict(zip(mw.HEAD, r)) for r in wb["Mail"].iter_rows(min_row=2, values_only=True)}, wb

    def notices():
        d = tmp_path / "out"
        return [open(d / f, encoding="utf-8").read() for f in sorted(os.listdir(d))] if d.exists() else []

    return dict(tmp=tmp_path, base=base, run=run, notices=notices)


def test_categories_need_and_contacts(world):
    rows, wb = world["run"]("2026-11-23 10:00")
    cat = {s: r["Category"] for s, r in rows.items()}
    assert cat["Seminārs par būvūdeņiem"] == "Confirm"
    assert cat["Quantities for site 7"] == "Reply awaited"
    assert cat["Приглашение на объект"] == "Invitation"
    assert cat["Angebot"] == "Deadline"
    assert cat["Küsimus kotte kohta"] == "Question"
    assert cat["Rēķins PR-2026-118"] == "Invoice"
    assert cat["Weekly: please reply to our survey"] in ("Newsletter", "Notice")  # "please reply" in a mailing is not personal
    assert cat["Jauns ziņojums"] == "Notice (important)"
    assert cat["Your verification code: 123456"] == "Code / login"
    assert cat["Automatic reply: Kaina"] == "Auto-reply"
    assert cat["FLOKTRON# L1 2026-11-23 ACCEPT"] == "FLOKTRON (system)"
    assert cat["Re: Quantities for site 7"] == "Sent"
    assert rows["Angebot"]["Need"] == "deadline: 10.12"
    assert "04.12.2026" in rows["Seminārs par būvūdeņiem"]["Dates in mail"]
    assert rows["Seminārs par būvūdeņiem"]["Organisation"] == "Paraugu biedriba (TEST)"
    assert all(r["Comment"] == "TEST" for r in rows.values())
    contacts = {r[0]: r for r in wb["Contacts"].iter_rows(min_row=2, values_only=True)}
    assert "+49 30 0000 0000" in contacts["buyer@muster-bau.example.com"][3]
    assert contacts["buyer@muster-bau.example.com"][4] == "www.muster-bau.example.com"
    assert "news@buildnews.example.com" not in contacts and "boss@demo-sia.example.com" not in contacts
    assert "office@demo-sia.example.com" not in contacts


def test_answered_star_and_reminders(world):
    rows, _ = world["run"]("2026-11-23 10:00")
    q = rows["Quantities for site 7"]
    assert q["Answered"] == "yes" and q["Status"] == "Answered" and not q["Reminded"]  # the sent reply answers it
    assert rows["Katalogas"]["Star"] == "⭐" and rows["Katalogas"]["Status"] == "Starred, waiting"
    assert not rows["Please confirm your attendance"]["Reminded"]  # a week old before the first run: sheet only
    reminded = {s for s, r in rows.items() if r["Reminded"]}
    assert reminded == {"Seminārs par būvūdeņiem", "Приглашение на объект", "Angebot", "Küsimus kotte kohta", "Jauns ziņojums"}
    n = world["notices"]()
    assert len(n) == 2 and "invoices from mail wait to be read: 1" in n[0] and "Seminārs par būvūdeņiem" in n[1]
    # same hour again: nothing new, no second reminder
    world["run"]("2026-11-23 10:30")
    assert len(world["notices"]()) == 2
    # next day: the second (last) reminder
    rows, _ = world["run"]("2026-11-24 10:30")
    assert rows["Angebot"]["Reminded"].endswith("(2)")
    assert len(world["notices"]()) == 3
    rows, _ = world["run"]("2026-11-25 11:00")
    assert len(world["notices"]()) == 3  # at most twice


def test_closed_by_hand_and_quiet_hours(world):
    world["run"]("2026-11-23 23:30")  # quiet hours: written, nothing sent
    assert world["notices"]() == []
    wb = openpyxl.load_workbook(world["base"])
    ws = wb["Mail"]
    for r in ws.iter_rows(min_row=2):
        if r[5].value == "Angebot":
            r[12].value = "Closed"
    wb.save(world["base"])
    rows, _ = world["run"]("2026-11-24 08:00")
    assert not rows["Angebot"]["Reminded"]
    assert "Angebot" not in world["notices"]()[-1]
    assert "Seminārs par būvūdeņiem" in world["notices"]()[-1]


def test_invoice_saved_once_then_checked(world):
    rows, _ = world["run"]("2026-11-23 10:00")
    f = rows["Rēķins PR-2026-118"]["Invoice file"]
    assert f == "Paraugs Reagenti/2026-11-23_Rekins_PR-2026-118.pdf"
    assert os.path.exists(world["tmp"] / "inbox" / f)
    # the AI assistant read it (prompts/50_invoices.md) → the next run hands it to invoices.py by itself
    rec = json.load(open(os.path.join(ROOT, "tests", "fixtures", "invoices", "extraction.json"), encoding="utf-8"))
    r = next(x for x in rec["docs"] if x["file"] == "Paraugs Reagenti/Rekins_PR-2026-118.pdf")
    json.dump({"docs": [dict(r, file=f)]}, open(world["tmp"] / "extraction.json", "w", encoding="utf-8"), ensure_ascii=False)
    world["run"]("2026-11-23 10:30")
    wb = openpyxl.load_workbook(world["base"])
    inv = [r for r in wb["Invoices"].iter_rows(min_row=2, values_only=True) if r[0]]
    assert len(inv) == 1 and "Paraugs" in str(inv[0][2])
    # same message again from another run: no second file
    os.remove(world["tmp"] / ".mail_watch_state.json")
    world["run"]("2026-11-23 11:00")
    assert len(os.listdir(world["tmp"] / "inbox" / "Paraugs Reagenti")) == 1


def test_notice_language_and_real_rows_untouched(world):
    world["run"]("2026-11-23 10:00", "lv")
    assert "pasts gaida jūs" in world["notices"]()[-1] and "apstiprināt" in world["notices"]()[-1]
    # a run without --test never reminds about TEST rows
    args = ["--config", str(world["tmp"] / "cfg_lv.yaml"), "--base", str(world["base"]), "--mail-folder",
            str(world["tmp"] / "mail"), "--outbox", str(world["tmp"] / "out2"), "--now", "2026-11-24 10:00",
            "--state", str(world["tmp"] / "s2.json")]
    assert mw.main(args) == 0
    out2 = world["tmp"] / "out2"
    assert not [x for x in (os.listdir(out2) if out2.exists() else []) if "pasts gaida jūs" in open(out2 / x, encoding="utf-8").read()]


def test_formula_text_stays_text(world, tmp_path):
    from email.message import EmailMessage
    m = EmailMessage()
    m["From"] = "x@evil.example.com"
    m["To"] = "office@demo-sia.example.com"
    m["Subject"] = '=HYPERLINK("http://bad.example","click")'
    m["Date"] = "Mon, 23 Nov 2026 09:00:00 +0200"
    m["Message-ID"] = "<evil@evil.example.com>"
    m.set_content("please reply")
    with open(tmp_path / "mail" / "99_evil.eml", "wb") as f:
        f.write(bytes(m))
    world["run"]("2026-11-23 10:00")
    wb = openpyxl.load_workbook(world["base"])
    vals = [r[5] for r in wb["Mail"].iter_rows(min_row=2, values_only=True)]
    assert any(str(v).startswith("'=HYPERLINK") for v in vals)


def test_categories_selftest_words():
    ctx = dict(tz=None, now=None, own=set(), important={}, system=mw.re.compile("FLOKTRON#"))
    assert mw.classify("Termin", "Palun kinnitage osalemine", mw.email.message.Message(), "a@b.ee", [], False, set(), ctx["system"]) in ("Confirm", "Letter")
    assert mw.need_word("ru", "deadline: 10.12") == "срок: 10.12"
    assert mw.need_word("de", "reply") == "antworten"


def test_dashboard_card(world):
    world["run"]("2026-11-23 10:00", "ru")
    import dashboard
    import datetime
    cfg = {"company": {"language": "ru"}}
    shutil.copy(world["base"], world["tmp"] / "floktron_base.xlsx")
    D = dashboard.collect(cfg, str(world["tmp"]), now=datetime.datetime(2026, 11, 24, 9, 0))
    assert D["inbox"]["n"] == 14 and D["inbox"]["need"] >= 5 and D["inbox"]["star"] == 1
    html = dashboard.render(D)
    assert "Почта ждёт ответа" in html and "подтвердить" in html


def test_imap_path_read_only(world, monkeypatch):
    """The real mailbox path with a fake IMAP server: only SELECT readonly, SEARCH and BODY.PEEK fetches."""
    import email as em
    import mail.read as mr
    mail = world["tmp"] / "mail"
    files = sorted(f for f in os.listdir(mail) if f.endswith(".eml"))
    boxes = {"INBOX": [f for f in files if not f.startswith("14")], '"Sent"': [f for f in files if f.startswith("14")]}
    calls = []

    class FakeIMAP:
        def __init__(self, *a):
            self.box = None

        def starttls(self, **k):
            pass

        def login(self, *a):
            pass

        def logout(self):
            pass

        def select(self, name, readonly=False):
            assert readonly
            self.box = name
            return ("OK", [b"1"])

        def search(self, *a):
            return ("OK", [" ".join(str(i + 1) for i in range(len(boxes[self.box]))).encode()])

        def fetch(self, num, what):
            calls.append(what)
            f = boxes[self.box][int(num) - 1]
            raw = open(mail / f, "rb").read()
            star = b" \\Flagged" if f.startswith("12") else b""
            if "HEADER.FIELDS" in what:
                m = em.message_from_bytes(raw)
                h = "".join(f"{k}: {m.get(k)}\r\n" for k in ("Message-ID", "In-Reply-To") if m.get(k))
                return ("OK", [(b"1 (FLAGS (\\Seen" + star + b") BODY[HEADER] {1}", h.encode())])
            return ("OK", [(b"1 (BODY[] {1}", raw)])

    monkeypatch.setattr(mr.imaplib, "IMAP4", FakeIMAP)
    monkeypatch.setattr(mr, "_password", lambda cfg: "x")
    cfgp = world["tmp"] / "cfg_imap.yaml"
    cfgp.write_text(CFG.replace("LANG", "en").replace("INBOX", str(world["tmp"] / "inbox")).replace("EXTR", str(world["tmp"] / "e.json"))
                    + "  inbox_folders: [INBOX]\n", encoding="utf-8")
    cfgp.write_text(cfgp.read_text(encoding="utf-8").replace("mail: {", "mail: {provider: proton_bridge, "), encoding="utf-8")
    args = ["--config", str(cfgp), "--base", str(world["base"]), "--outbox", str(world["tmp"] / "out"), "--now", "2026-11-23 10:00", "--test"]
    assert mw.main(args) == 0
    assert all("PEEK" in c for c in calls)
    wb = openpyxl.load_workbook(world["base"])
    rows = {r[5]: dict(zip(mw.HEAD, r)) for r in wb["Mail"].iter_rows(min_row=2, values_only=True)}
    assert len(rows) == 14 and rows["Katalogas"]["Star"] == "⭐" and rows["Quantities for site 7"]["Answered"] == "yes"
    calls.clear()
    assert mw.main(args) == 0  # second run: headers only, no bodies for known messages
    assert calls and all("HEADER.FIELDS" in c for c in calls)
