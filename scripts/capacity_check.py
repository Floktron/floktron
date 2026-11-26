# -*- coding: utf-8 -*-
"""FLOKTRON · capacity_check.py — can THIS computer carry FLOKTRON, and what does it take off the AI?

    python3 scripts/capacity_check.py          # report on screen + data/capacity_check_<date>.txt
    python3 scripts/capacity_check.py --json   # the same as JSON (for the dashboard or an assistant)

READ ONLY. It reads processor cores, memory, free disk, the system and the Python version — nothing else.
No network, no administrator rights, nothing installed or changed. Part of the computer check-up (setup step 0
and step 12, docs/BREATH.md). Thresholds are estimates for FLOKTRON's own scripts, not a benchmark.

"Breath": the routine runs here, on your computer — news slices, monitoring, mail, invoices, documents, the
dashboard. The AI assistant then reads one short summary instead of every page, so its work goes to thinking.
"""
import ctypes
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OK, WARN, BAD, INFO = "✅", "⚠️", "❌", "ℹ️"

# What runs on the computer (scripts, no AI) and what the AI does afterwards. Kept honest by tests/test_capacity.py.
BREATH = [
    ("News and registry slices", "news_slice.py, radar_create.py", "reads the short report, judges what matters"),
    ("Supply chain and Telegram watch", "supply_watch.py, tg_watch.py", "reads only what moved"),
    ("Mail watch and reminders", "mail_watch.py, followups.py", "drafts an answer when you ask"),
    ("Invoices and card payments", "invoices.py, gateways.py", "reads a new invoice once, the check is a script"),
    ("Documents from the library", "library.py, documents.py", "fills the buyer and the lines of a template"),
    ("Morning tasks, replies, escalation", "send_morning.py, collect_replies.py, route.py", "none — fully scripted"),
    ("Dashboard and morning audio", "dashboard.py, voice.py", "none — fully scripted"),
]


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=10).stdout.strip()
    except Exception:
        return ""


def ram_gb():
    """Total memory in GB, or None when it cannot be read."""
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / 1024 / 1024
        if sys.platform == "darwin":
            out = run(["sysctl", "-n", "hw.memsize"])
            return int(out) / 1024 ** 3 if out.isdigit() else None
        if sys.platform.startswith("win"):
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 1024 ** 3
    except Exception:
        return None
    return None


def facts(folder=ROOT):
    return {
        "system": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "cores": os.cpu_count() or 0,
        "ram_gb": round(ram_gb(), 1) if ram_gb() else None,
        "disk_free_gb": round(shutil.disk_usage(folder).free / 1024 ** 3, 1),
        "python": platform.python_version(),
    }


def judge(f):
    """Rows (mark, what, value, meaning). Estimates for FLOKTRON's scripts."""
    rows = []
    py = tuple(int(x) for x in f["python"].split(".")[:2])
    rows.append((OK if py >= (3, 10) else BAD, "Python", f["python"],
                 "fine" if py >= (3, 10) else "FLOKTRON needs Python 3.10 or newer"))
    c = f["cores"]
    rows.append((OK if c >= 4 else WARN, "Processor cores", str(c),
                 "all scripts and local voice run comfortably" if c >= 4 else
                 "scripts run; local speech-to-text will be slow — use a smaller model or skip voice"))
    r = f["ram_gb"]
    if r is None:
        rows.append((INFO, "Memory", "unknown", "could not be read — check it in the system settings"))
    else:
        rows.append((OK if r >= 8 else WARN if r >= 4 else BAD, "Memory", f"{r} GB",
                     "enough for everything incl. local voice" if r >= 8 else
                     "enough for the scripts; local voice with the small model, close heavy apps" if r >= 4 else
                     "tight: switch local voice off; the scripts still run"))
    d = f["disk_free_gb"]
    rows.append((OK if d >= 5 else WARN if d >= 1 else BAD, "Free disk", f"{d} GB",
                 "room for bases, PDFs, the library and the voice model" if d >= 5 else
                 "enough to start; the voice model needs about 0.5 GB" if d >= 1 else
                 "free some space before setup"))
    return rows


# What each way of using FLOKTRON asks of the computer (estimates, docs/REQUIREMENTS.md). Cloud voice needs no more
# than text only — the work is done by the voice service, which is a paid subscription.
VARIANTS = [
    ("Text only (letters, Telegram, tasks, radar, invoices)", {"cores": 2, "ram_gb": 4, "disk_free_gb": 2}),
    ("+ computer voice (system voice, free)", {"cores": 2, "ram_gb": 4, "disk_free_gb": 2}),
    ("+ voice reports turned into text on this computer", {"cores": 4, "ram_gb": 8, "disk_free_gb": 5}),
    ("+ live cloud voice (ElevenLabs, paid)", {"cores": 2, "ram_gb": 4, "disk_free_gb": 2}),
]


def variants(f):
    """[(variant, mark)] — ✅ fits, ⚠️ works but slower or tight, ❌ Python too old for anything."""
    py = tuple(int(x) for x in f["python"].split(".")[:2])
    out = []
    for name, need in VARIANTS:
        if py < (3, 10):
            mark = BAD
        else:
            short = [k for k, v in need.items() if f.get(k) is not None and f[k] < v]
            mark = OK if not short else WARN
        out.append((name, mark))
    return out


def report(f, rows):
    out = ["FLOKTRON computer check-up — capacity and breath", f"{datetime.date.today().isoformat()} · {f['system']} · {f['machine']}", ""]
    out += [f"{m} {w:<16} {v:<10} {why}" for m, w, v, why in rows]
    out += ["", "What this computer can carry (monthly costs of each: docs/REQUIREMENTS.md):"]
    out += [f"  {m} {name}" for name, m in variants(f)]
    out += ["", "Breath — what runs here and what is left for the AI:"]
    out += [f"  · {task}: {scripts} → AI: {ai}" for task, scripts, ai in BREATH]
    out += ["", "The library (company profile + templates) lives in data/library/ — offline, readable by any assistant.",
            "Nothing was changed. Suggested next: python3 scripts/security_check.py"]
    return "\n".join(out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    f = facts()
    rows = judge(f)
    if "--json" in argv:
        print(json.dumps({"facts": f, "rows": [dict(zip(("mark", "what", "value", "meaning"), r)) for r in rows],
                          "variants": [{"variant": n, "mark": m} for n, m in variants(f)],
                          "breath": [dict(zip(("task", "scripts", "ai"), b)) for b in BREATH]}, ensure_ascii=False, indent=1))
        return 0
    text = report(f, rows)
    print(text)
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, f"capacity_check_{datetime.date.today().isoformat()}.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return 1 if any(r[0] == BAD for r in rows) else 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    sys.exit(main())
