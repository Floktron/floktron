# -*- coding: utf-8 -*-
"""FLOKTRON · desktop_icon.py — a FLOKTRON icon on the desktop: one double-click refreshes and opens the dashboard.

    python3 scripts/desktop_icon.py            # put the icon on the desktop (Mac, Windows, Linux)
    python3 scripts/desktop_icon.py --remove   # take it away again
    python3 scripts/desktop_icon.py --open     # what the icon runs: rebuild data/dashboard.html, open it in the browser

What it makes (nothing is downloaded, nothing runs in the background, no admin rights):
- Mac:     ~/Desktop/FLOKTRON.app — a tiny app bundle with the FLOKTRON icon (assets/brand/floktron.icns)
- Windows: Desktop\\FLOKTRON.lnk — a shortcut with assets/brand/floktron.ico (made by PowerShell, the built-in way)
- Linux:   ~/.local/share/applications/floktron.desktop (+ a copy on ~/Desktop if that folder exists)
The icon only calls this script with --open. Moved the FLOKTRON folder? Run this script again from the new place.
"""
import argparse
import os
import plistlib
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path, PureWindowsPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BRAND = ROOT / "assets" / "brand"
NAME = "FLOKTRON"


def desktop_dir(home=None, system=None):
    home = Path(home or Path.home())
    system = system or sys.platform
    if system.startswith("win"):
        one = os.environ.get("OneDrive")  # Windows often moves the desktop into OneDrive
        if one and (Path(one) / "Desktop").is_dir():
            return Path(one) / "Desktop"
    return home / "Desktop"


def open_dashboard(data=None, opener=webbrowser.open):
    """Rebuild the dashboard (so the page is fresh) and open it in the default browser."""
    sys.path.insert(0, str(HERE))
    import dashboard
    args = ["--data", str(data)] if data else []
    try:
        dashboard.main(args)
    except Exception as e:  # an old page is better than no page
        print(f"dashboard not rebuilt ({e}); opening the last one")
    page = Path(data or dashboard.DATA) / "dashboard.html"
    if not page.exists():
        print(f"no dashboard yet: {page}")
        return 1
    opener(page.resolve().as_uri())
    return 0


def mac_app(dest, python=sys.executable, root=ROOT):
    """FLOKTRON.app: Contents/Info.plist + MacOS/FLOKTRON (shell launcher) + Resources/floktron.icns."""
    app = Path(dest) / f"{NAME}.app"
    if app.exists():
        shutil.rmtree(app)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir()
    shutil.copy(BRAND / "floktron.icns", app / "Contents" / "Resources" / "floktron.icns")
    with open(app / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump({"CFBundleName": NAME, "CFBundleDisplayName": NAME, "CFBundleExecutable": NAME,
                       "CFBundleIdentifier": "com.floktron.dashboard", "CFBundleIconFile": "floktron",
                       "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "1.0",
                       "LSUIElement": True}, f)
    run = app / "Contents" / "MacOS" / NAME
    run.write_text("#!/bin/sh\n# FLOKTRON · open the dashboard (made by scripts/desktop_icon.py)\n"
                   f'exec "{python}" "{Path(root) / "scripts" / "desktop_icon.py"}" --open\n', encoding="utf-8")
    run.chmod(0o755)
    return app


def windows_ps(dest, python=sys.executable, root=ROOT):
    """PowerShell text that makes Desktop\\FLOKTRON.lnk (pythonw = no black console window)."""
    py = PureWindowsPath(python)
    pyw = py.with_name("pythonw.exe") if py.name.lower() == "python.exe" else py
    q = lambda p: str(p).replace("'", "''")  # noqa: E731 — PowerShell single-quote escaping
    lnk = Path(dest) / f"{NAME}.lnk"
    return ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut('" + q(lnk) + "'); "
            "$s.TargetPath = '" + q(pyw) + "'; "
            "$s.Arguments = '\"" + q(Path(root) / "scripts" / "desktop_icon.py") + "\" --open'; "
            "$s.WorkingDirectory = '" + q(root) + "'; "
            "$s.IconLocation = '" + q(BRAND / "floktron.ico") + ",0'; "
            "$s.Description = 'FLOKTRON dashboard'; $s.Save()"), lnk


def linux_entry(python=sys.executable, root=ROOT):
    return ("[Desktop Entry]\nType=Application\nName=FLOKTRON\nComment=FLOKTRON dashboard\n"
            f'Exec="{python}" "{Path(root) / "scripts" / "desktop_icon.py"}" --open\n'
            f"Icon={BRAND / 'floktron-512.png'}\nTerminal=false\nCategories=Office;\n")


def install(home=None, system=None, run=subprocess.run):
    system = system or sys.platform
    home = Path(home or Path.home())
    desk = desktop_dir(home, system)
    if system == "darwin":
        desk.mkdir(parents=True, exist_ok=True)
        return [mac_app(desk)]
    if system.startswith("win"):
        ps, lnk = windows_ps(desk)
        run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True)
        return [lnk]
    apps = home / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    made = [apps / "floktron.desktop"]
    if desk.is_dir():
        made.append(desk / "floktron.desktop")
    for p in made:
        p.write_text(linux_entry(), encoding="utf-8")
        p.chmod(0o755)
    return made


def remove(home=None, system=None):
    system = system or sys.platform
    home = Path(home or Path.home())
    desk = desktop_dir(home, system)
    gone = []
    for p in (desk / f"{NAME}.app", desk / f"{NAME}.lnk", desk / "floktron.desktop",
              home / ".local" / "share" / "applications" / "floktron.desktop"):
        if p.is_dir():
            shutil.rmtree(p)
            gone.append(p)
        elif p.exists():
            p.unlink()
            gone.append(p)
    return gone


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON icon on the desktop")
    ap.add_argument("--remove", action="store_true", help="take the icon away")
    ap.add_argument("--open", action="store_true", help="rebuild and open the dashboard (what the icon runs)")
    a = ap.parse_args(argv)
    if a.open:
        return open_dashboard()
    if a.remove:
        gone = remove()
        print("removed: " + (", ".join(map(str, gone)) if gone else "nothing to remove"))
        return 0
    for p in install():
        print(f"✅ desktop icon: {p}")
    print("Double-click FLOKTRON on the desktop — the dashboard refreshes and opens in your browser.")
    if sys.platform == "darwin":
        print("First time only: if the Mac asks, right-click the icon → Open → Open.")
    return 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401
    sys.exit(main())
