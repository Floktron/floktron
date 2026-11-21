# -*- coding: utf-8 -*-
"""Security check: read only, honest parsing, no secrets missed."""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import security_check as sc  # noqa: E402

SRC = open(os.path.join(ROOT, "scripts", "security_check.py"), encoding="utf-8").read()


def test_only_read_only_commands_are_started():
    # every command list in the file starts with an allowed program
    started = re.findall(r"run\(\[\s*\"([^\"]+)\"", SRC) + re.findall(r"run\(\[(fw),", SRC)
    assert started, "no commands found — the test lost track of the code"
    for name in started:
        if name == "fw":
            continue
        assert os.path.basename(name) in sc.READ_ONLY_COMMANDS, name
    with pytest.raises(ValueError):
        sc.run(["rm", "-rf", "/tmp/x"])


def test_never_changes_settings():
    words = [r"run\(\[\s*\"sudo", r"--setglobalstate",
             r"--setstealthmode", r"fdesetup\", \"enable", r"defaults\", \"write", r"\bSet-Mp", r"Enable-BitLocker",
             r"netsh\", \"advfirewall\", \"set", r"reg\", \"add", r"reg\", \"delete", r"spctl\", \"--master"]
    for w in words:
        assert not re.search(w, SRC), f"security_check.py must only read settings: {w}"


def test_open_ports_mac():
    out = """Active Internet connections (including servers)
tcp4       0      0  *.22                   *.*                    LISTEN
tcp46      0      0  *.5000                 *.*                    LISTEN
tcp4       0      0  127.0.0.1.631          *.*                    LISTEN
tcp6       0      0  ::1.5432               *.*                    LISTEN
tcp4       0      0  192.168.1.5.52000      17.1.2.3.443           ESTABLISHED"""
    assert sc.open_ports(out, "bsd") == {22, 5000}


def test_open_ports_windows():
    out = """  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING
  TCP    0.0.0.0:445            0.0.0.0:0              LISTENING
  TCP    127.0.0.1:5939         0.0.0.0:0              LISTENING
  TCP    [::]:3389              [::]:0                 LISTENING"""
    assert sc.open_ports(out, "win") == {135, 445, 3389}


def test_open_ports_linux():
    out = """LISTEN 0 128 0.0.0.0:22 0.0.0.0:*
LISTEN 0 4096 127.0.0.53%lo:53 0.0.0.0:*
LISTEN 0 511 [::]:80 [::]:*
LISTEN 0 128 *:11434 *:*"""
    assert sc.open_ports(out, "ss") == {22, 80, 11434}


def test_secret_detection():
    key = "pass" + "word"  # split so the repository-wide secret test does not flag this fake value
    assert sc.secret_in_text("mail:\n  " + key + ': "Xk29!pq7z"\n')
    assert sc.secret_in_text("FLOKTRON_TG_TOKEN=123456:AAH-real-looking-token\n")
    assert not sc.secret_in_text('mail:\n  password_env: "FLOKTRON_MAIL_PASSWORD"\n')
    assert not sc.secret_in_text("calendar:\n  busy_only: true\n")
    assert not sc.secret_in_text('  password: ""\n')


def test_report_is_saved_locally_only(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sc, "DATA", str(tmp_path))
    monkeypatch.setattr(sc, "run", lambda cmd, timeout=15: (None, ""))
    assert sc.main() == 0
    files = os.listdir(tmp_path)
    assert len(files) == 1 and files[0].startswith("security_check_")
    out = capsys.readouterr().out
    assert "changed nothing and sent nothing" in out
