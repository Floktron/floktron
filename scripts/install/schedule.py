# -*- coding: utf-8 -*-
"""FLOKTRON · schedule.py — writes the scheduler entries for macOS (launchd), Linux (cron) or Windows (Task Scheduler).
Called by install_mac.command / install_linux.sh / install_windows.ps1 — not meant to be run by hand.

config.yaml → schedule (defaults shown):
    morning:  "07:40"      # working days
    deadline: "09:00"      # working days
    evening:  "18:30"      # working days
    news:     "18:56"      # every day
    content:  "07:12"      # every day — posts of the day, missed posts, duplicates
    summary:  "Fri 16:00"
    gaps:     "Fri 16:10"
    registry: "Mon 07:00"
    collect_every_minutes: 30
"""
import os
import sys

DEFAULTS = {"morning": "07:40", "deadline": "09:00", "evening": "18:30", "news": "18:56", "content": "07:12",
            "summary": "Fri 16:00", "gaps": "Fri 16:10", "registry": "Mon 07:00", "collect_every_minutes": 30}
DAILY = {"news", "content"}  # every day; the other "HH:MM" jobs — working days only
DAYS = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 0}


def load(root):
    p = os.path.join(root, "config", "config.yaml")
    cfg = {}
    if os.path.exists(p):
        import yaml
        with open(p, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    s = dict(DEFAULTS, **(cfg.get("schedule") or {}))
    return s


def hm(t):
    h, m = str(t).split(":")
    return int(h), int(m)


def jobs(s):
    """(name, weekdays or None for every day, hour, minute) + collect interval."""
    out = []
    for name, val in s.items():
        if name == "collect_every_minutes" or not val:
            continue
        val = str(val)
        if " " in val:                                   # "Fri 16:00" → once a week
            day, t = val.split()
            out.append((name, [DAYS[day[:3].title()]]) + hm(t))
        else:
            out.append((name, None if name in DAILY else [1, 2, 3, 4, 5]) + hm(val))
    return out, int(s.get("collect_every_minutes") or 30)


def mac(root, py, ident, la):
    s = load(root)
    fixed, every = jobs(s)
    run = os.path.join(root, "scripts", "run.py")

    def plist(name, when_xml):
        p = os.path.join(la, f"floktron.{ident}.{name}.plist")
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>floktron.{ident}.{name}</string>
<key>ProgramArguments</key><array><string>{py}</string><string>{run}</string><string>{name}</string></array>
<key>WorkingDirectory</key><string>{root}</string>
{when_xml}
<key>StandardOutPath</key><string>{root}/data/launchd.log</string>
<key>StandardErrorPath</key><string>{root}/data/launchd.log</string>
</dict></plist>
""")
    for name, wd, h, m in fixed:
        items = "".join(f"<dict><key>Weekday</key><integer>{d}</integer><key>Hour</key><integer>{h}</integer>"
                        f"<key>Minute</key><integer>{m}</integer></dict>" for d in wd) if wd else \
            f"<dict><key>Hour</key><integer>{h}</integer><key>Minute</key><integer>{m}</integer></dict>"
        plist(name, f"<key>StartCalendarInterval</key><array>{items}</array>")
    plist("collect", f"<key>StartInterval</key><integer>{every * 60}</integer>")


def linux(root, py):
    s = load(root)
    fixed, every = jobs(s)
    run = os.path.join(root, "scripts", "run.py")
    lines = [f"# FLOKTRON {root}"]
    for name, wd, h, m in fixed:
        days = ",".join(str(d) for d in wd) if wd else "*"
        lines.append(f"{m} {h} * * {days} cd '{root}' && '{py}' '{run}' {name}")
    lines.append(f"*/{every} * * * * cd '{root}' && '{py}' '{run}' collect")
    print("\n".join(lines))


def windows(root, py):
    s = load(root)
    fixed, every = jobs(s)
    run = os.path.join(root, "scripts", "run.py")
    names = {1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI", 6: "SAT", 0: "SUN"}
    for name, wd, h, m in fixed:
        sched = f'/SC WEEKLY /D {",".join(names[d] for d in wd)}' if wd else "/SC DAILY"
        print(f'schtasks /Create /F /TN "FLOKTRON\\{name}" /TR "\\"{py}\\" \\"{run}\\" {name}" {sched} /ST {h:02d}:{m:02d}')
    print(f'schtasks /Create /F /TN "FLOKTRON\\collect" /TR "\\"{py}\\" \\"{run}\\" collect" /SC MINUTE /MO {every}')


if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "mac":
        mac(*sys.argv[2:6])
    elif kind == "linux":
        linux(*sys.argv[2:4])
    elif kind == "windows":
        windows(*sys.argv[2:4])
