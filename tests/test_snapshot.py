# -*- coding: utf-8 -*-
"""Company snapshot: profiles, statuses, the lock and the PDF/JSON pair — on the FICTIONAL Demo SIA only."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import snapshot as snap  # noqa: E402

DAY = "2026-11-22"


@pytest.fixture()
def demo(tmp_path):
    base = tmp_path / "base.xlsx"
    snap.demo_base(str(base), DAY)
    return snap.demo_facts(DAY), snap.read_base(str(base), DAY)


def run(tmp_path, demo, profile, lang="en", plus=(), minus=(), cfg=None):
    facts, rows = demo
    pdf, js = snap.snapshot(facts, rows, profile, lang, str(tmp_path / "out"), plus, minus, True, DAY, cfg or {})
    with open(js, encoding="utf-8") as f:
        return pdf, json.load(f), open(js, encoding="utf-8").read()


def items(doc):
    return {i["id"]: i for s in doc["sections"] for i in s["items"]}


def test_secret_internal_and_names_never_leave(tmp_path, demo):
    for profile in snap.PROFILES:
        _, doc, raw = run(tmp_path, demo, profile)
        assert "how" not in items(doc) and "competitors" not in items(doc)
        for word in ("never exported", "internal list", "HIDDEN CLIENT", "HIDDEN SITE"):
            assert word not in raw, (profile, word)


def test_tax_profile_has_only_public_and_deal(tmp_path, demo):
    _, doc, _ = run(tmp_path, demo, "tax")
    assert {i["status"] for i in items(doc).values()} <= {"PUBLIC", "DEAL"}
    assert "unit_cost" not in items(doc) and "plan" not in items(doc)  # ESTIMATE and SCENARIO stay out
    assert "iban" in items(doc)


def test_no_bank_and_valuation_switches(tmp_path, demo):
    _, partner, _ = run(tmp_path, demo, "partner")
    assert "iban" in items(partner) and "valuation" not in items(partner)
    _, no_bank, _ = run(tmp_path, demo, "no_bank")
    assert "iban" not in items(no_bank) and "balance" not in items(no_bank)
    _, plus, _ = run(tmp_path, demo, "partner", plus=["valuation"], minus=["bank"])
    assert "valuation" in items(plus) and "iban" not in items(plus)


def test_public_profile_only_public(tmp_path, demo):
    _, doc, _ = run(tmp_path, demo, "public")
    assert {i["status"] for i in items(doc).values()} == {"PUBLIC"}
    assert {s["id"] for s in doc["sections"]} <= {"company", "people", "product_ip"}


def test_base_counts_only(tmp_path, demo):
    _, doc, _ = run(tmp_path, demo, "partner")
    it = items(doc)
    assert it["inv_total"]["value"] == "2 / 363,00 EUR"
    assert it["inv_open"]["value"] == "1 / 242,00 EUR"
    assert it["purchases"]["value"] == "2 / 1" and it["rentals"]["value"] == "2 / 1"
    assert it["stock:D-RA"]["status"] == "ESTIMATE"


def test_lock_stops_and_writes_nothing(tmp_path, demo):
    facts, rows = demo
    facts["facts"][0]["value"] = "Recipe: 40 g per unit"
    with pytest.raises(snap.Locked):
        snap.snapshot(facts, rows, "public", "en", str(tmp_path / "locked"), test=True, as_of=DAY)
    assert not (tmp_path / "locked").exists()
    facts, rows = snap.demo_facts(DAY), []
    with pytest.raises(snap.Locked):  # own words from config.yaml
        snap.snapshot(facts, rows, "public", "en", str(tmp_path / "own"), test=True, as_of=DAY,
                      cfg={"snapshot": {"locked_words": ["DEMOBRAND"]}})


def test_unknown_status_and_sensitivity_are_safe():
    f = snap.fact("finance", "x", "X", "1", "maybe", "s", DAY, "whatever")
    assert f["status"] == "ESTIMATE" and f["sensitivity"] == "secret"
    assert snap.fact("finance", "y", "Y", "1", "СДЕЛКА", "s", DAY)["status"] == "DEAL"
    with pytest.raises(ValueError):
        snap.fact("nowhere", "z", "Z", "1", "PUBLIC", "s", DAY)


def test_pdf_and_json_are_one_pair(tmp_path, demo):
    pytest.importorskip("reportlab")
    pdf, doc, _ = run(tmp_path, demo, "tax", "lv")
    assert doc["pdf"]["sha256"] == snap.sha256(pdf)
    assert doc["sections"][0]["title"] == "Uzņēmums" and doc["test_fictional"] is True
