# -*- coding: utf-8 -*-
"""FLOKTRON · radar_create.py — creates the radar workbook (data/floktron_radar.xlsx). Run once.

The radar is what FLOKTRON watches outside the company: keywords, news feeds, public consultations,
tenders, company registries, search demand. It contains NO company data — the client fills in
keywords at setup; the source catalogue below is a neutral starting list of public sources.

Usage:
    python3 scripts/radar_create.py                 # languages from config/config.yaml (radar.languages)
    python3 scripts/radar_create.py --force         # overwrite
    python3 scripts/radar_create.py --add-watch     # add the supply-chain sheets (Watchlist, Watch_log) to an existing radar
Options: --config <file>  --out <file>
"""
import argparse
import datetime
import os
import sys

try:
    import openpyxl
    import safe_xlsx  # noqa: F401 — outside text never becomes a formula
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    sys.exit("Missing package: run  pip install openpyxl")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILL = PatternFill("solid", fgColor="1A365D")
FONT = Font(bold=True, color="FFFFFF")

# Neutral catalogue of public sources (Baltics, Nordics/DACH, EU). Access notes come from real runs;
# "check" = not verified yet. Remove what the client does not need.
SOURCES = [
    # type, country, name, what we take, frequency, url, method, access
    ["Search", "All", "Web search (Google / Bing)", "Keywords priority A, all languages", "Weekly", "—", "AI agent web search", "OK"],
    ["Search demand", "All", "Google Trends", "Weekly series for fixed comparison sets", "Weekly", "https://trends.google.com", "Browser (explore + widget API)", "OK, rate-limited"],
    ["Tenders", "EU/EEA", "TED — EU tenders", "Notices by CPV and keywords", "Weekly", "https://api.ted.europa.eu/v3/notices/search", "Public API (POST)", "OK"],
    ["Tenders", "LV", "EIS — e-iepirkumi", "Municipal and state tenders", "Weekly", "https://www.eis.gov.lv", "Browser", "check"],
    ["Tenders", "LT", "CVP IS", "Public procurement", "Weekly", "https://cvpp.eviesiejipirkimai.lt", "Browser", "check"],
    ["Tenders", "EE", "Riigihangete register", "Public procurement", "Weekly", "https://riigihanked.riik.ee", "Browser", "check"],
    ["Consultations", "LV", "TAP portāls — public participation", "Draft laws and regulations open for opinion (14-day window)", "Weekly", "https://tapportals.mk.gov.lv/public_participation", "Browser; daily e-mail digest possible", "OK in browser, blocked for plain download"],
    ["Consultations", "LV", "Municipality draft regulations (e.g. Riga)", "Draft binding regulations, committee calendar", "Weekly", "https://www.riga.lv", "Browser", "OK in browser"],
    ["Consultations", "EE", "Eelnõude infosüsteem (EIS)", "Draft acts and consultations", "Weekly", "https://eelnoud.valitsus.ee", "Browser", "check"],
    ["Consultations", "LT", "E-seimas / TAIS", "Draft legal acts", "Weekly", "https://e-seimas.lrs.lt", "Browser", "check"],
    ["Consultations", "EU", "Have your say (European Commission)", "EU initiatives open for feedback", "Monthly", "https://ec.europa.eu/info/law/better-regulation/have-your-say", "Browser", "check"],
    ["Registry", "LV", "Uzņēmumu reģistrs — open data", "New registrations (register.csv, daily)", "Weekly", "https://data.gov.lv/dati/lv/dataset/uz", "Open data CSV (~130 MB, stream)", "OK"],
    ["Registry", "LV/LT/EE", "firmas.lv — new companies", "New registrations LV, LT, EE", "Weekly", "https://www.firmas.lv/lv/uznemumi/jauni", "Browser, pages of 20", "OK"],
    ["Registry", "EE", "e-Äriregister", "Company card, EMTAK code, public contacts", "On demand", "https://ariregister.rik.ee", "Browser", "OK"],
    ["Registry", "LT", "Registrų centras / Rekvizitai", "Company card", "On demand", "https://www.registrucentras.lt", "Browser", "Rekvizitai blocks automated runs"],
    ["Registry", "DE/AT/CH", "North Data / Firmenbuch / Zefix", "New registrations, company card", "Monthly", "https://www.northdata.de", "Browser", "OK (North Data)"],
    ["Registry", "LV", "Lursoft", "Company card, financials", "On demand", "https://www.lursoft.lv", "Paid", "needs subscription"],
]

