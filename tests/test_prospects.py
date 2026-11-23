# -*- coding: utf-8 -*-
"""Prospects (scripts/prospects.py): offline checks on FICTIONAL procurement results and register rows
(tests/fixtures/prospects). Files are built at test time, the notice goes to an outbox folder - no network."""
import os
import subprocess
import sys

import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
FX = os.path.join(ROOT, "tests", "fixtures", "prospects")
sys.path.insert(0, S)
import prospects as pr  # noqa: E402

import importlib.util  # noqa: E402 — tests/fixtures/*/make_fixtures.py share a name; load this one by path
_spec = importlib.util.spec_from_file_location("prospects_fixtures", os.path.join(FX, "make_fixtures.py"))
make_fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_fixtures)

CFG = """company: {name: "Demo SIA (TEST · FICTIONAL)", language: en, timezone: Europe/Riga, phone: "+372 5555 0000"}
mail: {user: office@demo-sia.example.com, manager_address: boss@demo-sia.example.com}
prospects:
  enabled: true
  notify: mail
  best_customers: ["40000000099", "40000000098"]
  pitch: "Our dry reagent cleans the wash water right in the bucket (TEST)."
"""


@pytest.fixture
def world(tmp_path):
    eis, reg = make_fixtures.main(str(tmp_path / "fx"))
    radar = tmp_path / "radar.xlsx"
    subprocess.run([sys.executable, os.path.join(S, "radar_create.py"), "--config", str(tmp_path / "none.yaml"),
                    "--out", str(radar)], check=True, capture_output=True)
    wb = openpyxl.load_workbook(radar)
    wc = wb["Companies"]
    hr = next(r for r in range(1, 6) if wc.cell(r, 1).value == "Found")
    head = [wc.cell(hr, c).value for c in range(1, wc.max_column + 1)]
    for reg_no, name, status in (("40000000011", "SIA Jau grāmatā Demo (TEST)", "New"),
                                 ("40000000006", "SIA Stopa Demo (TEST)", "Do not contact")):
        line = {"Found": "2026-11-16", "Country": "LV", "Reg. no.": reg_no, "Name": name, "Work status": status}
        wc.append([line.get(h, "") for h in head])
    wb.save(radar)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(CFG, encoding="utf-8")

    def run(now, *extra):
        assert pr.main(["--config", str(cfg), "--radar", str(radar), "--eis-csv", eis, "--register-csv", reg,
                        "--outbox", str(tmp_path / "out"), "--now", now, "--test", *extra]) == 0
        wb = openpyxl.load_workbook(radar)
        return {r[3]: dict(zip(pr.HEAD, r)) for r in wb[pr.SHEET].iter_rows(min_row=2, values_only=True)}, wb

    return dict(tmp=tmp_path, radar=radar, run=run, eis=eis)


def test_only_fresh_building_contracts_of_live_lv_companies(world):
    rows, _ = world["run"]("2026-11-23 08:00")
    got = set(rows)
    assert {"40000000001", "40000000002", "40000000004", "40000000012"} <= got   # tiles, rebuild, big roads, finishing
    assert "40000000003" not in got   # design + supervision
    assert "300000001" not in got     # not a Latvian company
    assert "40000000005" not in got   # paper supply
    assert "40000000006" not in got   # "Do not contact" in Companies
    assert "40000000007" not in got   # terminated in the register
    assert "40000000008" not in got   # contract older than 180 days
    assert "40000000009" not in got   # under min_eur
    assert "40000000010" not in got   # contract ended
    assert "40000000011" not in got   # already in Companies
    assert "40000000099" not in got   # one of the best customers
    for r in rows.values():
        assert "PUBLIC" in r["Data status"] and "ESTIMATE" in r["Data status"]
        assert r["Comment"] == "TEST · FICTIONAL" and r["Status"] == "New"


def test_lookalike_score_and_why_now(world):
    rows, _ = world["run"]("2026-11-23 08:00")
    tiles, big, far = rows["40000000001"], rows["40000000004"], rows["40000000002"]
    assert tiles["Priority"] == 1 and "like your best customers" in tiles["Looks like"]
    assert tiles["Why now"].startswith("signed 10.11.2026 · 84 500 EUR")
    assert "works under way" in tiles["Why now"]
    assert big["Score"] < tiles["Score"] and far["Score"] < tiles["Score"]   # big contractor / other town, old firm
    assert rows["40000000012"]["Signed"] == "02.11.2026"                    # dd.mm.yyyy dates are read too
    assert tiles["Source"].startswith("https://")


