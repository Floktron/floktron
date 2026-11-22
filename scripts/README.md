# scripts/ — the hands

Status: **18 parts ready, 1 planned.** Working versions are cleaned
(company names, addresses, paths and passwords moved to `config.yaml`) before they are added here.

| Planned file | What it does | Status |
|---|---|---|
| `base_create.py` | Creates an empty base (rays, tasks, routes, escalation, receipts, reports) | **ready (0.1.1)** |
| `send_morning.py` | Builds and sends the morning letters per ray | **ready (0.6.0)** — morning + evening (`--evening`), retry if the mail server does not answer, skips holidays |
| `collect_replies.py` | Reads replies from the mailbox, files them, writes receipts | **ready (0.3.0)** — button replies, OK/Q/NO, escalation, deadline |
| `route.py` | Turns replies into next tasks; repeat and escalation rules | **ready (0.4.0)** — runs automatically after collect_replies |
| `content_create.py` | Content workbook: Plan, Reserve, Media (what was published where), Run_log | **ready (0.7.0)** |
| `content_check.py` | Every morning: links pasted into `data/published_links.txt` → Published; posts of the day to copy; missed posts → today (status Scheduled waits for a link; missed twice → asks a person); the same picture never twice on one platform | **ready (0.14.0)** |
| `post_link.py` | Platform and exact publishing time from a post link (LinkedIn and X keep the time in the post ID) | **ready (0.14.0)** |
| `registry_lv.py` | New Latvian companies from open data (stream) by words in the name → Companies / Players | **ready (0.7.0)** |
| `gaps_report.py` | Weekly: what FLOKTRON could not do (by kind, with the fix) + runs that ended with an error → support | **ready (0.7.0)** |
| `mail/` | Adapters: `proton_bridge.py`, `gmail.py`, `outlook.py`, `imap.py` | **ready (0.3.0)**: `mail/send.py` + `mail/read.py` — Proton Bridge, Gmail, Outlook, any server |
| `backup_weekly.sh` | Weekly copy of the base and documents | planned |
| `install/` | Scheduler setup: macOS (launchd), Windows (Task Scheduler), Linux (cron) — see docs/INSTALL.md | **ready (0.6.0)** |
| `run.py` | One entry for the scheduler: morning · collect · deadline · evening · news · summary · status; lock + log | **ready (0.6.0)** |
| `weekly_summary.py` | One page for the manager: per ray done / not done (reasons) / open / no reply; open > 24 h; unknown senders | **ready (0.6.0)** |
| `calendar_days.py` | Working days with LV / LT / EE public holidays + company days off | **ready (0.6.0)** |
| `bot/telegram_bot.py` | Telegram bot: YAML dialog → leads (`data/floktron_leads.xlsx`), manager alert, source labels, funnel by step. Site-worker tasks — next | **ready (0.10.0)** |
| `radar_create.py` | Creates the radar workbook: keywords, sources, news feeds, signals, consultations, players, demand, gaps | **ready (0.5.0)** |
| `news_slice.py` | News by keywords from portal RSS and Google News → signals; failed feeds → Gaps | **ready (0.5.0)** |
| `calendar_read.py` · `ics.py` | Your calendar (.ics link, read only) in the morning message; .ics files for due dates and meetings | **ready (0.13.0)** |
| `invoices.py` | Invoices → accounting: AI-read supplier documents checked against the bank statement (CSV, or PDF with pypdf); duplicates, statuses, tasks for the finance ray, sheet Invoices | **ready (0.18.0)** |
| `snapshot.py` | Company snapshot: facts + base counts → branded PDF (EN / LV / RU) + JSON with status and source per figure; profiles partner / no_bank / tax / public; lock for secrets | **ready (0.19.0)** |
| `supply_watch.py` | Supply chain watch: prices, currencies, news and page changes of your Watchlist → Watch_log (🟢/🟡/🔴/⚪) | **ready (0.12.0)** |

## How to run (for now)
```
pip install openpyxl pyyaml
python3 scripts/base_create.py          # creates data/floktron_base.xlsx
python3 scripts/send_morning.py --dry   # builds morning messages into data/letters/<date>/
export FLOKTRON_MAIL_PASSWORD=...          # mailbox password (or macOS Keychain)
python3 scripts/send_morning.py --test you@mail.com   # one test message, base not changed
python3 scripts/collect_replies.py      # read replies, update tasks, escalate
python3 scripts/collect_replies.py --deadline   # at 09:00: who did not answer at all
python3 scripts/route.py --dry          # what next tasks the answers would create
python3 scripts/radar_create.py         # creates data/floktron_radar.xlsx — then fill in the keywords
python3 scripts/supply_watch.py --dry    # supply chain watch, show only (--full = weekly run)
python3 scripts/news_slice.py --days 7  # news of the last 7 days by the keywords (RSS, Google News, public Telegram channels)
export FLOKTRON_TG_TOKEN=...              # bot token from @BotFather
python3 scripts/bot/telegram_bot.py --flow-check   # check the dialog
python3 scripts/bot/telegram_bot.py --loop         # run the bot
```

`i18n.py` — message texts in EN / LV / RU (add a language by copying a block).
