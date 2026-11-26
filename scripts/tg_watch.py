# -*- coding: utf-8 -*-
"""FLOKTRON · tg_watch.py — watch public Telegram channels for your keywords; tell the manager in Telegram.

Channels: a text file, one public channel name per line (# comments). The bot adds channels for you when
a manager forwards it a post from a channel (telegram.channels_file). Pages read: https://t.me/s/<channel>
(public web preview, no Telegram account, phone or API key). Keywords: a plain text file or an .xlsx column.
New matches → <data_dir>/tg_signals.xlsx (no duplicates) + one Telegram message per match to the managers
(with the bot token, if set). Usage:
    python3 scripts/tg_watch.py --config <config.yaml> [--dry]
config.yaml → telegram: {channels_file, data_dir, manager_chat_ids, keychain_service/token_env,
                         keywords_xlsx, keywords_sheet, keywords_columns: [LV, RU, EN], keywords_priority: [A, B]}
                         or keywords_file: one keyword per line
"""
import argparse, datetime, json, os, re, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "bot"))
from news_slice import matches, parse_tg_preview  # noqa: E402
import telegram_bot as tb  # noqa: E402

UA = "Mozilla/5.0 (FLOKTRON channel watch)"


def keywords(cfg, base):
    out = []
    if cfg.get("keywords_file"):
        p = os.path.join(base, os.path.expanduser(cfg["keywords_file"]))
        out = [l.split("#")[0].strip() for l in open(p, encoding="utf-8")]
    elif cfg.get("keywords_xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(os.path.join(base, os.path.expanduser(cfg["keywords_xlsx"])), read_only=True)
        rows = list(wb[cfg.get("keywords_sheet", "Keywords")].iter_rows(values_only=True))
        h = next(i for i, r in enumerate(rows) if r and str(r[0]).strip() == "ID")
        head = [str(c or "").strip() for c in rows[h]]
        cols = [head.index(c) for c in cfg.get("keywords_columns", ["LV", "RU", "EN"]) if c in head]
        pr = head.index("Приоритет") if "Приоритет" in head else head.index("Priority") if "Priority" in head else None
        want = set(cfg.get("keywords_priority", ["A", "B"]))
        for r in rows[h + 1:]:
            if not r or not r[0] or (pr is not None and str(r[pr] or "").strip() not in want):
                continue
            for c in cols:
                out += re.split(r"[;,]", str(r[c] or ""))
    clean = []
    for k in out:
        k = re.sub(r"[«»\"()®™]", " ", k).strip()
        if len(k) >= 4 and k.lower() not in {x.lower() for x in clean}:
            clean.append(k)
    return clean


def channels(path):
    if not os.path.exists(path):
        return []
    names = [l.split("#")[0].strip().lstrip("@") for l in open(path, encoding="utf-8")]
    return [n for n in names if re.match(r"^[A-Za-z0-9_]{4,64}$", n)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    run(a.config, a.dry)


def run(config, dry=False):
    """One watch pass. Also called by the bot itself at telegram.watch_times (one process, no extra scheduler)."""
    class A:  # keep the body below unchanged
        pass
    a = A(); a.config, a.dry = config, dry
    base = os.path.dirname(os.path.abspath(a.config))
    cfg = tb.load_yaml(a.config).get("telegram") or {}
    data = os.path.join(base, os.path.expanduser(cfg.get("data_dir") or "data")); os.makedirs(data, exist_ok=True)
    chs = channels(os.path.join(base, os.path.expanduser(cfg.get("channels_file") or "channels.txt")))
    kws = keywords(cfg, base)
    print(f"{tb.now_str()} channels {len(chs)} · keywords {len(kws)}")
    seen_p = os.path.join(data, "tg_seen.json")
    seen = set(json.load(open(seen_p))) if os.path.exists(seen_p) else set()
    import openpyxl
    import safe_xlsx  # noqa: F401 — post text never becomes a formula
    out_p = os.path.join(data, "tg_signals.xlsx")
    if os.path.exists(out_p):
        wb = openpyxl.load_workbook(out_p)
    else:
        wb = openpyxl.Workbook(); wb.active.title = "Signals"
        wb.active.append(["Found", "Post date", "Channel", "Post URL", "Text", "Keywords", "Status"])
        wb.create_sheet("Runs").append(["Run", "Channels", "Answered", "Failed", "New matches"])
    api = None
    if not a.dry and cfg.get("manager_chat_ids"):
        try:
            api = tb.Api(tb.token_from(cfg))
        except tb.BotError as e:
            print("no bot token — Excel only:", e)
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=int(cfg.get("watch_days", 3)))
    new = ok = bad = 0
    for ch in chs:
        try:
            req = urllib.request.Request(f"https://t.me/s/{ch}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:  # nosec B310 - fixed https:// address
                items = parse_tg_preview(r.read(3_000_000)); ok += 1
        except Exception as e:  # noqa: BLE001
            bad += 1; print(f"@{ch}: {str(e)[:80]}"); continue
        for d, title, link, text in items:
            if link in seen or (d and d < since):
                continue
            hits = [k for k in kws if matches(k, text)]
            seen.add(link)
            if not hits:
                continue
            new += 1
            print(f"@{ch}: + {title[:80]}  [{', '.join(hits[:3])}]")
            if a.dry:
                continue
            wb["Signals"].append([tb.now_str(), d.strftime("%Y-%m-%d %H:%M") if d else "", "@" + ch, link, text,
                                  "; ".join(hits[:5]), "To score"])
            for m in cfg.get("manager_chat_ids") or []:
                if api:
                    try:
                        api.call("sendMessage", chat_id=int(m), disable_web_page_preview=True,
                                 text=f"📡 @{ch} · {', '.join(hits[:3])}\n{title}\n{link}")
                        time.sleep(0.5)
                    except tb.BotError as e:
                        print("send:", e)
    if not a.dry:
        wb["Runs"].append([tb.now_str(), len(chs), ok, bad, new]); wb.save(out_p)
        json.dump(sorted(seen)[-20000:], open(seen_p, "w"))
    print(f"answered {ok} · failed {bad} · new matches {new}")
    return new


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    main()