FEEDS = [
    # id, type (P = portal RSS, N = Google News query, T = public Telegram channel t.me/s/<name>, X = do not open), country, language, portal / query, url, filter, priority, access
    ["P01", "P", "LV", "lv", "LSM", "https://www.lsm.lv/rss/", "keywords", "A", "OK"],
    ["P02", "P", "LV", "lv", "TVNET", "https://www.tvnet.lv/rss", "keywords", "A", "OK"],
    ["P03", "P", "LV", "lv", "LV portāls", "https://lvportals.lv/rss", "keywords", "B", "sometimes refuses"],
    ["P04", "P", "EE", "et", "ERR", "https://www.err.ee/rss", "keywords", "A", "HTTP 403 (Cloudflare) — use Google News"],
    ["P05", "P", "EE", "et", "Postimees", "https://www.postimees.ee/rss", "keywords", "B", "check"],
    ["P06", "P", "LT", "lt", "LRT", "https://www.lrt.lt/rss", "keywords", "A", "OK"],
    ["P07", "P", "LV/EN", "en", "BNN", "https://bnn-news.com/feed", "keywords", "B", "OK"],
    ["X01", "X", "LV", "lv", "Delfi", "—", "—", "—", "do not open (high risk) — comes via Google News"],
    ["X02", "X", "LT", "lt", "15min", "—", "—", "—", "do not open (Cloudflare) — comes via Google News"],
    ["T01", "T", "LV", "lv", "Public Telegram channel (fill in)", "—", "keywords", "B", "replace — with https://t.me/s/<channel>; only public channels"],
    ["N01", "N", "LV", "lv", "Google News LV · keywords A (LV)", "https://news.google.com/rss/search?q={q}+when:7d&hl=lv&gl=LV&ceid=LV:lv", "query", "A", "OK"],
    ["N02", "N", "LT", "lt", "Google News LT · keywords A (LT)", "https://news.google.com/rss/search?q={q}+when:7d&hl=lt&gl=LT&ceid=LT:lt", "query", "A", "OK"],
    ["N03", "N", "EE", "et", "Google News EE · keywords A (ET)", "https://news.google.com/rss/search?q={q}+when:7d&hl=et&gl=EE&ceid=EE:et", "query", "A", "OK"],
    ["N04", "N", "DE", "de", "Google News DE · keywords A (DE)", "https://news.google.com/rss/search?q={q}+when:7d&hl=de&gl=DE&ceid=DE:de", "query", "B", "OK"],
    ["N05", "N", "EN", "en", "Google News EN · keywords A (EN)", "https://news.google.com/rss/search?q={q}+when:7d&hl=en&gl=GB&ceid=GB:en", "query", "B", "OK"],
]


WATCH_HEAD = ["ID", "Group", "Object", "Country", "Why it matters to us", "News query", "News languages", "Ticker",
              "Page URL", "Yellow %", "Red %", "Mode", "Active", "Data status", "Comment"]
# Neutral examples (reference prices, currencies, freight). Replace with what YOU buy and from whom.
WATCH_EXAMPLE = [
    ["S01", "Supplier", "Your main supplier (fill in)", "", "what you buy from them", '"Supplier name"', "en", "—",
     "https://example.com", "", "", "daily", "No", "PUBLIC", "example row — fill in, then Active = Yes"],
    ["M01", "Producer", "A big listed producer of your raw material (fill in)", "", "sets market prices", "Company name",
     "en", "TICKER", "", "5", "10", "daily", "No", "PUBLIC", "ticker as on finance.yahoo.com, e.g. HEI.DE"],
    ["L01", "Logistics", "Asia–Europe container route", "", "cost and time of sea freight",
     '"Red Sea" shipping OR Suez (closure OR attack OR diversion)', "en", "—", "", "", "", "daily", "Yes", "PUBLIC", ""],
    ["P01", "Price", "Aluminium (COMEX future)", "", "reference price, not your purchase price", "—", "", "ALI=F", "",
     "10", "20", "daily", "Yes", "PUBLIC", ""],
    ["P02", "Price", "Natural gas TTF (EU)", "", "energy cost of EU chemical and building-material plants", "—", "",
     "TTF=F", "", "10", "20", "daily", "Yes", "PUBLIC", ""],
    ["P03", "Currency", "EUR/USD", "", "freight and raw materials in USD", "—", "", "EURUSD=X", "", "3", "5", "daily",
     "Yes", "PUBLIC", ""],
    ["R01", "Rule", "EU anti-dumping on your inputs (fill in)", "EU", "duties change landed cost",
     "EU anti-dumping China \"product name\"", "en", "—", "", "", "", "weekly", "No", "PUBLIC", ""],
]
WATCH_LOG_HEAD = ["Date", "ID", "Object", "Measure", "Value", "Unit", "Δ day %", "Δ 5 days %", "Status",
                  "Event / news", "URL", "Data status", "Run"]


