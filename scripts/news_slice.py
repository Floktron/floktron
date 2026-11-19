# -*- coding: utf-8 -*-
"""FLOKTRON · news_slice.py — collects fresh news by the client's keywords into the radar.

Reads the "News_feeds" and "Keywords" sheets of data/floktron_radar.xlsx:
    P rows  portal RSS/Atom feed → items whose title or summary contains a keyword (feed language first)
    N rows  Google News query    → {q} is replaced by the priority-A keywords of that language
    T rows  public Telegram channel, URL https://t.me/s/<channel> (public web preview: no account,
            no phone, no API key) → posts that contain a keyword. Private channels and groups cannot be read.
    X rows  never opened
New items go to "Signal_feed" (type News, work status "To score") — the AI agent then scores relevance
1–5 and proposes a post or an action (prompts/30_news_evening.md). No duplicates by URL or title.
A feed that does not answer is written to "Gaps" (source blocked) and marked in "News_feeds".

Usage:
    python3 scripts/news_slice.py                # window 1 day (evening slice)
    python3 scripts/news_slice.py --days 7       # weekly
    python3 scripts/news_slice.py --dry          # show, write nothing
Options: --radar <file>  --only P01,N01
"""
import argparse
import datetime
import email.utils
import html
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (FLOKTRON news slice; +https://github.com)"

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")


def header_row(ws):
    """Sheets may start with a note line; the header is the first row whose first cell is 'ID' or 'Date'."""
    for r in range(1, 6):
        if str(ws.cell(r, 1).value or "").strip() in ("ID", "Date"):
            return r
    return 1


def keywords(wb):
    ws = wb["Keywords"]
    h = header_row(ws)
    head = [str(c.value or "") for c in ws[h]]
    lang_cols = {}
    for i, t in enumerate(head):
        m = re.match(r"Keyword (\w+)", t)
        if m:
            lang_cols[m.group(1).lower()] = i
    pcol = head.index("Priority") if "Priority" in head else None
    out = {}
    for row in ws.iter_rows(min_row=h + 1, values_only=True):
        if not row[0] or (pcol is not None and str(row[pcol] or "").strip().upper() != "A"):
            continue
        for lang, i in lang_cols.items():
            if row[i] and str(row[i]).strip():
                out.setdefault(lang, []).append(str(row[i]).strip())
    return out


MAX_FEED_BYTES = 5_000_000  # a news feed is never this big; protects memory from a hostile server


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError(f"feed larger than {MAX_FEED_BYTES // 1_000_000} MB — skipped")
    return data


def parse_feed(data):
    """Return [(date, title, link, summary)] from RSS or Atom."""
    data = re.sub(rb"<!DOCTYPE[^>]*>", b"", data)
    root = ET.fromstring(data)
    items = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        get = {c.tag.split("}")[-1]: c for c in it}
        title = (get.get("title").text or "") if get.get("title") is not None else ""
        link = ""
        if get.get("link") is not None:
            link = get["link"].text or get["link"].attrib.get("href", "")
        summ = ""
        for k in ("description", "summary", "content"):
            if get.get(k) is not None and get[k].text:
                summ = get[k].text
                break
        raw_date = ""
        for k in ("pubDate", "published", "updated", "date"):
            if get.get(k) is not None and get[k].text:
                raw_date = get[k].text
                break
        d = None
        try:
            d = email.utils.parsedate_to_datetime(raw_date)
        except (TypeError, ValueError):
            try:
                d = datetime.datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                d = None
        clean = lambda t: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()
        items.append((d, clean(title), link.strip(), clean(summ)[:300]))
    return items


TG_POST = re.compile(r'data-post="([A-Za-z0-9_]{3,64}/\d{1,9})"')
TG_TIME = re.compile(r'<time[^>]*datetime="([^"]+)"')
TG_TEXT = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)


def parse_tg_preview(data):
    """Return [(date, title, link, summary)] from a public channel page t.me/s/<channel> (newest 20 posts)."""
    page = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    items = []
    for block in page.split('class="tgme_widget_message_wrap')[1:]:
        post = TG_POST.search(block)
        if not post:
            continue
        t, body = TG_TIME.search(block), TG_TEXT.search(block)
        d = None
        if t:
            try:
                d = datetime.datetime.fromisoformat(t.group(1).replace("Z", "+00:00"))
            except ValueError:
                d = None
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<br\s*/?>", " ", re.sub(r"<(?!br)[^>]+>", "", body.group(1))))).strip() if body else ""
        if not text:
            continue                     # photo/video without caption — nothing to match
        title = text if len(text) <= 120 else text[:117].rsplit(" ", 1)[0] + "…"
        items.append((d, title, "https://t.me/" + post.group(1), text[:300]))
    return items


