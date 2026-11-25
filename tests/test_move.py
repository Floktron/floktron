# -*- coding: utf-8 -*-
"""Move and backup (scripts/move.py): offline checks on FICTIONAL data only (TEST · FICTIONAL — Demo SIA).
No real company, no real mailbox; every password and token below is made up."""
import json
import os
import shutil
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import move  # noqa: E402

pyzipper = pytest.importorskip("pyzipper")

PW = "TEST-fictional-pass-1"
FAKE_TG = "123456789:" + "A" * 35                     # made-up Telegram token shape
CFG = f"""company: {{name: "TEST Demo SIA", language: en, timezone: Europe/Riga, country: LV}}
mail: {{provider: gmail, user: demo@example.com, password_env: FLOKTRON_MAIL_PASSWORD, manager_address: boss@example.com,
       app_password: abcd-efgh-ijkl-mnop}}
telegram: {{enabled: true, token_env: FLOKTRON_TG_TOKEN, keychain_service: FLOKTRON_TG_BOT, manager_chat_ids: [12345],
           note: "{FAKE_TG}"}}
calendar: {{enabled: true, url: "https://calendar.example/private.ics", url_env: FLOKTRON_CAL_URL}}
storage: {{root: "/Users/someone-old/Cloud/FLOKTRON"}}
rays: [{{id: L1, name: Sales, email: anna@example.com, phone: "+371 20000000"}}, {{id: L2, name: Stock}}]
snapshot: {{locked_words: ["TEST secret glue"]}}
move: {{backup: true, keep: 2, password_env: FLOKTRON_MOVE_PASSWORD}}
"""