def add_watch(wb, cfg=None):
    ws = sheet(wb, "Watchlist", WATCH_HEAD, WATCH_EXAMPLE, [6, 11, 32, 8, 32, 44, 12, 12, 34, 8, 8, 9, 8, 11, 34],
               note="INTERNAL. Supply chain watch (supply_watch.py): one row per supplier, producer, route, price or rule "
                    "you depend on. Groups: Supplier · Producer · Logistics · Price · Currency · Rule. Ticker as on "
                    "finance.yahoo.com. Yellow % / Red % = alarm for a 5-day move (empty → config). Mode: daily / weekly. "
                    "Never put recipes, quantities or contract prices here.")
    dv = DataValidation(type="list", formula1='"Supplier,Producer,Logistics,Price,Currency,Rule"')
    ws.add_data_validation(dv)
    dv.add("B4:B500")
    dv2 = DataValidation(type="list", formula1='"Yes,No"')
    ws.add_data_validation(dv2)
    dv2.add("M4:M500")
    sheet(wb, "Watch_log", WATCH_LOG_HEAD, widths=[11, 6, 30, 16, 14, 9, 9, 10, 14, 60, 40, 22, 18],
          note="INTERNAL. What supply_watch.py measured. 🟢 normal · 🟡 attention · 🔴 urgent · ⚪ no data. "
               "'candidate' = alarm word in a news title — the AI agent reads it and confirms or lowers the status.")


