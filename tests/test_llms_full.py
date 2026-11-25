# -*- coding: utf-8 -*-
"""llms-full.txt must match its sources — run scripts/build_llms_full.py after changing docs."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_llms_full  # noqa: E402


def test_llms_full_is_current():
    with open(os.path.join(ROOT, "llms-full.txt"), encoding="utf-8") as f:
        assert f.read() == build_llms_full.build(), "run: python3 scripts/build_llms_full.py"


def test_start_is_current():
    with open(os.path.join(ROOT, "START.md"), encoding="utf-8") as f:
        assert f.read() == build_llms_full.build_start(), "run: python3 scripts/build_llms_full.py"


def test_shipped_prompt_hashes_are_current():
    with open(os.path.join(ROOT, "templates", "shipped_prompts.json"), encoding="utf-8") as f:
        assert f.read() == build_llms_full.build_shipped(), "run: python3 scripts/build_llms_full.py"