def make_root(tmp, name="old"):
    r = tmp / name
    for d in ("prompts", "agents", "templates"):
        shutil.copytree(os.path.join(ROOT, d), r / d, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(os.path.join(ROOT, "CHANGELOG.md"), r / "CHANGELOG.md")
    (r / "config").mkdir()
    (r / "data" / "library").mkdir(parents=True)
    (r / "data" / "context").mkdir()
    (r / "data" / "audio").mkdir()
    (r / "data" / "replies").mkdir()
    return r


def fill(r):
    import openpyxl
    import safe_xlsx  # noqa: F401
    (r / "config" / "config.yaml").write_text(CFG, encoding="utf-8")
    (r / "config" / "bot_flow.yaml").write_text("start: hello  # TEST\n", encoding="utf-8")
    (r / "data" / "library" / "company.json").write_text(json.dumps({"name": "TEST Demo SIA", "reg_no": "40000000000"}),
                                                         encoding="utf-8")
    (r / "data" / "context" / "rules.md").write_text("TEST · FICTIONAL: answer customers in Latvian first.\n", encoding="utf-8")
    (r / "data" / ".env").write_text("FLOKTRON_MAIL_PASSWORD=fake\n", encoding="utf-8")
    (r / "data" / "notes.txt").write_text(f"bot {FAKE_TG}\n", encoding="utf-8")
    (r / "data" / "audio" / "pulse_2026-11-25.m4a").write_bytes(b"\x00TEST audio")
    (r / "data" / "replies" / "r1.json").write_text('{"from": "anna@example.com"}', encoding="utf-8")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rays"
    ws.append(["ID", "Ray", "Responsible", "E-mail / messenger", "Active"])
    ws.append(["L1", "Sales", "Anna TEST", "anna@example.com", "Yes"])
    wb.create_sheet("Mail").append(["From", "Subject"])
    wb.save(r / "data" / "floktron_base.xlsx")
    with open(r / "prompts" / "50_invoices.md", "a", encoding="utf-8") as f:
        f.write("\nTEST company rule: invoices over 1000 EUR go to the director.\n")


@pytest.fixture
def old(tmp_path):
    r = make_root(tmp_path)
    fill(r)
    return r


def inner(path, pw=PW):
    with pyzipper.AESZipFile(path) as z:
        z.setpassword(pw.encode())
        return {i.filename.split("/", 1)[1]: z.read(i) for i in z.infolist()}


def test_pack_has_no_secrets_and_lists_them(old, tmp_path):
    path, m = move.pack(str(old), str(tmp_path / "out"), password=PW)
    files = inner(path)
    blob = b"".join(files.values())
    for s in (b"abcd-efgh-ijkl-mnop", FAKE_TG.encode(), b"private.ics", b"FLOKTRON_MAIL_PASSWORD=fake"):
        assert s not in blob
    names = {s["name"] for s in m["secrets"]}
    assert {"FLOKTRON_MAIL_PASSWORD", "FLOKTRON_TG_TOKEN", "FLOKTRON_TG_BOT", "FLOKTRON_CAL_URL",
            "FLOKTRON_MOVE_PASSWORD"} <= names
    skipped = {s["path"] for s in m["skipped"]}
    assert {"data/.env", "data/notes.txt"} <= skipped
    for k in ("MOVE.md", "MANIFEST.json", "COMPANY_CONTEXT.md", "SECRETS_TO_ENTER.md", "SCHEDULE.md", "AGENTS.md",
              "config/config.yaml", "config/bot_flow.yaml", "data/floktron_base.xlsx", "data/library/company.json"):
        assert k in files, k
    assert b"answer customers in Latvian first" in files["COMPANY_CONTEXT.md"]
    assert b"backup" in files["SCHEDULE.md"]                       # move.backup: true adds the weekly job
    assert "custom/prompts/50_invoices.md" in files                 # the company's own change travels
    assert "custom/prompts/00_setup_wizard.md" not in files         # unchanged shipped files do not
    assert os.path.exists(path[:-4] + "_READ_ME.txt") and PW not in open(path[:-4] + "_READ_ME.txt").read()


def test_archive_needs_the_password(old, tmp_path):
    path, _ = move.pack(str(old), str(tmp_path / "out"), password=PW)
    with zipfile.ZipFile(path) as z:                                # AES: names visible, content not
        assert all(i.flag_bits & 0x1 for i in z.infolist())
    with pytest.raises(move.MoveError, match="password"):
        move.check(path, None, str(old))
    with pytest.raises(move.MoveError, match="wrong password"):
        move.check(path, "not-the-password-1", str(old))
    assert move.check(path, PW, str(old))["ok"]


def test_unpack_on_new_computer(old, tmp_path):
    path, m = move.pack(str(old), str(tmp_path / "out"), password=PW)
    new = make_root(tmp_path, "new")
    (new / "config" / "config.yaml").write_text("company: {name: before}\n", encoding="utf-8")
    (new / "data" / "old_here.txt").write_text("keep me", encoding="utf-8")
    r = move.unpack(path, PW, str(new))
    assert (new / "data" / "floktron_base.xlsx").exists()
    assert "TEST Demo SIA" in (new / "config" / "config.yaml").read_text(encoding="utf-8")
    aside = r["aside"]
    assert open(os.path.join(aside, "old_here.txt")).read() == "keep me"               # nothing deleted
    assert "before" in open(os.path.join(aside, "config.yaml")).read()
    after = open(r["after"], encoding="utf-8").read()
    assert "FLOKTRON_MAIL_PASSWORD" in after and "someone-old" in after and "off" in after.lower()
    live = (new / "prompts" / "50_invoices.md").read_text(encoding="utf-8")
    assert "TEST company rule" in live                                                   # same version → in place
    assert (new / "prompts" / "50_invoices.md.shipped").exists()
    assert r["restored"] == ["prompts/50_invoices.md"]
    assert (new / "data" / "move" / "last" / "COMPANY_CONTEXT.md").exists()


def test_other_version_never_overwrites_prompts(old, tmp_path):
    path, _ = move.pack(str(old), str(tmp_path / "out"), password=PW)
    new = make_root(tmp_path, "new")
    (new / "CHANGELOG.md").write_text("# Changelog\n\n## 9.9.9 — later\n", encoding="utf-8")
    r = move.unpack(path, PW, str(new))
    assert "TEST company rule" not in (new / "prompts" / "50_invoices.md").read_text(encoding="utf-8")
    assert (new / "data" / "move" / "restored_custom" / "prompts" / "50_invoices.md").exists()
    assert "compare" in open(r["after"], encoding="utf-8").read()


def test_handover_removes_people(old, tmp_path):
    import openpyxl
    path, m = move.pack(str(old), str(tmp_path / "out"), profile="handover", password=PW)
    files = inner(path)
    cfg = files["config/config.yaml"].decode()
    assert "anna@example.com" not in cfg and "boss@example.com" not in cfg and "20000000" not in cfg
    assert "12345" not in cfg
    import io
    wb = openpyxl.load_workbook(io.BytesIO(files["data/floktron_base.xlsx"]))
    assert "Mail" not in wb.sheetnames
    rows = list(wb["Rays"].iter_rows(values_only=True))
    assert rows[1][0] == "L1" and rows[1][2] is None and rows[1][3] is None
    assert not any(k.startswith("data/replies/") for k in files)
    assert path.endswith("_handover.zip")


def test_tampered_or_unsafe_archive_is_refused(old, tmp_path):
    path, _ = move.pack(str(old), str(tmp_path / "out"), password=None)            # test only: no password
    files = inner(path, "")
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        for k, v in files.items():
            z.writestr(f"{move.TOP}/{k}", v + b"x" if k == "data/library/company.json" else v)
    r = move.check(str(bad), None, str(old))
    assert not r["ok"] and "data/library/company.json" in r["bad"]
    with pytest.raises(move.MoveError, match="damaged"):
        move.unpack(str(bad), None, str(make_root(tmp_path, "n2")))
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr(f"{move.TOP}/MANIFEST.json", files["MANIFEST.json"])
        z.writestr(f"{move.TOP}/../../outside.txt", b"x")
    with pytest.raises(move.MoveError, match="unsafe path"):
        move.check(str(evil), None, str(old))


def test_backup_needs_a_password_and_keeps_the_last(old, tmp_path, monkeypatch):
    import datetime as dt
    monkeypatch.delenv("FLOKTRON_MOVE_PASSWORD", raising=False)
    with pytest.raises(move.MoveError, match="backup password not set"):
        move.backup(str(old))
    monkeypatch.setenv("FLOKTRON_MOVE_PASSWORD", PW)
    for d in range(3):
        move.backup(str(old), now=dt.datetime(2026, 11, 1 + d, 19, 30))
    out = old / "data" / "backups"                                   # storage.root does not exist here
    zips = sorted(f for f in os.listdir(out) if f.endswith(".zip"))
    assert len(zips) == 2 and "2026-11-03" in zips[-1]                # keep: 2
    path, m = move.pack(str(old), str(tmp_path / "o2"), password=PW)
    assert not any(f["path"].startswith("data/backups/") for f in m["files"])   # archives are never packed again


def test_no_media_and_short_password(old, tmp_path, monkeypatch):
    path, m = move.pack(str(old), str(tmp_path / "out"), password=PW, media=False)
    assert "data/audio/pulse_2026-11-25.m4a" in {s["path"] for s in m["skipped"]}
    monkeypatch.delenv("FLOKTRON_MOVE_PASSWORD", raising=False)
    monkeypatch.setattr(move.getpass, "getpass", lambda *_: "short")
    with pytest.raises(move.MoveError, match="too short"):
        move.ask_password()


def test_schedule_adds_backup_only_when_switched_on(tmp_path):
    sys.path.insert(0, os.path.join(ROOT, "scripts", "install"))
    import schedule as sch
    r = tmp_path / "r"
    (r / "config").mkdir(parents=True)
    (r / "config" / "config.yaml").write_text("move: {backup: false}\n", encoding="utf-8")
    assert "backup" not in sch.load(str(r))
    (r / "config" / "config.yaml").write_text("move: {backup: true}\n", encoding="utf-8")
    assert sch.load(str(r))["backup"] == "Sun 19:30"
    fixed, _ = sch.jobs(sch.load(str(r)))
    assert ("backup", [0], 19, 30) in fixed


def test_dashboard_shows_a_failed_backup(tmp_path):
    import datetime as dt
    import dashboard
    (tmp_path / "run.log").write_text("\n=== 2026-11-22 19:30 backup\n❌ backup password not set\n--- exit 2\n", encoding="utf-8")
    D = dashboard.collect({"company": {"language": "en"}}, data=str(tmp_path), now=dt.datetime(2026, 11, 25, 8, 0))
    p = [x for x in D["pulse"] if x["name"] == "Backup"]
    assert p and p[0]["st"] == "bad" and "MOVE" in p[0]["fix"]
