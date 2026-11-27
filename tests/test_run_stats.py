# -*- coding: utf-8 -*-
"""Run numbers (scripts/run_stats.py): what counts as ok / failed / recovered, on a FICTIONAL run log."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import run_stats  # noqa: E402

LOG = """
=== 2026-11-08 07:00 morning
sent 3
--- exit 0
=== 2026-11-08 07:30 collect
--- exit 1
=== 2026-11-08 07:30 mail
--- exit 0
=== 2026-11-08 08:00 collect
--- exit 0
=== 2026-11-08 08:30 gateways
--- gateways: timeout
2026-11-08 08:31 collect: skipped — another FLOKTRON run is working
=== 2026-11-09 07:00 morning
--- exit 2
=== 2026-11-10 07:00 news
started
"""


def test_counts_and_definitions(tmp_path):
    runs, skipped = run_stats.parse(LOG.splitlines())
    s = run_stats.stats(runs, skipped)
    assert (s["runs"], s["ok"], s["failed"], s["unfinished"], s["skipped"]) == (7, 3, 3, 1, 1)
    assert s["recovered"] == 1           # collect 07:30 failed, 08:00 ok
    assert s["not_recovered"] == 2       # gateways timeout and morning 09.11: no later ok run
    assert s["failed_pct"] == 50.0       # 3 of 6 finished runs; the unfinished one is not counted as ok
    assert s["from"].strftime("%d.%m") == "08.11" and s["to"].strftime("%d.%m") == "10.11"
    t = run_stats.text(s)
    assert "08.11.2026–10.11.2026" in t and "not that every letter was read" in t


def test_period_and_json(tmp_path, capsys):
    p = tmp_path / "run.log"
    p.write_text(LOG, encoding="utf-8")
    out = tmp_path / "run_stats.json"
    assert run_stats.main(["--log", str(p), "--since", "2026-11-09", "--json", str(out)]) == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["runs"] == 2 and d["from"].startswith("2026-11-09") and d["counted"] and d["source"] == "data/run.log"
