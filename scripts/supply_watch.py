# -*- coding: utf-8 -*-
"""FLOKTRON · supply_watch.py — watches your supply chain: suppliers, big producers, listed companies,
logistics, reference prices and currencies, rules. Everything comes from public sources.

Reads the "Watchlist" sheet of data/floktron_radar.xlsx (one row per thing you depend on) and writes what it
measured into "Watch_log":
    Ticker      → last close, change vs the previous close and vs 5 trading days ago (Yahoo Finance public chart
                  data; futures and currencies work the same, e.g. ALI=F, TTF=F, EURUSD=X)
    News query  → Google News RSS, window 1 day (light) or 7 days (--full); items with alarm words are flagged
    Page URL    → only with --full: a fingerprint of the page text; a change since the last fingerprint is flagged
Status per line: 🟢 normal · 🟡 attention · 🔴 urgent · ⚪ no data. Thresholds come from the row
(Yellow % / Red %) or from config.yaml → supply_chain. A news flag is only a CANDIDATE: the AI agent reads the
item and confirms or lowers it (prompts/32_supply_chain.md). Nothing is bought, ordered or sent.
Sources that do not answer go to "Gaps".

Usage:
    python3 scripts/supply_watch.py              # light run (every evening)
    python3 scripts/supply_watch.py --full       # weekly run: news for 7 days + page fingerprints
    python3 scripts/supply_watch.py --dry        # show, write nothing
Options: --radar <file>  --config <file>  --only S01,P01
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
UA = "Mozilla/5.0 (FLOKTRON supply watch; +https://github.com)"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=1mo&interval=1d"
GNEWS = "https://news.google.com/rss/search?q={q}+when:{d}d&hl={hl}&gl={gl}&ceid={gl}:{hl}"

# Words that make a news item a candidate. The agent always reads the item before the status stands.
RED_WORDS = ["bankrupt", "insolven", "liquidat", "force majeure", "explosion", "fire at", "shut down", "shutdown",
             "halts production", "plant closure", "sanction", "strike", "port closed", "suspended", "recall",
             "maksātnespēj", "likvidāc", "streik", "Insolvenz", "Werksschließung", "Brand", "höhere Gewalt",
             "банкрот", "забастов", "санкци", "пожар", "остановк"]
YELLOW_WORDS = ["price increase", "raises prices", "surcharge", "acquisition", "acquires", "merger", "new plant",
                "expansion", "launch", "new product", "delay", "congestion", "blank sailing", "typhoon", "storm",
                "anti-dumping", "tariff", "restriction", "cenu pieaugum", "Preiserhöhung", "Übernahme",
                "повышение цен", "поглощен", "новый завод", "задержк", "пошлин"]
STATUS = {"green": "🟢", "yellow": "🟡", "red": "🔴", "none": "⚪"}

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")


# ---------- pure helpers (tested offline) ----------
def pct(new, old):
    try:
        return round((float(new) / float(old) - 1) * 100, 1) if old else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def price_status(d1, d5, yellow, red):
    """5-day move ≥ red → red; day or 5-day move ≥ yellow → yellow. Up and down count the same."""
    if d1 is None and d5 is None:
        return "none"
    a1, a5 = abs(d1 or 0), abs(d5 or 0)
    if a5 >= red:
        return "red"
    if a5 >= yellow or a1 >= yellow:
        return "yellow"
    return "green"


def parse_chart(data):
    """Yahoo chart JSON → (date, last, change vs previous close %, change vs 5 closes ago %, currency)."""
    j = json.loads(data)
    r = j["chart"]["result"][0]
    closes = [(t, c) for t, c in zip(r.get("timestamp") or [], r["indicators"]["quote"][0].get("close") or [])
              if c is not None]
    if not closes:
        return None
    t, last = closes[-1]
    prev = closes[-2][1] if len(closes) > 1 else None
    wk = closes[-6][1] if len(closes) > 5 else None
    day = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).date().isoformat()
    return day, round(last, 4), pct(last, prev), pct(last, wk), (r.get("meta") or {}).get("currency", "")


def lang_region(lang):
    """'en' → ('en', 'US'), 'lv' → ('lv', 'LV'), 'en-GB' → ('en', 'GB')."""
    if "-" in lang:
        hl, gl = lang.split("-", 1)
        return hl.lower(), gl.upper()
    return lang.lower(), {"en": "US"}.get(lang.lower(), lang.upper())


def word_hit(text, words):
    low = text.lower()
    for w in words:
        if w.lower() in low:
            return w
    return ""


def news_status(title):
    if word_hit(title, RED_WORDS):
        return "red"
    if word_hit(title, YELLOW_WORDS):
        return "yellow"
    return "green"


def page_text(raw):
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def parse_rss(data):
    """Minimal RSS reader → [(title, link, pubDate)] — regex, so no XML entities trick the parser."""
    out = []
    for item in re.findall(r"(?s)<item>(.*?)</item>", data):
        def tag(n):
            m = re.search(rf"(?s)<{n}>(.*?)</{n}>", item)
            return html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1))).strip() if m else ""
        out.append((tag("title"), tag("link"), tag("pubDate")))
    return out


# ---------- network ----------
def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


# ---------- workbook ----------
def header_row(ws):
    for r in range(1, 6):
        if str(ws.cell(r, 1).value or "").strip() in ("ID", "Date"):
            return r
    return 1


def rows(ws):
    h = header_row(ws)
    head = [str(c.value or "").strip() for c in ws[h]]
    for row in ws.iter_rows(min_row=h + 1, values_only=True):
        if any(v not in (None, "") for v in row):
            yield dict(zip(head, row))


def last_fingerprint(log_rows, oid, url):
    fp = ""
    for r in log_rows:
        if r.get("ID") == oid and r.get("Measure") == "page" and r.get("URL") == url:
            fp = str(r.get("Value") or "")
    return fp


def num(v, default):
    try:
        return float(str(v).replace("%", "").replace(",", ".").strip())
    except (TypeError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser(description="Watch your supply chain by public sources.")
    ap.add_argument("--radar", default=os.path.join(ROOT, "data", "floktron_radar.xlsx"))
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--full", action="store_true", help="weekly: news for 7 days + page fingerprints")
    ap.add_argument("--only", default="")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    cfg = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg = (yaml.safe_load(f) or {}).get("supply_chain") or {}
    dy, dr = num(cfg.get("yellow_pct"), 5.0), num(cfg.get("red_pct"), 10.0)
    if not os.path.exists(a.radar):
        sys.exit(f"No radar: {a.radar} — run scripts/radar_create.py first")
    wb = openpyxl.load_workbook(a.radar)
    if "Watchlist" not in wb.sheetnames or "Watch_log" not in wb.sheetnames:
        sys.exit("The radar has no Watchlist / Watch_log sheets — run: python3 scripts/radar_create.py --add-watch")
    wl, log = wb["Watchlist"], wb["Watch_log"]
    old_log = list(rows(log))
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    today = datetime.date.today().isoformat()
    days = 7 if a.full else 1
    run = "supply_watch --full" if a.full else "supply_watch"
    out, gaps, counts = [], [], {k: 0 for k in STATUS}
    seen_urls = {str(r.get("URL") or "") for r in old_log}
    done_today = {(r.get("ID"), str(r.get("Measure") or "")) for r in old_log if str(r.get("Date") or "")[:10] == today}

    for o in rows(wl):
        oid = str(o.get("ID") or "").strip()
        if not oid or (only and oid not in only) or str(o.get("Active") or "Yes").strip().lower() in ("no", "nē", "нет"):
            continue
        name = str(o.get("Object") or oid)
        if str(o.get("Mode") or "daily").strip().lower().startswith("week") and not a.full:
            continue
        y, r_ = num(o.get("Yellow %"), dy), num(o.get("Red %"), dr)

        tick = str(o.get("Ticker") or "").strip()
        if tick and tick != "—":
            res, err = None, "no data"
            try:
                res = parse_chart(fetch(CHART.format(t=urllib.parse.quote(tick))))
            except Exception as e:  # noqa: BLE001 — any failure is a gap, not a crash
                err = str(e)[:80]
            if res and (oid, f"close {res[0]}") in done_today:
                continue  # already measured today (second run of the day)
            if res:
                day, val, d1, d5, cur = res
                st = price_status(d1, d5, y, r_)
                out.append([today, oid, name, f"close {day}", val, cur, d1, d5, STATUS[st], "",
                            CHART.format(t=urllib.parse.quote(tick)), "PUBLIC (Yahoo Finance)", run])
            else:
                st = "none"
                out.append([today, oid, name, "close", None, "", None, None, STATUS[st], "no data", "", "", run])
                gaps.append([today, f"price {tick}", "Yahoo Finance chart", err,
                             "source blocked", "check the ticker on finance.yahoo.com", "New"])
            counts[st] += 1

        q = str(o.get("News query") or "").strip()
        if q and q != "—":
            for lang in [x.strip() for x in str(o.get("News languages") or "en").split(",") if x.strip()][:3]:
                hl, gl = lang_region(lang)
                url = GNEWS.format(q=urllib.parse.quote(q), d=days, hl=hl, gl=gl)
                try:
                    items = parse_rss(fetch(url))
                except Exception as e:  # noqa: BLE001
                    gaps.append([today, f"news {oid} ({lang})", "Google News RSS", str(e)[:80], "source blocked", "", "New"])
                    continue
                for title, link, pub in items[:15]:
                    if not link or link in seen_urls:
                        continue
                    seen_urls.add(link)
                    st = news_status(title)
                    if st == "green":
                        continue  # ordinary news is not logged — only candidates
                    out.append([today, oid, name, "news", None, "", None, None, STATUS[st] + " candidate",
                                title[:300], link, "PUBLIC (Google News)", run])
                    counts[st] += 1

        page = str(o.get("Page URL") or "").strip()
        if a.full and page.startswith("http") and (oid, "page") not in done_today:
            try:
                fp = fingerprint(page_text(fetch(page)))
                before = last_fingerprint(old_log, oid, page)
                st = "green" if not before or before == fp else "yellow"
                note = "first fingerprint" if not before else ("no change" if st == "green" else "page changed — agent: read and describe")
                out.append([today, oid, name, "page", fp, "hash", None, None, STATUS[st], note, page, "PUBLIC (site)", run])
                counts[st] += 1
            except Exception as e:  # noqa: BLE001
                gaps.append([today, f"page {oid}", page, str(e)[:80], "source blocked", "", "New"])
                counts["none"] += 1

    summary = " · ".join(f"{STATUS[k]} {v}" for k, v in counts.items())
    for line in out:
        if line[8].startswith("🔴") or line[8].startswith("🟡"):
            print(f"{line[8]}  {line[2]} — {line[3]}: {line[9] or line[4]} {('Δ5 ' + str(line[7]) + ' %') if line[7] is not None else ''}")
    print(f"Supply watch {today}: {summary}  ({len(gaps)} gaps)")
    if a.dry:
        return
    for line in out:
        log.append(line)
    if "Gaps" in wb.sheetnames:
        for g in gaps:
            wb["Gaps"].append(g)
    if "Run_log" in wb.sheetnames:
        wb["Run_log"].append([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), run,
                              "supply chain watch", len(out), summary])
    wb.save(a.radar)


if __name__ == "__main__":
    main()
