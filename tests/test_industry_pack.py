# -*- coding: utf-8 -*-
"""Industry packs: a ready set of radar keywords, added without overwriting; editing from Telegram."""
import json
import os
import subprocess
import sys

import openpyxl
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
sys.path.insert(0, S)
sys.path.insert(0, os.path.join(S, "bot"))

import industry_pack as ip  # noqa: E402
import news_slice  # noqa: E402


def radar(tmp_path, langs=("lv", "ru", "en")):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.safe_dump({"radar": {"languages": list(langs)}}), encoding="utf-8")
    out = tmp_path / "radar.xlsx"
    subprocess.run([sys.executable, os.path.join(S, "radar_create.py"), "--config", str(cfg), "--out", str(out)],
                   check=True, capture_output=True)
    return out


def test_every_pack_is_complete():
    packs = ip.list_packs()
    assert any(p["id"] == "construction" for p in packs)
    for p in packs:
        assert p["prefix"] and len(p["questions"]) == 3
        for k in p["keywords"]:
            assert k["priority"] in ("A", "B") and k["lv"] and k["ru"] and k["en"], k
            assert '"' not in "".join(k[l] for l in ("lv", "ru", "en"))   # quotes break the stem matching
        a = sum(k["priority"] == "A" for k in p["keywords"])
        assert 5 <= a <= news_slice.QUERY_WORDS * news_slice.MAX_QUERIES - 6   # room left for competitors + own words


def test_pack_has_no_secrets_or_client_terms():
    text = open(os.path.join(ROOT, "templates", "industry", "construction.json"), encoding="utf-8").read().lower()
    for bad in ("семантическ", "semantic core", "koagu", "floki", "@", "pilot"):
        assert bad not in text, bad


def test_apply_adds_once_and_keeps_own_rows(tmp_path):
    out = radar(tmp_path)
    wb = openpyxl.load_workbook(out)
    wb["Keywords"].append(["K02", "Own", "mūsu vārds", "", "", "A", "", "", "mine"])
    pack = ip.load_pack("construction")
    got = ip.apply(wb, pack, "LV", "Rīga", ["Demo Būve SIA", "Test Celtnieks"])
    assert got["keywords"] == len(pack["keywords"]) + 1 and got["competitors"] == 2
    assert got["sources"] >= 4 and got["registry"] == 2 and got["watch"] == 2
    again = ip.apply(wb, pack, "LV", "Rīga", ["Demo Būve SIA"])
    assert all(v == 0 for v in again.values())             # nothing twice
    wb.save(out)
    wb = openpyxl.load_workbook(out)
    kw = news_slice.keywords(wb)
    assert "mūsu vārds" in kw["lv"] and "būvatļauja" in kw["lv"] and "Rīga būvniecība" in kw["lv"]
    assert "Demo Būve SIA" in kw["ru"] and "строительный тендер" in kw["ru"]
    assert "cementa cena" not in kw["lv"]                   # priority B — only the first run of the month
    players = [r[0] for r in wb["Players"].iter_rows(min_row=4, values_only=True)]
    assert "Test Celtnieks" in players


def test_language_without_translation_is_marked(tmp_path):
    out = radar(tmp_path, ("lv", "de"))
    wb = openpyxl.load_workbook(out)
    ip.apply(wb, ip.load_pack("construction"))
    comments = {r[-1] for r in wb["Keywords"].iter_rows(min_row=5, values_only=True) if r[0]}
    assert any("translate DE" in str(c) for c in comments)


def test_add_and_switch_off(tmp_path):
    out = radar(tmp_path)
    wb = openpyxl.load_workbook(out)
    assert ip.add_word(wb, "fasādes siltināšana").startswith("OW")
    assert ip.add_word(wb, "Fasādes  siltināšana") == ""     # same word again
    assert ip.add_word(wb, "=HYPERLINK(1)") == ""             # never a formula
    assert ip.switch_off(wb, "fasādes siltināšana")
    assert "fasādes siltināšana" not in news_slice.keywords(wb).get("lv", [])


def test_google_news_splits_long_lists():
    words = [f"word{i}" for i in range(20)]
    assert news_slice.google_query(words).count("OR") == news_slice.QUERY_WORDS - 1


def test_bot_words_commands(tmp_path):
    import telegram_bot as tb
    from test_bot import FakeApi, FLOW, msg
    out = radar(tmp_path)
    flow = yaml.safe_load(open(FLOW, encoding="utf-8"))
    api = FakeApi()
    b = tb.Bot(api, flow, {"manager_chat_ids": [999], "radar_file": str(out)}, tb.Store(data_dir=str(tmp_path)))
    b.handle(msg(999, "/addword jumta remonts"))
    b.handle(msg(999, "/words"))
    b.handle(msg(999, "/delword jumta remonts"))
    b.handle(msg(123, "/addword svešs vārds"))               # not a manager — never edits the radar
    t = api.texts(999)
    assert t[0].startswith("✅ Added") and "jumta remonts" in t[1] and t[2].startswith("⏸")
    words_now = [x[2] for x in ip.words(openpyxl.load_workbook(out), priority="")]
    assert "svešs vārds" not in words_now


def test_cli_list_and_show():
    r = subprocess.run([sys.executable, os.path.join(S, "industry_pack.py"), "show", "construction"],
                       capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0 and "būvatļauja" in r.stdout
    assert json.load(open(os.path.join(ROOT, "templates", "industry", "construction.json"), encoding="utf-8"))["id"] == "construction"