def test_decisions_add_and_no_then_safe_rerun(world):
    rows, wb = world["run"]("2026-11-23 08:00")
    ws = wb[pr.SHEET]
    H = {h: i for i, h in enumerate(pr.HEAD)}
    for r in ws.iter_rows(min_row=2):
        if r[H["Reg. no."]].value == "40000000001":
            r[H["Decision"]].value = "Add"
        if r[H["Reg. no."]].value == "40000000004":
            r[H["Decision"]].value = "No"
    wb.save(world["radar"])
    rows2, wb2 = world["run"]("2026-11-24 08:00")
    assert len(rows2) == len(rows)                                   # nothing doubled
    assert rows2["40000000001"]["Status"] == "In Companies"
    assert rows2["40000000004"]["Status"] == "Not suitable"
    comp = [r for r in wb2["Companies"].iter_rows(values_only=True) if "40000000001" in [str(x) for x in r]]
    assert len(comp) == 1 and "New" in comp[0]
    draft = world["tmp"] / rows2["40000000001"]["Draft"]
    text = draft.read_text(encoding="utf-8")
    assert text.startswith("DRAFT · not sent") and "TEST · FICTIONAL" in text
    assert "finishing / renovation works" in text and "in the bucket (TEST)" in text
    assert "If you do not want to hear from us again" in text
    world["run"]("2026-11-25 08:00")
    comp = [r for r in openpyxl.load_workbook(world["radar"])["Companies"].iter_rows(values_only=True)
            if "40000000001" in [str(x) for x in r]]
    assert len(comp) == 1                                            # Add is done once


def test_notice_only_when_new(world):
    world["run"]("2026-11-23 08:00")
    out = world["tmp"] / "out"
    first = sorted(os.listdir(out))
    assert len(first) == 1
    text = (out / first[0]).read_text(encoding="utf-8")
    assert text.startswith("[TEST] FLOKTRON · new prospects") and "new prospects: " in text and "nothing is sent" in text
    world["run"]("2026-11-24 08:00")
    assert sorted(os.listdir(out)) == first                          # no new prospects - no new notice


def test_formula_in_csv_stays_text(world, tmp_path):
    import csv
    with open(world["eis"], encoding="utf-8") as f:
        data = list(csv.reader(f))
    row = list(data[1])
    row[0], row[1], row[17], row[18] = "99", '=HYPERLINK("http://x.example","click") remonts (TEST)', "=1+1", "40000000013"
    data.append(row)
    with open(world["eis"], "w", encoding="utf-8", newline="") as f:
        csv.writer(f, quoting=csv.QUOTE_ALL).writerows(data)
    world["run"]("2026-11-23 08:00")
    ws = openpyxl.load_workbook(world["radar"])[pr.SHEET]
    cells = [c for r in ws.iter_rows(min_row=2) for c in r if isinstance(c.value, str) and "1+1" in c.value or
             isinstance(c.value, str) and "HYPERLINK" in c.value]
    assert cells and all(c.data_type == "s" and not str(c.value).startswith("=") for c in cells)


def test_disabled_does_nothing(tmp_path, capsys):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("prospects: {enabled: false}\n", encoding="utf-8")
    assert pr.main(["--config", str(cfg), "--radar", str(tmp_path / "none.xlsx")]) == 0
    assert "enabled is false" in capsys.readouterr().out


def test_dashboard_card(world):
    import datetime
    import shutil
    import dashboard
    world["run"]("2026-11-23 08:00")
    shutil.copy(world["radar"], world["tmp"] / "floktron_radar.xlsx")
    D = dashboard.collect({"company": {"language": "lv"}}, str(world["tmp"]), now=datetime.datetime(2026, 11, 23, 9, 0))
    assert D["prospects"]["new"] >= 4 and D["prospects"]["top"] >= 1
    html = dashboard.render(D)
    assert "Jauni klienti: kāpēc tieši tagad" in html and "84 500 EUR" in html


def test_road_rebuild_is_networks_not_building():
    pc = dict(pr.DEFAULTS)
    assert pr.kind_of("Ielas pārbūve (TEST)", pc)[0] == "networks"
    assert pr.kind_of("Skolas ēkas pārbūve un kanalizācijas izbūve (TEST)", pc)[0] == "building"
    assert pr.kind_of("Sanmezglu remonts (TEST)", pc)[0] == "finishing"
    assert pr.kind_of("Būvprojekta izstrāde (TEST)", pc)[0] is None
