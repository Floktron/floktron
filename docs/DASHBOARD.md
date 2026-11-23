# Dashboard — the whole system on one page

`data/dashboard.html` — open it by double-click on the computer, or from your cloud folder app on the phone
(put FLOKTRON's `data/` in iCloud / Google Drive / OneDrive, see [STORAGE](STORAGE.md)).

- **Works offline and sends nothing**: no internet, no outside fonts or scripts, a strict Content-Security-Policy;
  every text from your data is escaped.
- **Always fresh**: `scripts/run.py` rebuilds it after every run (collect, morning, news, …); the page re-reads itself every 15 minutes.
  Build by hand: `python3 scripts/run.py dashboard` (or `python3 scripts/dashboard.py`).

## What you see
| Block | From |
|---|---|
| Ring N/M + chips — which parts work | `data/run.log` (last run and exit code of each job), Telegram channel watch |
| Needs your attention | failed or late runs, overdue tasks, questions from people, deadlines within 3 days |
| Coming up | open consultations with a deadline (radar) |
| Rays — who confirmed today's tasks | sheets Rays / Tasks / Receipts of `floktron_base.xlsx` (test rays are marked) |
| Open tasks · answers for 14 days | Tasks, Receipts |
| Voice reports · audio summary player | `voice_reports.xlsx`, `pulse_*.m4a` ([VOICE](VOICE.md)) |
| Invoices → accounting | sheet Invoices ([INVOICES](INVOICES.md)) |
| Mail waits for you — waiting for you, starred without an answer, messages in 7 days, up to 10 rows | sheet Mail ([MAIL_WATCH](MAIL_WATCH.md)); a confirm / reply older than a day also goes to *Needs your attention* |
| Posts today · radar signals · supply chain | `floktron_content.xlsx` Plan, `floktron_radar.xlsx` Signal_feed / Watch_log |

Language follows `company.language` (en, ru, lv); colours follow `colors.main` / `colors.ok`.
The page holds your internal data — do not publish it on the web.
