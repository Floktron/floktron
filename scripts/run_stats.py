# -*- coding: utf-8 -*-
"""FLOKTRON · run_stats.py — honest run numbers from the run log: period, what counts, how many failed.

    python3 scripts/run_stats.py                      # data/run.log → text summary
    python3 scripts/run_stats.py --json data/run_stats.json   # also write the numbers for the dashboard / a web page
    python3 scripts/run_stats.py --since 2026-11-08 --until 2026-11-27

What is counted (the same words go next to every published number):
  run        one start of a scheduled job by scripts/run.py — a "=== <date> <job>" line in data/run.log
             (jobs that ride along, e.g. mail watch after reply collection, count as their own runs);
  ok         the job ended with exit code 0;
  failed     exit code ≠ 0, or a timeout;
  recovered  a failed run whose NEXT run of the same job ended ok (the next scheduled try fixed it);
  not recovered  failed, and the next run of that job also failed or never came;
  skipped    not started because another FLOKTRON run was working (not a run, listed apart);
  unfinished a start without an end line (computer switched off, still running) — listed apart, not "ok".
"ok" means the program finished without an error. It does NOT check that every letter reached its reader:
FLOKTRON says that in the morning message and the dashboard separately.
Nothing leaves the computer; the script only reads the log.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

START = re.compile(r"^=== (\d{4}-\d\d-\d\d \d\d:\d\d) (\S+)")
EXIT = re.compile(r"^--- exit (-?\d+)")
TIMEOUT = re.compile(r"^--- (\S+): timeout")
SKIP = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d) (\S+): skipped")

DEFINITION = ("run = one start of a scheduled job (scripts/run.py, data/run.log); ok = ended with exit code 0; "
              "failed = exit code not 0 or timeout; recovered = the next run of the same job ended ok; "
              "ok means the program finished without an error, not that every letter was read")


def parse(lines):
    """[{when, job, result: ok|failed|unfinished}], skipped count."""
    runs, skipped, cur = [], 0, None
    for ln in lines:
        ln = ln.rstrip("\n")
        m = START.match(ln)
        if m:
            if cur is not None:
                runs.append(cur)
            cur = dict(when=dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M"), job=m.group(2), result="unfinished")
            continue
        if SKIP.match(ln):
            skipped += 1
            continue
        if cur is None:
            continue
        m = EXIT.match(ln)
        if m:
            cur["result"] = "ok" if m.group(1) == "0" else "failed"
            runs.append(cur)
            cur = None
        elif TIMEOUT.match(ln):
            cur["result"] = "failed"
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    return runs, skipped


def stats(runs, skipped=0, since=None, until=None):
    sel = [r for r in runs if (not since or r["when"].date() >= since) and (not until or r["when"].date() <= until)]
    by_job, out = {}, dict(runs=0, ok=0, failed=0, recovered=0, not_recovered=0, unfinished=0, skipped=skipped)
    for r in sorted(runs, key=lambda x: x["when"]):
        by_job.setdefault(r["job"], []).append(r)
    nxt = {}
    for lst in by_job.values():
        for a, b in zip(lst, lst[1:] + [None]):
            nxt[id(a)] = b
    jobs = {}
    for r in sel:
        out["runs"] += 1
        j = jobs.setdefault(r["job"], dict(runs=0, failed=0))
        j["runs"] += 1
        if r["result"] == "ok":
            out["ok"] += 1
        elif r["result"] == "unfinished":
            out["unfinished"] += 1
        else:
            out["failed"] += 1
            j["failed"] += 1
            b = nxt.get(id(r))
            out["recovered" if b is not None and b["result"] == "ok" else "not_recovered"] += 1
    done = out["ok"] + out["failed"]
    out["failed_pct"] = round(100.0 * out["failed"] / done, 1) if done else 0.0
    out["from"] = min((r["when"] for r in sel), default=None)
    out["to"] = max((r["when"] for r in sel), default=None)
    out["jobs"] = jobs
    return out


def text(s, lang="en"):
    if not s["runs"]:
        return "No runs in the log for this period."
    f, t = s["from"].strftime("%d.%m.%Y"), s["to"].strftime("%d.%m.%Y")
    return (f"{s['runs']} automatic runs {f}–{t}: {s['ok']} ok, {s['failed']} failed ({s['failed_pct']} %), "
            f"of them {s['recovered']} fixed by the next run and {s['not_recovered']} not; "
            f"{s['unfinished']} unfinished, {s['skipped']} skipped (another run working). Source: data/run.log. "
            f"Counted: {DEFINITION}.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="FLOKTRON run numbers from data/run.log")
    ap.add_argument("--log", default=os.path.join(ROOT, "data", "run.log"))
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    if not os.path.exists(a.log):
        print(f"No run log yet: {a.log}")
        return 1
    with open(a.log, encoding="utf-8", errors="replace") as f:
        runs, skipped = parse(f)
    s = stats(runs, skipped, dt.date.fromisoformat(a.since) if a.since else None,
              dt.date.fromisoformat(a.until) if a.until else None)
    print(text(s))
    for name, j in sorted(s["jobs"].items()):
        print(f"  {name:12} {j['runs']:5} runs, {j['failed']} failed")
    if a.json:
        doc = {k: v for k, v in s.items() if k not in ("from", "to")}
        doc.update({"from": s["from"].isoformat(timespec="minutes") if s["from"] else None,
                    "to": s["to"].isoformat(timespec="minutes") if s["to"] else None,
                    "counted": DEFINITION, "source": "data/run.log",
                    "made": dt.datetime.now().isoformat(timespec="minutes")})
        tmp = a.json + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        os.replace(tmp, a.json)
        print("written:", a.json)
    return 0


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    sys.exit(main())
