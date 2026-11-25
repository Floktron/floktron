# -*- coding: utf-8 -*-
"""Supply chain watch: offline checks (no network). Fixtures copy the real shape of Yahoo chart JSON and Google News RSS."""
import json
import os
import subprocess
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
sys.path.insert(0, S)
import supply_watch as sw  # noqa: E402

CHART = json.dumps({"chart": {"result": [{"meta": {"currency": "USD"},
    "timestamp": [1794355200, 1794441600, 1794528000, 1794787200, 1794873600, 1794960000, 1795046400],
    "indicators": {"quote": [{"close": [1.1169, 1.1095, 1.1050, 1.1025, None, 1.0993, 1.0997]}]}}]}})
RSS = ("<rss><channel><item><title>Producer X halts production after fire at plant - Paper</title>"
       "<link>https://news.example/a?oc=5</link><pubDate>Thu, 19 Nov 2026 10:00:00 GMT</pubDate></item>"
       "<item><title><![CDATA[Market closes flat &amp; calm]]></title><link>https://news.example/b</link>"
       "<pubDate>Thu, 19 Nov 2026 09:00:00 GMT</pubDate></item></channel></rss>")


def test_parse_chart_skips_missing_closes():
    day, last, d1, d5, cur = sw.parse_chart(CHART)
    assert (day, last, cur) == ("2026-11-19", 1.0997, "USD")
    assert d1 == round((1.0997 / 1.0993 - 1) * 100, 1)
    assert d5 == round((1.0997 / 1.1169 - 1) * 100, 1)   # five valid closes back, the empty one is skipped


def test_price_status_thresholds_both_directions():
    assert sw.price_status(0.5, 2.0, 5, 10) == "green"
    assert sw.price_status(-6.0, -4.0, 5, 10) == "yellow"
    assert sw.price_status(1.0, -12.0, 5, 10) == "red"
    assert sw.price_status(None, None, 5, 10) == "none"


def test_news_words_and_rss():
    items = sw.parse_rss(RSS)
    assert items[1][0] == "Market closes flat & calm"
    assert sw.news_status(items[0][0]) == "red"
    assert sw.news_status(items[1][0]) == "green"
    assert sw.news_status("Supplier announces price increase from January") == "yellow"


def test_page_fingerprint_ignores_scripts_and_spaces():
    a = sw.page_text("<html><script>var t=1</script><p>Our  products</p>\n<p>Prices</p></html>")
    b = sw.page_text("<html><script>var t=2</script><p>Our products</p><p>Prices</p></html>")
    assert a == b == "Our products Prices"
    assert sw.fingerprint(a) == sw.fingerprint(b)


def test_lang_region():
    assert sw.lang_region("en") == ("en", "US")
    assert sw.lang_region("lv") == ("lv", "LV")
    assert sw.lang_region("en-GB") == ("en", "GB")


def test_radar_has_watch_sheets_and_add_watch(tmp_path):
    out = tmp_path / "radar.xlsx"
    none = str(tmp_path / "none.yaml")
    subprocess.run([sys.executable, os.path.join(S, "radar_create.py"), "--config", none, "--out", str(out)], check=True)
    wb = openpyxl.load_workbook(out)
    assert {"Watchlist", "Watch_log"} <= set(wb.sheetnames)
    del wb["Watchlist"], wb["Watch_log"]
    wb.save(out)
    subprocess.run([sys.executable, os.path.join(S, "radar_create.py"), "--config", none, "--out", str(out),
                    "--add-watch"], check=True)
    wb = openpyxl.load_workbook(out)
    assert "Watchlist" in wb.sheetnames
    again = subprocess.run([sys.executable, os.path.join(S, "radar_create.py"), "--config", none, "--out", str(out),
                            "--add-watch"], capture_output=True, text=True, encoding="utf-8")
    assert "already exists" in (again.stdout + again.stderr)


def test_no_order_or_send_code():
    src = open(os.path.join(S, "supply_watch.py"), encoding="utf-8").read()
    for bad in ("smtplib", "subprocess", "POST", "sendMessage"):
        assert bad not in src


def test_second_run_same_day_adds_nothing(tmp_path):
    out = tmp_path / "radar.xlsx"
    subprocess.run([sys.executable, os.path.join(S, "radar_create.py"), "--config", str(tmp_path / "n.yaml"),
                    "--out", str(out)], check=True)
    sw.fetch = lambda url, timeout=25: CHART if "finance.yahoo" in url else RSS
    old = sys.argv
    try:
        for _ in range(2):
            sys.argv = ["x", "--radar", str(out), "--config", str(tmp_path / "n.yaml")]
            sw.main()
    finally:
        sys.argv = old
    wb = openpyxl.load_workbook(out)
    log = [r for r in wb["Watch_log"].iter_rows(min_row=4, values_only=True) if r[0]]
    keys = [(r[1], r[3]) for r in log]
    assert keys and len(keys) == len(set(keys))