def plain(text):
    """Lower case without diacritics: 'Flīžu' → 'flizu' (Baltic and German letters change inside a word)."""
    t = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


def stem(word):
    """Cut the ending so 'kanalizācija' also finds 'kanalizācijas', 'kanalizāciju', and 'flīzes' finds 'flīžu'."""
    w = plain(word)
    return w[:-2] if len(w) >= 6 else w[:-1] if len(w) == 5 else w


def matches(keyword, text):
    """All words of the keyword must appear in the text (by their stem)."""
    t = plain(text)
    return all(stem(part) in t for part in keyword.split())


def google_query(words):
    q = " OR ".join(f'"{w}"' if " " in w else w for w in words[:8])
    return urllib.parse.quote(f"({q})").replace("%20", "+") if words else ""


def main():
    ap = argparse.ArgumentParser(description="Collect fresh news by keywords into the radar.")
    ap.add_argument("--radar", default=os.path.join(ROOT, "data", "floktron_radar.xlsx"))
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    now = datetime.datetime.now().astimezone()
    since = now - datetime.timedelta(days=a.days)
    only = {x.strip() for x in a.only.split(",") if x.strip()}

    wb = openpyxl.load_workbook(a.radar)
    kw = keywords(wb)
    all_kw = [w for ws_ in kw.values() for w in ws_]
    wf, ws_sig, ws_gap = wb["News_feeds"], wb["Signal_feed"], wb["Gaps"]
    hf, hs = header_row(wf), header_row(ws_sig)
    seen_urls = {str(r[5]) for r in ws_sig.iter_rows(min_row=hs + 1, values_only=True) if r[5]}
    seen_titles = {str(r[4]).lower() for r in ws_sig.iter_rows(min_row=hs + 1, values_only=True) if r[4]}

    found, answered, failed = 0, 0, 0
    for row in wf.iter_rows(min_row=hf + 1):
        fid, ftype, country, lang, name, url = [c.value for c in row[:6]]
        if not fid or ftype == "X" or not url or url == "—" or (only and fid not in only):
            continue
        lang = str(lang or "").lower()
        words = kw.get(lang) or all_kw
        if ftype == "N":
            if not words:
                continue
            url = url.replace("{q}", google_query(words)).replace("when:7d", f"when:{max(a.days, 1)}d")
        try:
            raw = fetch(url)
            items = parse_tg_preview(raw) if ftype == "T" else parse_feed(raw)
            answered += 1
            result = f"{len(items)} items"
        except Exception as e:  # noqa: BLE001 — any network/parse problem is a gap, not a crash
            failed += 1
            result = f"error: {str(e)[:80]}"
            if not a.dry:
                ws_gap.append([now.strftime("%Y-%m-%d"), f"News feed {fid} {name}", url[:200], result,
                               "source blocked", "Try Google News for this portal or open it in a browser", "New"])
            print(f"{fid}: {result}")
            items = []
        new_here = 0
        for d, title, link, summ in items:
            if d and d.tzinfo is None:
                d = d.replace(tzinfo=now.tzinfo)
            if d and d < since:
                continue
            text = f"{title} {summ}".lower()
            hits = [w for w in words if matches(w, text)]
            if ftype in ("P", "T") and not hits:
                continue
            if not link or link in seen_urls or title.lower() in seen_titles:
                continue
            seen_urls.add(link)
            seen_titles.add(title.lower())
            new_here += 1
            found += 1
            if not a.dry:
                ws_sig.append([(d or now).strftime("%Y-%m-%d"), country, "News", name, title, link, summ,
                               "; ".join(hits[:5]), "", "", "PUBLIC", "", "To score", "No"])
            print(f"{fid}: + {title[:90]}")
        if not a.dry and not result.startswith("error"):
            result = f"{result}, new {new_here}"
        if not a.dry:
            row[9].value = now.strftime("%Y-%m-%d %H:%M")
            row[10].value = result

    if not a.dry:
        wb["Run_log"].append([now.strftime("%Y-%m-%d %H:%M"), f"news_slice {a.days}d",
                              f"feeds answered {answered}, failed {failed}", found, ""])
        wb.save(a.radar)
    print(f"feeds answered: {answered} · failed: {failed} · new news: {found}")


if __name__ == "__main__":
    main()
