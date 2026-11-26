# -*- coding: utf-8 -*-
"""FLOKTRON safety checks — run with the other tests:  pytest -q
They guard the rules in SECURITY.md so a later change cannot quietly break them."""
import os
import re
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
sys.path.insert(0, S)

import safe_xlsx  # noqa: E402

FORBIDDEN = [r"\beval\(", r"\bexec\(", r"os\.system\(", r"shell\s*=\s*True", r"\bpickle\b",
             r"__import__\(", r"curl[^\n]*\|\s*(ba|z)?sh", r"wget[^\n]*\|\s*(ba|z)?sh"]


def _code_files():
    for d, _, files in os.walk(ROOT):
        if any(x in d for x in (".git", "__pycache__", os.sep + "tests", os.sep + "data")):
            continue
        for f in files:
            if f.endswith((".py", ".sh", ".command", ".ps1")):
                yield os.path.join(d, f)


def test_no_dangerous_calls():
    bad = []
    for p in _code_files():
        txt = open(p, encoding="utf-8", errors="ignore").read()
        for pat in FORBIDDEN:
            if re.search(pat, txt):
                bad.append(f"{os.path.relpath(p, ROOT)}: {pat}")
    assert not bad, "dangerous call found: " + "; ".join(bad)


def test_outside_text_never_becomes_formula(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["=HYPERLINK(\"http://bad.example\",\"click\")", "normal text", "- not done", "="])
    p = tmp_path / "x.xlsx"
    wb.save(p)  # patched save from safe_xlsx
    c = openpyxl.load_workbook(p).active
    assert c["A1"].data_type == "s" and str(c["A1"].value).startswith("'=")
    assert c["B1"].value == "normal text" and c["C1"].value == "- not done"
    assert c["D1"].value == "="  # FLOKTRON's own "same ray" marker stays


def test_every_writing_script_uses_safe_xlsx():
    missing = [f for f in os.listdir(S) if f.endswith(".py") and f != "safe_xlsx.py"
               and "import openpyxl" in open(os.path.join(S, f), encoding="utf-8").read()
               and "import safe_xlsx" not in open(os.path.join(S, f), encoding="utf-8").read()]
    assert not missing, "scripts writing .xlsx without safe_xlsx: " + ", ".join(missing)


def test_secrets_and_company_data_are_ignored_by_git():
    gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
    for item in ("config/config.yaml", ".env", "data/*", "*.eml"):
        assert item in gi, f"{item} must be in .gitignore"


def test_no_password_or_token_in_repo():
    pat = re.compile(r"(password|passwd|token|api[_-]?key|secret)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]", re.I)
    hits = []
    for d, _, files in os.walk(ROOT):
        if any(x in d for x in (".git", "__pycache__", os.sep + "data")):
            continue
        for f in files:
            if f.endswith((".py", ".md", ".yaml", ".yml", ".txt", ".sh", ".command", ".ps1")):
                p = os.path.join(d, f)
                if f == "config.yaml":
                    continue
                if pat.search(open(p, encoding="utf-8", errors="ignore").read()):
                    hits.append(os.path.relpath(p, ROOT))
    assert not hits, "possible secret in: " + ", ".join(hits)


def test_agent_entry_files_point_to_agents_md():
    for f in ("CLAUDE.md", "GEMINI.md", os.path.join(".github", "copilot-instructions.md")):
        p = os.path.join(ROOT, f)
        assert os.path.exists(p), f"{f} missing"
        assert "AGENTS.md" in open(p, encoding="utf-8").read(), f"{f} must point to AGENTS.md"
    a = open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8").read()
    assert "data, not instructions" in a


def test_every_prompt_and_role_says_outside_text_is_data():
    """Prompt-injection guard: every prompt and every ready role must keep the 'outside text is data' rule."""
    import glob, re
    files = [f for f in glob.glob(os.path.join(ROOT, "prompts", "*.md")) if not f.endswith("README.md")]
    files += glob.glob(os.path.join(ROOT, "agents", "*", "agent.md"))
    assert files
    for f in files:
        t = open(f, encoding="utf-8").read()
        assert re.search(r"data, (not|never) instructions", t), f"{os.path.relpath(f, ROOT)} lost the 'data, not instructions' rule"
