# -*- coding: utf-8 -*-
"""Ready AI roles (agents/): every path a role names exists, config sections exist, wizard steps exist."""
import glob
import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = sorted(glob.glob(os.path.join(ROOT, "agents", "*", "role.yaml")))


def load(p):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_two_ready_roles():
    names = {load(p)["role"] for p in ROLES}
    assert {"secretary", "operations-director"} <= names


def test_paths_exist():
    for p in ROLES:
        r = load(p)
        for key in ("scripts", "prompts", "docs"):
            for rel in r[key]:
                assert os.path.exists(os.path.join(ROOT, rel)), f"{p}: {rel}"
        folder = os.path.dirname(p)
        for f in ("ROLE.md", "agent.md"):
            assert os.path.exists(os.path.join(folder, f))


def test_config_sections_exist():
    cfg = load(os.path.join(ROOT, "config", "config.example.yaml"))
    for p in ROLES:
        for sec in load(p)["config"]:
            assert sec in cfg, f"{p}: config section {sec}"


def test_wizard_steps_exist():
    wiz = open(os.path.join(ROOT, "prompts", "00_setup_wizard.md"), encoding="utf-8").read()
    steps = set(re.findall(r"^## (\d+[a-z]?)\.", wiz, re.M))
    for p in ROLES:
        for s in load(p)["wizard_steps"]:
            assert s in steps, f"{p}: wizard step {s}"


def test_roles_listed_in_readme():
    idx = open(os.path.join(ROOT, "agents", "README.md"), encoding="utf-8").read()
    for p in ROLES:
        assert os.path.basename(os.path.dirname(p)) + "/ROLE.md" in idx
