# -*- coding: utf-8 -*-
"""Invoices → accounting: offline checks on FICTIONAL documents (tests/fixtures/invoices, 7 languages + a scan).
The extraction file is what an AI assistant read from the page images; the script does the bookkeeping logic."""
import json
import os
import shutil
import sys

import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(ROOT, "tests", "fixtures", "invoices")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import invoices as inv  # noqa: E402

IBAN = "LV80BANK0000435195001"


def args(tmp, statements="statements_csv", extraction=None, *extra):
    return ["--config", str(tmp / "none.yaml"), "--folder", os.path.join(FX, "docs"),
            "--extraction", extraction or os.path.join(FX, "extraction.json"),
            "--statements", os.path.join(FX, statements), "--base", str(tmp / "floktron_base.xlsx"),
            "--iban", IBAN, "--today", "2026-11-22", *extra]


def base(tmp):
    shutil.copy(os.path.join(ROOT, "templates", "floktron_base_empty.xlsx"), tmp / "floktron_base.xlsx")


def rows(tmp, sheet):
    ws = openpyxl.load_workbook(tmp / "floktron_base.xlsx")[sheet]
    h = [c.value for c in ws[1]]
    return [dict(zip(h, r)) for r in ws.iter_rows(min_row=2, values_only=True)]


def test_numbers_and_dates():
    assert inv.to_float("-60,50") == 60.5
    assert inv.to_float("1.234,56") == 1234.56
    assert inv.to_float("1,234.56") == 1234.56
    assert inv.to_date("05.11.2026").isoformat() == "2026-11-05"
    assert inv.norm("Rēķins PR-2026/118") == "REKINSPR2026118"


def test_dry_run_writes_nothing(tmp_path, capsys):
    base(tmp_path)
    before = (tmp_path / "floktron_base.xlsx").read_bytes()
    assert inv.main(args(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "New documents: 9" in out and "= copy of" in out
    assert (tmp_path / "floktron_base.xlsx").read_bytes() == before


def test_apply_statuses_tasks_and_rerun(tmp_path, capsys):
    base(tmp_path)
    assert inv.main(args(tmp_path, "statements_csv", None, "--apply", "--test")) == 0
    got = {r["Document no."]: r for r in rows(tmp_path, "Invoices")}
    assert len(got) == 9                                                    # 10 files, one forwarded copy
    assert got["PR-2026/118"]["Status"].startswith("Paid 12.11.2026")
    assert got["PR-2026/118"]["File"] == "Paraugs Reagenti/Rekins_PR-2026-118.pdf"   # the original, not the FW_ copy
    assert got["2026-0457"]["Status"] == "Not found in statement (similar payment)"  # RIMI card payment is not taken
    assert got["LS-8812"]["Status"] == "Not a payment document" and got["LS-8812"]["Linked to"] == "invoice 2026-0457"
    assert got["PF-2026-0089"]["Status"].endswith("no final invoice")
    assert got["7781"]["Status"].endswith("no final invoice")
    assert got["Д-0042"]["Status"] == "To pay by 01.12.2026"
    assert got["2026110"]["Status"].startswith("Paid 21.10.2026")         # the scan, matched by its variable symbol
    assert "reverse charge" in got["INV-50731"]["Comment"]
    assert "VAT of DE" in got["2026-0457"]["Comment"]
    assert all(r["Comment"].startswith("TEST") for r in got.values())
    tasks = [t for t in rows(tmp_path, "Tasks") if str(t["Task ID"]).startswith("TI")]
    assert len(tasks) == 6 and all(t["Task"].startswith("TEST: ") and t["Ray"] == "L7" for t in tasks)
    text = " ".join(t["Task"] for t in tasks)
    assert "RIMI" in text and "final invoice for proforma no. PF-2026-0089" in text and "Pass 9 supplier documents" in text
    capsys.readouterr()
    assert inv.main(args(tmp_path, "statements_csv", None, "--apply", "--test")) == 0   # second run: nothing new
    assert "New documents: 0" in capsys.readouterr().out
    assert len(rows(tmp_path, "Invoices")) == 9


def test_pdf_statement_same_result(tmp_path, capsys):
    pytest.importorskip("pypdf")
    base(tmp_path)
    assert inv.main(args(tmp_path, "statements_pdf")) == 0
    out = capsys.readouterr().out
    assert "7 payments from statement_2026-10_11.pdf" in out and "payment found in the statement: 6 of 8" in out


def test_unread_document_is_listed(tmp_path, capsys):
    data = json.load(open(os.path.join(FX, "extraction.json"), encoding="utf-8"))
    data["docs"] = [x for x in data["docs"] if "scan_faktura" not in x["file"]]
    ex = tmp_path / "extraction.json"
    ex.write_text(json.dumps(data), encoding="utf-8")
    assert inv.main(args(tmp_path, "statements_csv", str(ex))) == 0
    assert "not read yet (no record in the extraction file): Vzorova Chemie/scan_faktura.pdf" in capsys.readouterr().out


def test_no_extraction_file(tmp_path, capsys):
    assert inv.main(args(tmp_path, "statements_csv", str(tmp_path / "missing.json"))) == 1
    assert "prompts/50_invoices.md" in capsys.readouterr().out


def test_dashboard_card(tmp_path):
    import dashboard as db
    base(tmp_path)
    assert inv.main(args(tmp_path, "statements_csv", None, "--apply", "--test")) == 0
    assert db.main(["--config", str(tmp_path / "none.yaml"), "--data", str(tmp_path)]) == 0
    page = (tmp_path / "dashboard.html").read_text(encoding="utf-8")
    assert "Invoices → accounting" in page and "6/8" in page and "Musterchemie" in page
