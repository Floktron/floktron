# -*- coding: utf-8 -*-
"""Desktop icon: Mac app bundle, Windows shortcut command, Linux entry, remove, open — all in a temp home."""
import os
import plistlib
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import desktop_icon as di  # noqa: E402


def test_brand_files_exist():
    for f in ("floktron-mark.svg", "floktron.icns", "floktron.ico", "floktron-512.png"):
        assert (di.BRAND / f).stat().st_size > 0, f


def test_mac_app_bundle(tmp_path):
    (app,) = di.install(home=tmp_path, system="darwin")
    assert app == tmp_path / "Desktop" / "FLOKTRON.app"
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleExecutable"] == "FLOKTRON" and info["CFBundleIconFile"] == "floktron"
    assert (app / "Contents" / "Resources" / "floktron.icns").exists()
    run = app / "Contents" / "MacOS" / "FLOKTRON"
    assert os.access(run, os.X_OK) and "desktop_icon.py\" --open" in run.read_text()
    assert di.install(home=tmp_path, system="darwin")  # running twice replaces, no error
    assert di.remove(home=tmp_path, system="darwin") == [app] and not app.exists()


def test_windows_shortcut_command(tmp_path):
    calls = []
    (lnk,) = di.install(home=tmp_path, system="win32", run=lambda cmd, check: calls.append(cmd))
    assert lnk.name == "FLOKTRON.lnk"
    ps = calls[0][-1]
    assert calls[0][0] == "powershell" and "CreateShortcut" in ps and "floktron.ico,0" in ps and "--open" in ps


def test_windows_quotes_escaped(tmp_path):
    ps, _ = di.windows_ps(tmp_path / "O'Brien", python="C:\\Py\\python.exe", root=tmp_path)
    assert "O''Brien" in ps and "pythonw.exe" in ps


def test_linux_entry(tmp_path):
    (tmp_path / "Desktop").mkdir()
    made = di.install(home=tmp_path, system="linux")
    assert len(made) == 2
    text = made[0].read_text()
    assert "Exec=" in text and "--open" in text and "floktron-512.png" in text and "Terminal=false" in text
    assert len(di.remove(home=tmp_path, system="linux")) == 2


def test_open_builds_and_opens(tmp_path):
    seen = []
    assert di.open_dashboard(data=tmp_path, opener=seen.append) == 0
    assert seen and seen[0].startswith("file://") and seen[0].endswith("dashboard.html")
    page = (tmp_path / "dashboard.html").read_text(encoding="utf-8")
    assert 'rel="icon"' in page and "#8B5CF6" in page
