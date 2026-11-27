# Dashboard — the whole system on one page

`data/dashboard.html` — open it by double-click on the computer, or from your cloud folder app on the phone
(put FLOKTRON's `data/` in iCloud / Google Drive / OneDrive, see [STORAGE](STORAGE.md)).

- **Works offline and sends nothing**: no internet, no outside fonts or scripts, a strict Content-Security-Policy;
  every text from your data is escaped.
- **Always fresh**: `scripts/run.py` rebuilds it after every run (collect, morning, news, …); the page re-reads itself every 15 minutes.
  Build by hand: `python3 scripts/run.py dashboard` (or `python3 scripts/dashboard.py`).

## Icon on the desktop — open the dashboard with one double-click
`python3 scripts/desktop_icon.py` puts a FLOKTRON icon on the desktop: on a Mac `FLOKTRON.app`, on Windows the
shortcut `FLOKTRON.lnk`, on Linux `floktron.desktop` (also in the applications menu). Double-click it: the dashboard is
rebuilt from the latest data and opens in your default browser. Nothing is downloaded, nothing keeps running, no admin
rights. `--remove` takes the icon away; moved the FLOKTRON folder — run the script again. On a Mac, the first time only:
if the Mac asks, right-click the icon → Open → Open. The page itself also shows the FLOKTRON mark in the browser tab.

## What you see
| Block | From |
|---|---|
| Ring N/M + chips — which parts work | `data/run.log` (last run and exit code of each job), Telegram channel watch |
| Needs your attention | failed or late runs, overdue tasks, questions from people, deadlines within 3 days |
| Coming up | open consultations with a deadline (radar) |
| Online meetings — date, time, service, the official join link in full, ID and passcode; a trick link only as a red warning | `data/meetings.json` from `scripts/meeting_links.py` (your calendar + invitation letters, [MEETINGS](MEETINGS.md)); a meeting within the hour also goes to the top of *Needs your attention* |
| Rays — who confirmed today's tasks | sheets Rays / Tasks / Receipts of `floktron_base.xlsx` (test rays are marked) |
| Work time — at work now, hours today and this month, overtime, night, weekend, what to check | `data/worktime.jsonl`, marks from the bot ([WORKTIME](WORKTIME.md)); no end mark or a start far from the site also goes to *Needs your attention* |
| Site cameras — online / no fresh frame, the latest frame, a button to open the camera; public webcams only as marked *examples* (link) | `config.yaml → cameras`, frames from `scripts/cameras.py snap` in `data/cameras/` ([CAMERAS](CAMERAS.md)); a camera without a fresh frame also goes to *Needs your attention* |
| Open tasks · answers for 14 days | Tasks, Receipts |
| Voice reports · audio summary player | `voice_reports.xlsx`, `pulse_*.m4a` ([VOICE](VOICE.md)) |
| Invoices → accounting | sheet Invoices ([INVOICES](INVOICES.md)) |
| Mail waits for you — waiting for you, starred without an answer, messages in 7 days, up to 10 rows | sheet Mail ([MAIL_WATCH](MAIL_WATCH.md)); a confirm / reply older than a day also goes to *Needs your attention* |
| New customers: why now — new prospects, priority 1, up to 6 rows with the reason and the town | sheet Prospects in the radar base ([PROSPECTS](PROSPECTS.md)) |
| Posts today · radar signals · supply chain | `floktron_content.xlsx` Plan, `floktron_radar.xlsx` Signal_feed / Watch_log |

Language follows `company.language` (en, ru, lv); colours follow `colors.main` / `colors.ok`.
The page holds your internal data — do not publish it on the web.
