# -*- coding: utf-8 -*-
"""Payment gateways (scripts/gateways.py): offline checks on FICTIONAL data (tests/fixtures/gateways, built at test time).
Mail is a folder of .eml files (INBOX + Spam), the bank statement is a CSV (and a Swedbank-like PDF when pypdf and
reportlab are installed), notices go to an outbox folder — nothing is sent, no network, no link is opened."""
import glob
import os
import shutil
import sys

import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(ROOT, "tests", "fixtures", "gateways")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, FX)
import gateways as gw  # noqa: E402
import make_gateway_fixtures as make_fixtures  # noqa: E402

CFG = """company: {name: "Demo SIA (TEST · FICTIONAL)", language: en, timezone: Europe/Riga}
mail: {user: office@demo-sia.example.com, manager_address: boss@demo-sia.example.com}
documents: {legal_name: "Demo SIA (TEST · FICTIONAL)", reg_no: "40000000077", vat_no: "LV40000000077", address: "Parauga iela 1, Riga (FICTIONAL)"}
invoices: {folder: "INBOX_DIR", our_iban: "IBAN", ray: L7}
gateways: {enabled: true, notify: mail, out: "OUT_DIR", act_days: 30, card_days: 120}
"""


@pytest.fixture
def world(tmp_path):
    fx = make_fixtures.main(str(tmp_path / "fx"))
    base = tmp_path / "base.xlsx"
    shutil.copy(os.path.join(ROOT, "templates", "floktron_base_empty.xlsx"), base)
    wb = openpyxl.load_workbook(base)
    ws = wb["Invoices"]
    ws.append(["TINV-0001", "2026-11-20", "SIA TEST Veikals (FICTIONAL)", "LV40000000011", "Invoice", "TV-1001", "2026-11-10", "", 24.79, 5.21,
               30.0, "EUR", "card", "Paid 10.11.2026", "10.11.2026 · 30.00 · TEST VEIKALS · name + amount + date", "", "Office", "TEST/TV-1001.pdf",
               "000000000000", "", "no", "TEST"])
    wb.save(base)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(CFG.replace("INBOX_DIR", str(tmp_path / "inbox")).replace("OUT_DIR", str(tmp_path / "gw")).replace("IBAN", make_fixtures.IBAN),
                   encoding="utf-8")

    def run(statements="statements_csv", *extra):
        args = ["--config", str(cfg), "--base", str(base), "--mail-folder", os.path.join(fx, "mail"), "--statements", os.path.join(fx, statements),
                "--outbox", str(tmp_path / "out"), "--today", "2026-11-23", "--test", *extra]
        assert gw.main(args) == 0
        wb = openpyxl.load_workbook(base)
        rows = [dict(zip(gw.HEAD, r)) for r in wb[gw.SHEET].iter_rows(min_row=2, values_only=True)]
        tasks = [r for r in wb["Tasks"].iter_rows(min_row=2, values_only=True) if r[0]]
        return rows, tasks

    return dict(tmp=tmp_path, run=run, fx=fx)


def by(rows, word):
    return [r for r in rows if word.lower() in str(r["Seller"]).lower()]