def sheet(wb, name, head, rows=(), widths=None, note=None, first=False):
    ws = wb.active if first else wb.create_sheet(name)
    ws.title = name
    r0 = 1
    if note:
        ws.cell(1, 1, note).font = Font(italic=True, color="717171")
        r0 = 3
    for i, h in enumerate(head, 1):
        c = ws.cell(r0, i, h)
        c.fill, c.font = FILL, FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows:
        ws.append(list(r))
    for i, w in enumerate(widths or [18] * len(head), 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    return ws


def build(cfg):
    radar = cfg.get("radar") or {}
    langs = radar.get("languages") or ["en", "lv"]
    company = (cfg.get("company") or {}).get("name", "")
    today = datetime.date.today().isoformat()
    wb = openpyxl.Workbook()

    sheet(wb, "README", [f"FLOKTRON radar · {company or 'your company'} · created {today}"], [
        ["Keywords — what to look for, one row per idea, one column per language. Priority A = every run, B = first run of the month."],
        ["Sources — where to look (tenders, consultations, registries, search). News_feeds — RSS of news portals and Google News queries."],
        ["Signal_feed — everything found that matters. Relevance 1–5; the AI agent scores it and proposes an action (post, letter, offer)."],
        ["Consultations — public consultations and draft regulations, with deadlines. Write opinions only while a consultation is OPEN."],
        ["Players — other companies in the niche. INTERNAL: never copy into external documents or posts."],
        ["Demand / Demand_history — search interest (Google Trends index 0–100, relative to its comparison set, not absolute numbers)."],
        ["Watchlist / Watch_log — INTERNAL supply chain watch: suppliers, producers, logistics, reference prices, rules (supply_watch.py)."],
        ["Gaps — what FLOKTRON could not get and why (site blocked, needs subscription, function missing, client wish). Weekly report to the client."],
        ["Every figure carries a status: PUBLIC / ESTIMATE / SCENARIO / DEAL, and a source."],
    ], [130], first=True)

    ws = sheet(wb, "Keywords", ["ID", "Cluster"] + [f"Keyword {l.upper()}" for l in langs] +
               ["Priority", "Signal type", "In Trends set", "Comment"],
               [["K01", "Core demand"] + ["" for _ in langs] + ["A", "Demand", "", "example row — replace"]],
               [6, 22] + [30] * len(langs) + [9, 16, 12, 30],
               note="One idea per row, translated into every working language. Priority A = every run, B = first run of the month. "
                    "Write whole words (they are also used for Google News); other endings are found automatically.")
    dv = DataValidation(type="list", formula1='"A,B"')
    ws.add_data_validation(dv)
    dv.add(f"{get_column_letter(3 + len(langs))}4:{get_column_letter(3 + len(langs))}500")

    sheet(wb, "Sources", ["Type", "Country", "Source", "What we take", "Frequency", "URL", "Method", "Access", "Last check"],
          [s + [""] for s in SOURCES], [14, 9, 34, 40, 11, 44, 30, 30, 12],
          note="Neutral starting list of public sources. Access 'check' = not verified yet. Remove what you do not need.")
    sheet(wb, "News_feeds", ["ID", "Type", "Country", "Language", "Portal / query", "Feed URL", "Filter",
                             "Priority", "Access", "Last check", "Last result"],
          [f + ["", ""] for f in FEEDS], [6, 6, 8, 9, 34, 60, 10, 9, 36, 12, 30],
          note="P = portal RSS, filtered by keywords · N = Google News query, {q} is replaced by keywords · X = never open. "
               "news_slice.py reads this sheet.")
    sheet(wb, "Signal_feed", ["Date", "Country", "Type", "Source", "Title", "URL", "Summary", "Keywords", "Segment",
                              "Relevance 1–5", "Data status", "Action", "Work status", "Internal"],
          widths=[11, 8, 16, 18, 50, 40, 50, 12, 16, 10, 12, 40, 12, 9],
          note="Types: News · Tender · Consultation · Event · Funding · Registration · Competitor · Demand. No duplicates by URL.")
    sheet(wb, "Consultations", ["ID", "Title", "Type", "Open from", "Open until", "Institution", "Keywords",
                                "Relevance", "What it means for us", "Action", "Work status", "URL", "Recorded"],
          widths=[14, 50, 14, 11, 11, 24, 12, 9, 40, 30, 14, 40, 11],
          note="Write an opinion only while the consultation is open. Closed ones — watch only.")
    sheet(wb, "Players", ["Company", "Country", "Reg. no.", "Role", "Where seen", "URL", "Facts", "Relation to us",
                          "Data status", "Next step"], widths=[28, 8, 14, 22, 24, 36, 40, 24, 12, 24],
          note="INTERNAL. Personal data — only what open business registries show.")
    sheet(wb, "Demand", ["Region", "Language", "Keyword", "Comparison set", "Keyword ID", "Avg 12 months (base)",
                         "Last 4 weeks", "Change", "Alert"], widths=[8, 9, 30, 12, 10, 14, 12, 10, 8],
          note="Google Trends: compare only inside one set (5 keywords, same region). Alert = change ≥ +10 % and index ≥ 5.")
    sheet(wb, "Demand_history", ["Date", "Region", "Keyword", "Set", "Avg 12 months", "Note"],
          widths=[11, 8, 30, 10, 12, 60])
    sheet(wb, "Registry_queries", ["ID", "Country", "Words in company name (; separated)", "Goal", "Exclude words",
                                   "Company types", "Active"],
          [["R01", "LV", "", "Client", "", "SIA;IK;AS", "Yes"]], [6, 8, 50, 12, 30, 14, 8],
          note="What to look for among NEW companies in registries. Goal: Client · Channel · Competitor. "
               "Words are matched by stem in the company name. registry_lv.py reads this sheet.")
    sheet(wb, "Companies", ["Found", "Country", "Reg. no.", "Name", "Type", "Registered", "Address", "Matched",
                            "Goal", "Query", "Contacts (public, company only)", "Data status", "Work status"],
          widths=[11, 8, 14, 40, 8, 11, 40, 20, 11, 7, 36, 12, 12],
          note="New registrations that match Registry_queries. Only general company contacts published by the "
               "company or the registry. Nobody is contacted automatically.")
    ws = sheet(wb, "Gaps", ["Date", "What was wanted", "Source / function", "What happened", "Kind", "Proposed fix",
                            "Status"], widths=[11, 40, 30, 40, 18, 40, 12],
               note="Kinds: source blocked · needs subscription · function missing · client wish · data quality. "
                    "Goes to the client weekly — this is the list of improvements.")
    dv = DataValidation(type="list",
                        formula1='"source blocked,needs subscription,function missing,client wish,data quality"')
    ws.add_data_validation(dv)
    dv.add("E4:E2000")
    add_watch(wb, cfg)
    sheet(wb, "Run_log", ["Date/time", "Run", "What was done", "New signals", "Comment"],
          [[datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "radar_create", "empty radar created", 0, ""]],
          [17, 18, 60, 12, 50])
    return wb


def main():
    ap = argparse.ArgumentParser(description="Create the FLOKTRON radar workbook.")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "floktron_radar.xlsx"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--add-watch", action="store_true", help="add Watchlist + Watch_log to an existing radar")
    a = ap.parse_args()
    cfg0 = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg0 = yaml.safe_load(f) or {}
    if a.add_watch:
        if not os.path.exists(a.out):
            sys.exit(f"No radar yet: {a.out} — run without --add-watch first")
        wb = openpyxl.load_workbook(a.out)
        if "Watchlist" in wb.sheetnames:
            sys.exit("Watchlist already exists — nothing changed")
        add_watch(wb, cfg0)
        wb.save(a.out)
        print("OK: Watchlist + Watch_log added to", a.out)
        return
    if os.path.exists(a.out) and not a.force:
        sys.exit(f"Radar already exists: {a.out}  (use --force to overwrite)")
    cfg = {}
    if os.path.exists(a.config):
        import yaml
        with open(a.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    build(cfg).save(a.out)
    print("OK:", a.out)


if __name__ == "__main__":
    main()
