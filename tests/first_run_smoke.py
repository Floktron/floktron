# -*- coding: utf-8 -*-
"""FLOKTRON · first-run smoke test — the "safe first test" from README, done by a script on a clean computer.

    python tests/first_run_smoke.py            # Windows
    python3 tests/first_run_smoke.py           # macOS / Linux

It copies the repository into a temporary folder and runs, as a new user would, every step that needs no mailbox
and no internet: config from the example, base, radar, company library, branded documents, supplier invoices
on the fictional set, company snapshot, dashboard, run.py, computer check-up, security check-up (read-only),
scheduler entries (printed only, nothing is installed), move pack → check → unpack, update check on a saved file.
All data is fictional (TEST · FICTIONAL, Demo SIA). Nothing outside the temporary folder is changed.

CI runs it on Windows and Linux (.github/workflows/tests.yml). The console encoding is NOT forced to UTF-8,
so a script that cannot print on a plain Windows console fails here, as it would for a real user.
"""
import os
import platform
import shutil
import subprocess
import sys
import tempfile

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
SKIP = {".git", ".pytest_cache", "__pycache__", ".venv", "venv"}


def copy_repo(dst):
    def ignore(d, names):
        out = [n for n in names if n in SKIP]
        if os.path.abspath(d) == os.path.join(SRC, "data"):
            out += [n for n in names if n not in ("letters", "replies", "reports")]
        return out
    shutil.copytree(SRC, dst, ignore=ignore)


def env_plain():
    """The environment of a plain user: no forced UTF-8, a fixed test password for the move archive."""
    e = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    e["FLOKTRON_MOVE_PASSWORD"] = "test-only-Fictional-2026"
    return e


def main():
    # this report itself must print on any console (the scripts it runs are NOT helped by this)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    tmp = tempfile.mkdtemp(prefix="floktron_smoke_")
    root = os.path.join(tmp, "floktron")
    copy_repo(root)
    shutil.copy(os.path.join(root, "config", "config.example.yaml"), os.path.join(root, "config", "config.yaml"))
    fx = os.path.join("tests", "fixtures")
    inv = os.path.join(fx, "invoices")
    osname = {"Windows": "windows", "Darwin": "mac"}.get(platform.system(), "linux")
    archive_dir = os.path.join(tmp, "archives")
    os.makedirs(archive_dir)

    steps = [
        ("base", ["scripts/base_create.py"], (0,)),
        ("radar", ["scripts/radar_create.py"], (0,)),
        ("library", ["scripts/library.py", "init"], (0,)),
        ("library check", ["scripts/library.py", "check"], (0, 1)),  # 1 = "fill in your company" — expected on a new setup
        ("document invoice LV", ["scripts/documents.py", "--doc", os.path.join(fx, "documents", "invoice_lv.json"),
                                 "--seller", os.path.join(fx, "documents", "seller_demo.json"),
                                 "--out", os.path.join("data", "smoke_docs")], (0,)),
        ("document offer EN", ["scripts/documents.py", "--doc", os.path.join(fx, "documents", "offer_en.json"),
                               "--seller", os.path.join(fx, "documents", "seller_demo.json"),
                               "--out", os.path.join("data", "smoke_docs")], (0,)),
        ("invoices (fictional set)", ["scripts/invoices.py", "--folder", os.path.join(inv, "docs"),
                                      "--extraction", os.path.join(inv, "extraction.json"),
                                      "--statements", os.path.join(inv, "statements_csv"),
                                      "--iban", "LV80BANK0000435195001", "--today", "2026-11-22",
                                      "--test", "--apply"], (0,)),
        ("snapshot", ["scripts/snapshot.py", "--test", "--as-of", "2026-11-22"], (0,)),
        ("dashboard", ["scripts/dashboard.py"], (0,)),
        ("run.py dashboard", ["scripts/run.py", "dashboard"], (0,)),
        ("run.py status", ["scripts/run.py", "status"], (0,)),
        ("computer check-up", ["scripts/capacity_check.py"], (0,)),
        # read-only; it may report ⚠ / ❌ about the CI machine itself, so any normal exit counts
        ("security check-up", ["scripts/security_check.py"], (0, 1, 2)),
        ("scheduler entries (" + osname + ", print only)",
         ["scripts/install/schedule.py", osname, root, PY], (0,)),
        ("move pack", ["scripts/move.py", "pack", "--out", archive_dir], (0,)),
        ("update check (saved file)", ["scripts/update_check.py", "--releases",
                                       os.path.join(fx, "updates", "releases.json"), "--current", "0.1.0",
                                       "--force", "--dry"], (0,)),
    ]

    results, failed = [], 0
    env = env_plain()

    def run(name, args, ok, cwd=root):
        nonlocal failed
        p = subprocess.run([PY] + args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        out = p.stdout.decode("utf-8", "replace")
        good = p.returncode in ok and "Traceback" not in out
        results.append((name, good, p.returncode))
        if not good:
            failed += 1
            print(f"\n----- FAILED: {name} (exit {p.returncode}) -----\n{out[-4000:]}\n-----")
        return good

    try:
        import reportlab  # noqa: F401 — optional: PDF documents (docs/DOCUMENTS.md)
        has_pdf = True
    except ImportError:
        has_pdf = False
    try:
        import pyzipper  # noqa: F401 — optional: password-protected move archive (docs/MOVE.md)
        has_zip = True
    except ImportError:
        has_zip = False
    for name, args, ok in steps:
        if name.startswith("document") and not has_pdf:
            results.append((name + " — skipped, reportlab not installed", True, "-"))
            continue
        if name == "move pack" and not has_zip:
            results.append((name + " — skipped, pyzipper not installed (the move buttons install it)", True, "-"))
            continue
        run(name, args, ok)

    zips = sorted(f for f in os.listdir(archive_dir) if f.endswith(".zip"))
    if not has_zip:
        pass
    elif zips:
        arc = os.path.join(archive_dir, zips[-1])
        run("move check", ["scripts/move.py", "check", arc], (0,))
        root2 = os.path.join(tmp, "floktron_new_computer")
        copy_repo(root2)
        run("move unpack (new computer)", ["scripts/move.py", "unpack", arc], (0,), cwd=root2)
        if not os.path.exists(os.path.join(root2, "data", "floktron_base.xlsx")):
            results.append(("base arrived after unpack", False, "-"))
            failed += 1
    else:
        results.append(("move archive written", False, "-"))
        failed += 1

    print(f"\nFLOKTRON first-run smoke · {platform.system()} {platform.release()} · Python {platform.python_version()}")
    for name, good, rc in results:
        print(f"  {'OK  ' if good else 'FAIL'}  {name}")
    print(f"{len(results) - failed} of {len(results)} steps passed")
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