def test_receipts_from_mail(world):
    rows, tasks = world["run"]()
    a = by(rows, "Cloudnote")
    assert len(a) == 1 and a[0]["Document"] == "PDF from the message"            # the copy in Spam is not counted twice
    assert "2026-11-03_TEST_Cloudnote_Ltd_24.20EUR.pdf" in a[0]["File"]
    assert os.path.exists(os.path.join(world["tmp"], "inbox", a[0]["File"]))    # → the usual invoice check
    b = by(rows, "Pixelforge")
    assert b and "Spam" in b[0]["Source"] and b[0]["Amount"] == 20.0 and b[0]["Currency"] == "USD"
    assert "Business invoice needed" in b[0]["Status"] and b[0]["Document"].startswith("copy of the message")
    assert "invoice.stripe.com" in b[0]["How to get the business invoice"] and "pixelforge-test" not in b[0]["How to get the business invoice"]
    assert "Add VAT" in by(rows, "Formwise")[0]["How to get the business invoice"]
    assert by(rows, "Iconkit")[0]["Gateway"] == "Lemon Squeezy"
    e = by(rows, "Notely")
    assert e and e[0]["Gateway"] == "Apple" and e[0]["Amount"] == 4.99 and "reportaproblem" in e[0]["How to get the business invoice"]
    assert by(rows, "Scanly")[0]["Gateway"] == "Google Play"
    assert not [r for r in rows if "What's new" in str(r["Comment"])]           # gateway news is not a payment
    assert not by(rows, "Paraugs")                                               # an ordinary invoice stays with mail watch
    h = [r for r in rows if str(r["Status"]).startswith("⚠")]
    assert len(h) == 1 and not h[0]["How to get the business invoice"] and not h[0]["Payment in statement"]
    req = glob.glob(os.path.join(world["tmp"], "gw", "requests", "*.txt"))
    assert len(req) == 3                                                         # Stripe, Paddle, Lemon — none for Apple / Google
    assert all("DRAFT — not sent" in open(p, encoding="utf-8").read() for p in req)
    assert all(str(t[3]).startswith("TEST:") and t[2] == "L7" for t in tasks if str(t[0]).startswith("TG"))


def test_card_payments_csv(world):
    rows, tasks = world["run"]()
    assert "24.20 EUR" in by(rows, "Cloudnote")[0]["Payment in statement"]
    assert by(rows, "Formwise")[0]["Charged EUR"] == 15.0 and by(rows, "Notely")[0]["Charged EUR"] == 4.99
    assert by(rows, "Scanly")[0]["Charged EUR"] == 2.99
    v = by(rows, "VECTORLY")
    assert v and "internal act" in v[0]["Status"]                                # 59 days without a document
    assert not by(rows, "VEIKALS")                                               # already in the sheet Invoices
    assert not by(rows, "Paraugs Būve")                                          # a transfer is not a card payment
    acts = glob.glob(os.path.join(world["tmp"], "gw", "acts", "*"))
    if acts:  # reportlab installed
        assert "VECTORLY" in acts[0]
    assert any("internal acts" in str(t[3]) for t in tasks)


def test_notice_and_rerun(world):
    rows, tasks = world["run"]()
    out = world["tmp"] / "out"
    notes = [open(out / f, encoding="utf-8").read() for f in sorted(os.listdir(out))]
    assert len(notes) == 1 and "card payments" in notes[0] and "Pixelforge" in notes[0]
    rows2, tasks2 = world["run"]()
    assert len(rows2) == len(rows) and len(tasks2) == len(tasks)                 # safe to run again


def test_dry_run_writes_nothing(world):
    gw.main(["--config", str(world["tmp"] / "config.yaml"), "--base", str(world["tmp"] / "base.xlsx"), "--mail-folder",
             os.path.join(world["fx"], "mail"), "--statements", os.path.join(world["fx"], "statements_csv"), "--today", "2026-11-23",
             "--dry-run"])
    assert gw.SHEET not in openpyxl.load_workbook(world["tmp"] / "base.xlsx").sheetnames
    assert not os.path.exists(world["tmp"] / "inbox")


def test_card_payments_pdf_foreign_currency(world):
    pytest.importorskip("pypdf")
    pytest.importorskip("reportlab")
    rows, _ = world["run"]("statements_pdf")
    b = by(rows, "Pixelforge")[0]
    assert b["Charged EUR"] == 18.89 and "fee 0.46" in b["Payment in statement"]   # 20.00 USD → 18.89 EUR
    assert by(rows, "Iconkit")[0]["Charged EUR"] == 8.47
    n = by(rows, "NAME-CHEAP")
    assert n and n[0]["Currency"] == "USD" and n[0]["Charged EUR"] == 5.75 and "find the receipt" in n[0]["Status"]
    assert os.path.exists(os.path.join(world["tmp"], "inbox", b["File"]))       # PDF copy of the message


def test_disabled_does_nothing(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("gateways: {enabled: false}\n", encoding="utf-8")
    assert gw.main(["--config", str(cfg), "--base", str(tmp_path / "none.xlsx")]) == 0
