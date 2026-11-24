# -*- coding: utf-8 -*-
"""Company library (profile + document templates on the computer): offline checks on FICTIONAL data only
(TEST · FICTIONAL — Demo SIA from tests/fixtures/documents)."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(ROOT, "tests", "fixtures", "documents")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import library  # noqa: E402

DEMO = {
    "company": {"name": "Demo SIA"},
    "documents": {"reg_no": "40000000000", "vat_no": "LV40000000000", "address": "Demo iela 1, Rīga, LV-1000",
                  "bank": "Demo Bank", "swift": "DEMOLV2X", "iban": "LV00DEMO0000000000000", "prefix": "TST"},
}


def cfg_file(tmp, data):
    import yaml
    p = tmp / "config.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return str(p)


def test_shipped_templates_are_empty_forms():
    for name in ("invoice", "advance", "act", "offer"):
        with open(os.path.join(ROOT, "templates", "documents", name + ".json"), encoding="utf-8") as f:
            t = json.load(f)
        assert t["date"] == "" and t["buyer"]["name"] == ""
        assert "_about" in t


def test_init_check_new(tmp_path):
    cfg, lib = cfg_file(tmp_path, DEMO), str(tmp_path / "lib")
    assert library.main(["--config", cfg, "--dir", lib, "init"]) in (0, None)
    prof = json.load(open(os.path.join(lib, "company.json"), encoding="utf-8"))
    assert prof["name"] == "Demo SIA" and prof["iban"].startswith("LV00DEMO")
    assert sorted(os.listdir(os.path.join(lib, "templates"))) == ["act.json", "advance.json", "invoice.json", "offer.json"]
    assert os.path.exists(os.path.join(lib, "README.md"))
    assert library.missing(prof) == []
    out = tmp_path / "in"
    library.main(["--dir", lib, "new", "invoice", "--date", "2026-11-24", "--out", str(out)])
    made = os.listdir(out)
    assert len(made) == 1 and made[0].startswith("2026-11-24_invoice")
    assert json.load(open(out / made[0], encoding="utf-8"))["date"] == "2026-11-24"


def test_init_never_overwrites_edits(tmp_path):
    cfg, lib = cfg_file(tmp_path, DEMO), str(tmp_path / "lib")
    library.main(["--config", cfg, "--dir", lib, "init"])
    tpl = os.path.join(lib, "templates", "offer.json")
    with open(tpl, "w", encoding="utf-8") as f:
        f.write('{"edited": true}')
    comp = os.path.join(lib, "company.json")
    data = json.load(open(comp, encoding="utf-8")); data["phone"] = "+371 00000000"
    json.dump(data, open(comp, "w", encoding="utf-8"))
    library.main(["--config", cfg, "--dir", lib, "init"])
    assert json.load(open(tpl, encoding="utf-8")) == {"edited": True}
    assert json.load(open(comp, encoding="utf-8"))["phone"] == "+371 00000000"


def test_check_lists_missing(tmp_path):
    cfg = cfg_file(tmp_path, {"company": {"name": "Demo SIA"}})
    lib = str(tmp_path / "lib")
    library.main(["--config", cfg, "--dir", lib, "init"])
    prof = json.load(open(os.path.join(lib, "company.json"), encoding="utf-8"))
    assert set(library.missing(prof)) == {"reg_no", "address", "bank", "iban"}


def test_library_profile_draws_a_document(tmp_path, monkeypatch):
    pytest.importorskip("reportlab")
    import documents
    cfg, lib = cfg_file(tmp_path, DEMO), str(tmp_path / "lib")
    library.main(["--config", cfg, "--dir", lib, "init"])
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["documents.py", "--seller", os.path.join(lib, "company.json"),
                                      "--doc", os.path.join(FX, "invoice_lv.json"), "--out", str(out)])
    documents.main()
    assert any(n.endswith(".pdf") for n in os.listdir(out))
