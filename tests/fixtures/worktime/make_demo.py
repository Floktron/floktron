# -*- coding: utf-8 -*-
"""TEST · FICTIONAL — a month of work-time marks for an invented company, to see the dashboard block.

    python3 tests/fixtures/worktime/make_demo.py OUT_DIR [--lang ru] [--now "2026-11-27 16:20"]
Writes OUT_DIR/worktime.jsonl + OUT_DIR/config.yaml; then:  python3 scripts/dashboard.py --config OUT_DIR/config.yaml --data OUT_DIR
People, sites and coordinates are invented (TEST · FICTIONAL)."""
import argparse
import datetime
import json
import os
import random

PEOPLE = {"9001": "Anna K. (TEST)", "9002": "Jānis B. (TEST)", "9003": "Oleg S. (TEST)", "9004": "Marta L. (TEST)",
          "9005": "Pēteris D. (TEST)", "9006": "Ivo R. (TEST)"}
WHY = {"ru": "забыл нажать «Закончил» (TEST)", "lv": "aizmirsa nospiest «Beidzu» (TEST)", "en": "forgot to tap End (TEST)"}
SITES = [{"name": "Objekts Parka 12 (TEST)", "lat": 56.95100, "lon": 24.11300, "radius_m": 250},
         {"name": "Noliktava (TEST)", "lat": 56.93000, "lon": 24.16000, "radius_m": 200}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--now", default="2026-11-27 16:20")
    a = ap.parse_args()
    now = datetime.datetime.strptime(a.now, "%Y-%m-%d %H:%M")
    os.makedirs(a.out, exist_ok=True)
    rnd = random.Random(7)
    ev = []

    def put(who, ts, e, site=None, off=0, **x):
        r = {"ts": ts.strftime("%Y-%m-%d %H:%M"), "who": who, "name": PEOPLE[who], "ev": e, "by": "bot"}
        if site:
            r.update(lat=round(site["lat"] + off, 5), lon=round(site["lon"], 5), site=site["name"])
            r["dist"] = int(abs(off) * 111000)
            r["inside"] = r["dist"] <= site["radius_m"]
        r.update(x)
        ev.append(r)

    first = now.replace(day=1, hour=0, minute=0)
    d = first
    while d.date() < now.date():
        for i, who in enumerate(PEOPLE):
            if d.weekday() >= 5 and not (who == "9003" and d.weekday() == 5):   # Oleg works some Saturdays
                continue
            if rnd.random() < 0.07 and d.date() not in (now.date() - datetime.timedelta(days=1), now.date() - datetime.timedelta(days=3)):
                continue
            site = SITES[1] if who in ("9004", "9006") else SITES[0]
            s = d.replace(hour=7, minute=rnd.randint(30, 59)) if who != "9006" else d.replace(hour=21, minute=55)  # Ivo — night shift
            put(who, s, "start", site, off=rnd.uniform(-0.0012, 0.0012))
            put(who, s + datetime.timedelta(hours=4, minutes=rnd.randint(0, 30)), "pause")
            put(who, s + datetime.timedelta(hours=4, minutes=45 + rnd.randint(0, 15)), "back")
            length = 8.5 + (1.5 if who == "9003" and rnd.random() < 0.4 else 0) + rnd.uniform(-0.3, 0.4)
            forgot = (who == "9005" and d.date() == now.date() - datetime.timedelta(days=1)) or \
                (who == "9001" and d.date() == now.date() - datetime.timedelta(days=3))     # Pēteris yesterday, Anna 3 days ago
            if not forgot:
                put(who, s + datetime.timedelta(hours=length + 0.75), "end")
        d += datetime.timedelta(days=1)
    t = now.replace(hour=0, minute=0)
    put("9001", t.replace(hour=7, minute=48), "start", SITES[0], 0.0003)
    put("9002", t.replace(hour=7, minute=55), "start", SITES[0], 0.0041)            # 450 m away from the site
    put("9003", t.replace(hour=7, minute=31), "start", SITES[0], -0.0002)
    put("9003", t.replace(hour=15, minute=58), "pause")
    put("9004", t.replace(hour=6, minute=59), "start", SITES[1], 0.0001)
    put("9004", t.replace(hour=15, minute=31), "end")
    fixd = (now.date() - datetime.timedelta(days=3)).isoformat()
    ev.append({"ts": (now - datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M"), "who": "9001", "name": PEOPLE["9001"], "ev": "fix",
               "by": "manager", "date": fixd, "end": "17:10", "why": WHY.get(a.lang, WHY["en"])})
    ev.sort(key=lambda r: r["ts"])
    with open(os.path.join(a.out, "worktime.jsonl"), "w", encoding="utf-8") as f:
        for r in ev:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    import yaml
    cfg = {"company": {"name": "TEST · FICTIONAL SIA Paraugs Būve", "language": a.lang},
           "worktime": {"enabled": True, "geo": True, "people": PEOPLE, "sites": SITES, "remind_at": "20:00",
                        "holidays": ["2026-11-18"]}}
    with open(os.path.join(a.out, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    print(f"TEST · FICTIONAL: {len(ev)} marks → {a.out}")


if __name__ == "__main__":
    main()
