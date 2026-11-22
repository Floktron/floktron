# -*- coding: utf-8 -*-
"""Branded documents (invoice, advance invoice, act, offer): offline checks on FICTIONAL data
(tests/fixtures/documents, Demo SIA). Skipped when reportlab is not installed."""
import glob
import json
import os
import re
import sys

import pytest

pytest.importorskip("reportlab")
import openpyxl  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(ROOT, "tests", "fixtures", "documents")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import documents as docs  # noqa: E402

SELLER = os.path.join(FX, "seller_demo.json")


def run(monkeypatch, tmp, doc, *extra):
    argv = ["documents.py", "--seller", SELLER, "--doc", doc, "--out", str(tmp / "out"), *extra]
    monkeypatch.setattr(sys, "argv", argv)
    return docs.main()


def test_amount_in_words():
    assert docs.amount_words(310.49, "lv") == "Trīs simti desmit eiro un 49 centi"
    assert docs.amount_words(1189.43, "lv") == "Tūkstotis simts astoņdesmit deviņi eiro un 43 centi"
    assert docs.amount_words(21021.01, "lv") == "Divdesmit viens tūkstotis divdesmit viens eiro un 01 cents"
    assert docs.amount_words(11.11, "lv") == "Vienpadsmit eiro un 11 centi"
    assert docs.amount_words(393.20, "en") == "Three hundred ninety-three euro and 20 cents"


def test_totals_round_half_up():
    lines, net, vat, total, rate = docs.calc({"vat_rate": 21, "lines": [
        {"desc": "a", "qty": 4, "price": 89.90}, {"desc": "b", "qty": 1, "price": 15}]})
    assert (str(net), str(vat), str(total)) == ("374.60", "78.67", "453.27")


@pytest.mark.parametrize("name", ["invoice_lv", "advance_lv", "act_lv", "offer_en", "invoice_lv_en_eu"])
def test_every_type_makes_a_pdf(monkeypatch, tmp_path, name):
    path = run(monkeypatch, tmp_path, os.path.join(FX, name + ".json"))
    assert os.path.basename(path).startswith("TEST_")
    data = open(path, "rb").read()
    assert data.startswith(b"%PDF") and len(data) > 5000


def test_numbering_and_register(monkeypatch, tmp_path):
    base = tmp_path / "base.xlsx"
    openpyxl.Workbook().save(base)
    doc = os.path.join(FX, "invoice_lv.json")
    run(monkeypatch, tmp_path, doc, "--base", str(base))                # dry run: nothing written
    assert "Issued" not in openpyxl.load_workbook(base).sheetnames
    run(monkeypatch, tmp_path, doc, "--base", str(base), "--apply")
    run(monkeypatch, tmp_path, doc, "--base", str(base), "--apply")
    ws = openpyxl.load_workbook(base)["Issued"]
    nums = [r[0] for r in ws.iter_rows(min_row=2, values_only=True)]
    assert nums == ["DEMO-R-2026-001", "DEMO-R-2026-002"]
    assert [r[14] for r in ws.iter_rows(min_row=2, values_only=True)] == ["TEST", "TEST"]


def test_fixed_number_is_never_reused(monkeypatch, tmp_path):
    base = tmp_path / "base.xlsx"
    openpyxl.Workbook().save(base)
    d = json.load(open(os.path.join(FX, "act_lv.json"), encoding="utf-8"))
    d["number"] = "DEMO-A-2026-007"
    p = tmp_path / "act.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    run(monkeypatch, tmp_path, str(p), "--base", str(base), "--apply")
    with pytest.raises(SystemExit):
        run(monkeypatch, tmp_path, str(p), "--base", str(base), "--apply")


def test_long_invoice_flows_to_more_pages(monkeypatch, tmp_path):
    d = json.load(open(os.path.join(FX, "invoice_lv.json"), encoding="utf-8"))
    d["lines"] = [{"desc": f"Line {i} with a long description that must wrap inside the table cell", "qty": i,
                   "unit": "pcs", "price": 1.11} for i in range(1, 41)]
    p = tmp_path / "long.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    path = run(monkeypatch, tmp_path, str(p))
    pages = re.findall(rb"/Type\s*/Page(?!s)", open(path, "rb").read())
    assert len(pages) >= 2


def test_missing_seller_field_stops(monkeypatch, tmp_path):
    s = json.load(open(SELLER, encoding="utf-8"))
    s["iban"] = ""
    p = tmp_path / "seller.json"
    p.write_text(json.dumps(s), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["documents.py", "--seller", str(p), "--doc",
                                      os.path.join(FX, "invoice_lv.json"), "--out", str(tmp_path)])
    with pytest.raises(SystemExit):
        docs.main()
