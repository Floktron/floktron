# -*- coding: utf-8 -*-
"""FLOKTRON · run.py — one entry point for the scheduler. Everything goes to data/run.log.

    python3 scripts/run.py morning     # morning messages
    python3 scripts/run.py collect     # read replies (+ routes)          — every 30 min
    python3 scripts/run.py deadline    # who did not answer at all        — at the reply deadline
    python3 scripts/run.py evening     # evening reminder for open tasks
    python3 scripts/run.py news        # evening news slice (1 day)
    python3 scripts/run.py supply      # supply chain watch, light (prices, currencies, news of your watch list)
    python3 scripts/run.py supply_week # supply chain watch, weekly (news 7 days + supplier page changes)
    python3 scripts/run.py summary     # weekly summary to the manager
    python3 scripts/run.py gaps        # weekly list of what FLOKTRON could not do
    python3 scripts/run.py registry    # new companies in the registry (LV)
    python3 scripts/run.py content     # posts of the day, missed posts, duplicate pictures
    python3 scripts/run.py mail        # mail watch by hand (it also runs after every collect, docs/MAIL_WATCH.md)
    python3 scripts/run.py gateways    # payment gateways by hand (it also runs after every collect, docs/GATEWAYS.md)
    python3 scripts/run.py prospects   # new customers like your best ones, with a reason to write now (once a day)
    python3 scripts/run.py backup      # weekly backup of the whole setup, password-protected (docs/MOVE.md)
    python3 scripts/run.py dashboard   # rebuild data/dashboard.html (also done after every other run)
    python3 scripts/run.py status      # last lines of the log

A lock file stops two runs of FLOKTRON from writing the base at the same time.
If the base is open in Excel, the run waits and tries again (up to 10 minutes).
"""
import datetime
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
LOG = os.path.join(DATA, "run.log")
LOCK = os.path.join(DATA, ".floktron.lock")

JOBS = {
    "morning": ["send_morning.py"],
    "collect": ["collect_replies.py"],
    "deadline": ["collect_replies.py", "--deadline"],
    "evening": ["send_morning.py", "--evening"],
    "news": ["news_slice.py", "--days", "1"],
    "supply": ["supply_watch.py"],
    "supply_week": ["supply_watch.py", "--full"],
    "summary": ["weekly_summary.py"],
    "gaps": ["gaps_report.py"],
    "registry": ["registry_lv.py"],
    "content": ["content_check.py"],
    "mail": ["mail_watch.py"],
    "gateways": ["gateways.py"],
    "prospects": ["prospects.py"],
    "backup": ["move.py", "backup"],
    "dashboard": ["dashboard.py"],
}


def excel_has_open(path):
    """Excel / LibreOffice leave a lock file next to an open workbook."""
    d, n = os.path.split(path)
    return any(os.path.exists(os.path.join(d, p + n)) for p in ("~$", ".~lock."))


def main():
    job = sys.argv[1] if len(sys.argv) > 1 else ""
    os.makedirs(DATA, exist_ok=True)
    if job == "status":
        if os.path.exists(LOG):
            with open(LOG, encoding="utf-8") as f:
                print("".join(f.readlines()[-40:]))
        return
    if job not in JOBS:
        sys.exit(__doc__)

    # one FLOKTRON run at a time (a stale lock older than 1 hour is ignored)
    if os.path.exists(LOCK) and time.time() - os.path.getmtime(LOCK) < 3600:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M} {job}: skipped — another FLOKTRON run is working\n")
        return
    base = os.path.join(DATA, "floktron_base.xlsx")
    for _ in range(10):
        if not excel_has_open(base):
            break
        time.sleep(60)
    open(LOCK, "w").close()
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M} {job}\n")
            f.flush()
            r = subprocess.run([sys.executable, os.path.join(HERE, JOBS[job][0])] + JOBS[job][1:] + sys.argv[2:],
                               cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
            f.write(f"--- exit {r.returncode}\n")
            if job == "collect":        # mail watch rides along every 30 minutes (does nothing while mail_watch.enabled is false)
                f.write(f"=== {datetime.datetime.now():%Y-%m-%d %H:%M} mail\n")
                f.flush()
                m = subprocess.run([sys.executable, os.path.join(HERE, "mail_watch.py")], cwd=ROOT, stdout=f,
                                   stderr=subprocess.STDOUT, timeout=900)
                f.write(f"--- exit {m.returncode}\n")
                f.write(f"=== {datetime.datetime.now():%Y-%m-%d %H:%M} gateways\n")   # card payments → documents (nothing while gateways.enabled is false)
                f.flush()
                try:
                    g = subprocess.run([sys.executable, os.path.join(HERE, "gateways.py")], cwd=ROOT, stdout=f,
                                       stderr=subprocess.STDOUT, timeout=600)
                    f.write(f"--- exit {g.returncode}\n")
                except subprocess.TimeoutExpired:
                    f.write("--- gateways: timeout\n")
            if job != "dashboard":      # the one-page overview follows every run; a failure here never fails the job
                subprocess.run([sys.executable, os.path.join(HERE, "dashboard.py")], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    finally:
        os.remove(LOCK)


if __name__ == "__main__":
    main()
