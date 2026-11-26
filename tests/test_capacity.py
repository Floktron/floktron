# -*- coding: utf-8 -*-
"""Capacity check (breath): thresholds, the breath table points at real scripts, read-only, no network."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import capacity_check as cc  # noqa: E402


def marks(**kw):
    f = {"python": "3.12.0", "cores": 8, "ram_gb": 16, "disk_free_gb": 50, **kw}
    return {r[1]: r[0] for r in cc.judge(f)}


def test_thresholds():
    assert set(marks().values()) == {cc.OK}
    assert marks(python="3.9.1")["Python"] == cc.BAD
    assert marks(cores=2)["Processor cores"] == cc.WARN
    assert marks(ram_gb=6)["Memory"] == cc.WARN
    assert marks(ram_gb=2)["Memory"] == cc.BAD
    assert marks(ram_gb=None)["Memory"] == cc.INFO
    assert marks(disk_free_gb=3)["Free disk"] == cc.WARN
    assert marks(disk_free_gb=0.5)["Free disk"] == cc.BAD


def test_breath_scripts_exist():
    for _task, scripts, _ai in cc.BREATH:
        for s in scripts.split(","):
            assert os.path.exists(os.path.join(ROOT, "scripts", s.strip())), s


def test_breath_doc_has_every_row():
    doc = open(os.path.join(ROOT, "docs", "BREATH.md"), encoding="utf-8").read()
    for task, _s, _ai in cc.BREATH:
        assert task in doc


def test_facts_shape():
    f = cc.facts()
    assert {"system", "cores", "ram_gb", "disk_free_gb", "python"} <= set(f)


def test_read_only_and_offline():
    src = open(os.path.join(ROOT, "scripts", "capacity_check.py"), encoding="utf-8").read()
    for bad in ("urllib", "requests", "socket", "http.client", "os.remove", "shutil.rmtree", "smtplib"):
        assert bad not in src, bad
    cmds = re.findall(r"run\(\[([^\]]*)\]", src)
    assert cmds == ['"sysctl", "-n", "hw.memsize"'], cmds
    assert not re.search(r"open\([^)]*['\"]w", src.split("def main")[0]), "writes only in main (the report)"


def test_variants_say_what_fits():
    big = {"python": "3.12.0", "cores": 8, "ram_gb": 16, "disk_free_gb": 50}
    assert {m for _n, m in cc.variants(big)} == {cc.OK}
    small = dict(big, cores=2, ram_gb=4, disk_free_gb=3)
    v = dict(cc.variants(small))
    assert v[cc.VARIANTS[0][0]] == cc.OK and v[cc.VARIANTS[2][0]] == cc.WARN and v[cc.VARIANTS[3][0]] == cc.OK
    assert {m for _n, m in cc.variants(dict(big, python="3.9.1"))} == {cc.BAD}


def test_variants_are_in_requirements_doc():
    doc = open(os.path.join(ROOT, "docs", "REQUIREMENTS.md"), encoding="utf-8").read()
    for name, _need in cc.VARIANTS:
        assert name in doc, name
