# -*- coding: utf-8 -*-
"""Dashboard: builds from empty or filled data, escapes everything, loads nothing from the internet."""
import datetime
import os
import re
import shutil
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import dashboard as db  # noqa: E402

TODAY = datetime.date.today().isoformat()


def filled(tmp):
    shutil.copy(os.path.join(ROOT, "templates", "floktron_base_empty.xlsx"), tmp / "floktron_base.xlsx")
    shutil.copy(os.path.join(ROOT, "templates", "floktron_radar_empty.xlsx"), tmp / "floktron_radar.xlsx")
    wb = openpyxl.load_workbook(tmp / "floktron_base.xlsx")
    for name in ("Rays", "Tasks", "Receipts"):
        ws = wb[name]
        if ws.max_row > 1:
            ws.delete_rows(2, ws.max_row)
    wb["Rays"].append(["L1", "Sales", "Anna", "a@example.com", "en", "07:40", "Yes", "", ""])
    wb["Rays"].append(["L2", "Stock", "TEST box", "b@example.com", "en", "07:40", "Yes", "test", ""])
    wb["Tasks"].append(["T1", TODAY, "L1", "<script>alert(1)</script> call the client", "rule", "2020-01-01", "Sent", "", "", "L-1", ""])
    wb["Tasks"].append(["T2", TODAY, "L2", "TEST: count stock", "rule", TODAY, "Sent", "", "", "L-2", ""])
    wb["Receipts"].append([TODAY + " 08:01", "L-1", "L1", "Accepted", "", "a@example.com", "<m1>"])
    wb.save(tmp / "floktron_base.xlsx")
    with open(tmp / "run.log", "w", encoding="utf-8") as f:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"\n=== {now} collect\nok\n--- exit 0\n\n=== {now} news\nboom\n--- exit 1\n")


def test_empty_data_builds(tmp_path):
    assert db.main(["--config", str(tmp_path / "none.yaml"), "--data", str(tmp_path)]) == 0
    page = (tmp_path / "dashboard.html").read_text(encoding="utf-8")
    assert "FLOKTRON" in page and "</html>" in page


def test_filled_data_shows_rays_tasks_and_problems(tmp_path):
    filled(tmp_path)
    D = db.collect({}, str(tmp_path))
    assert {r["id"] for r in D["rays"]} == {"L1", "L2"}
    assert next(r for r in D["rays"] if r["id"] == "L1")["st"] == "ok"
    assert any(p["name"] == "News slice" and p["st"] == "bad" for p in D["pulse"])
    assert any("News slice" in a["text"] for a in D["attention"])
    assert D["tasks_test"] == 1 and len(D["tasks"]) == 1 and D["tasks"][0]["over"]


def test_everything_escaped_and_offline(tmp_path):
    filled(tmp_path)
    db.main(["--config", str(tmp_path / "none.yaml"), "--data", str(tmp_path)])
    page = (tmp_path / "dashboard.html").read_text(encoding="utf-8")
    assert "<script" not in page.lower()                       # task text is shown as text, page has no scripts
    assert "&lt;script&gt;" in page
    assert not re.search(r'(src|href)="(https?:)?//', page)     # no outside fonts, scripts or images
    assert "Content-Security-Policy" in page


def test_language_and_colours(tmp_path):
    filled(tmp_path)
    D = db.collect({"company": {"language": "ru", "name": "Тест"}}, str(tmp_path))
    page = db.render(D, {"main": "#123456; background:url(x)"})
    assert "пульт управления" in page and "--main:#123456;" in page and "url(x)" not in page
