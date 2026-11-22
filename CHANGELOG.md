# Changelog

History of FLOKTRON. Newest first.
Every change in this repository is also a git commit with date and description — the full archive.

## 0.16.0 — 22.11.2026 · voice and a dashboard
Learned in real use: people on site do not type reports, and a manager in the car cannot read a table.
- **Voice reports** (`scripts/voice.py`, Telegram bot): a team member sends a voice message → text on your own computer
  (local Whisper model; ElevenLabs only if you choose it) → `data/voice_reports.xlsx`, a reply with what was understood,
  the text to the manager. Only people listed in `telegram.voice.users`; strangers are asked to write. Audio is kept if
  the text cannot be made.
- **Audio summary**: the morning AI run writes `pulse_<date>.txt`, the bot reads it aloud with the system voice and sends it
  to the manager once a day; `/pulse` — again.
- **Dashboard** (`scripts/dashboard.py` → `data/dashboard.html`): health ring, needs-your-attention, rays, open tasks,
  answers for 14 days, voice reports, posts, radar, supply chain, audio player. Offline, escaped, strict CSP; rebuilt after every run (`run.py dashboard`). EN / RU / LV.
- Docs: [VOICE](docs/VOICE.md), [DASHBOARD](docs/DASHBOARD.md); TRANSPARENCY lists the optional ElevenLabs connection and the
  local speech tools; config example has the `voice` block. Tests: `test_voice.py`, `test_dashboard.py` (no network) — 72 checks.
- From this version on every version is also a **GitHub Release** with a tag (v0.16.0 is the first): after each push,
  `.github/workflows/release.yml` sees a new version in README, runs all tests and publishes the CHANGELOG section as the release text.

## 0.15.2 — 21.11.2026 · always the live version
Learned in real use: an AI assistant given the repository link answered from a cached copy two days old (0.13.1) and
did not know about the security checkup.
- AGENTS.md starts with *make sure you read the live version*: compare with the first entry of the raw CHANGELOG; if older,
  read the raw files (`llms-full.txt`) instead of the cached copy, and tell the person which version is used.
- README and llms.txt carry the same note; `llms-full.txt` / START.md now state their version (taken from README automatically).

## 0.15.1 — 21.11.2026 · overview PDF 1.3
- `docs/FLOKTRON_overview.pdf` (version 1.3): *Data and security* now says that setup ends with a security checkup; open version 0.15, 61 automated tests. Other languages on the KOAGU site were updated the same day.

## 0.15.0 — 21.11.2026 · setup ends with a security checkup
Your data stays with you — so you protect it, not luck. Every setup now ends with a check of your own computer.
- `scripts/security_check.py` — read-only checkup for macOS (Apple silicon and Intel), Windows 10/11 and Linux: FLOKTRON
  folder (no passwords in files, permissions, cloud version history), user account, disk encryption, firewall, updates,
  screen lock, backups, programs that start by themselves, ports open to the network. Marks ✅ ⚠️ ❌ ❔ ℹ️, each with
  "how to fix" — the person makes every change. Changes nothing, needs no admin password, sends nothing; the report
  stays in `data/`. `--manual` adds the list no script can see: 2-step login, cloud encryption, 3-2-1 backups, router,
  app permissions, sandbox for unknown files, free extra tools.
- `docs/SECURITY_CHECKUP.md` — where your data lives and what protects it, mode A / mode B (paste the text or a screenshot).
- Setup wizard v0.6: new step 12 *Security checkup* — never skipped; hand-over includes its result. Announced at step 0.
- AGENTS.md: the person hears about the checkup before any step; safety rule 11 — the checkup only reads, the agent
  never changes security settings or asks for an admin password.
- README, SECURITY, TRANSPARENCY, INSTALL updated. Tests: read-only commands only, port parsing for all three systems,
  password detection, report saved locally.

## 0.14.0 — 21.11.2026 · "published" is checked, not guessed
Learned in real use: a post on a *personal* LinkedIn profile went out on time, but only the company page was checked
and nobody pasted the link — FLOKTRON called it missed for two days and kept moving it.
- **Links file** `data/published_links.txt` (created by `content_create.py`): published a post → paste its link,
  one line, from the phone is fine. Every morning `content_check.py` matches each line to the plan (platform from the
  link, date from the link or the note, ±1 day), sets Published + link, marks the picture in `Media` and moves the
  line under `## DONE`. A line it cannot match stays with "← no matching post" and is reported.
- **Status `Scheduled`** — set in the platform's scheduler. After its date it is **not** moved: "waiting for a link".
- **Missed twice** → no silent moving from day to day: the post is flagged and the person decides (publish by hand or cancel).
- The morning letter has a **"Needs you"** block (waiting for a link, missed twice, links not matched) and is sent
  even on a day without posts when something needs a person.
- `scripts/post_link.py`: platform and exact publishing time from a link — LinkedIn and X keep the time in the post
  ID (feeds only say "1d").
- `prompts/41_published_check.md`: the AI agent checks in three places — links file → plan → live profile
  (read only), including the person's own profile for posts and reposts made as a person, and X's scheduled list.
  A page that asks to sign in never makes a post "missed". Run in the evening slice (step 0) and before moving posts.
- `config.yaml → content`: `notify`, `links_file`, `profiles` (pages the agent may read). Setup wizard step 9 asks for them.
- Tests: link time/platform, links file, Scheduled, missed twice (54 in total).

## 0.13.6 — 20.11.2026 · written reports count
- `collect_replies.py`: a written report sent with a plain «Reply» (or the 📝 evening button) now closes tasks. Before, only the per-task buttons did — a report typed into the reply was saved but the tasks stayed open, and the same tasks came again the next morning. Learned in real use.
- The report can be lines (`2 + meeting on Tuesday`, `T005 - nobody answered`) or a table pasted from a spreadsheet (number, sign and comment in different cells). N = the task's number in that message, or its task ID.
- `+` `✅` `*` → Done · `-` `−` `❌` → Not done (goes to the team lead and the route, as with buttons). A plain reply without lines counts as «Accepted».
- A report that matches no task is flagged «Report not recognised» in Receipts — nothing is lost silently.
- Tests: table report, plain lines, own outgoing message ignored.

## 0.13.5 — 20.11.2026 · for any field
- FLOKTRON is described for anyone who runs work, in any field — from one person (a social-media manager, a freelancer) to a company with departments (online shop, logistics, production, services, construction). Construction is one example, not the target.
- The site module is now a field module: anyone out of the office — warehouse, road, site — ticks off work in a bot.
- `docs/FLOKTRON_overview.pdf` updated (version 1.2).

## 0.13.4 — 19.11.2026 · overview in English, any size
- `docs/FLOKTRON_overview.pdf`: the overview by rays is now in English (the repository language); other languages live on koagu.com/floktron.
- FLOKTRON is described for teams and companies of any size — from a crew of three to a developer running several sites — not only small companies.

## 0.13.3 — 19.11.2026 · overview PDF
- `docs/FLOKTRON_overview_RU.pdf`: overview by rays to read before installing — daily cycle, how it is built, the 8 rays with their tools, radars, connectors, what else can be plugged in, data and security, status. Linked from the README. English version next.
- Cost of the AI engine stated honestly: a basic subscription (about 20 € a month) is enough to set up and run FLOKTRON every day; a higher plan only gives more room for heavy use.

## 0.13.2 — 19.11.2026 · own contact address
- Contact for FLOKTRON is now **floktron@koagu.com** (support, licence, security reports) — README, AGENTS, SECURITY, LICENSING, FEEDBACK, TRANSPARENCY, llms-full. The company address is no longer used for the project; commits are signed with the project address too.

## 0.13.1 — 19.11.2026 · long calendar links
- Mac: `calendar_link.command` read the link through the system password prompt, which cuts input at 128 characters — Proton and Google links are longer and came back as HTTP 404. The link is now read in full, its length is shown, and anything that is not an https/webcal link is refused. Learned in real use.
- `calendar_read.py --diagnose`: shows the shape of the link with every secret part hidden (host, path, parameter names, length) — safe to send to support; a 404 explains what to do.

## 0.13.0 — 19.11.2026 · calendar + one setup path
- `scripts/calendar_read.py`: reads YOUR calendar through its private read-only `.ics` link — Proton, Google, Outlook / Microsoft 365, Apple iCloud, Nextcloud, any other that gives one. The link is kept like a password (environment variable `FLOKTRON_CAL_URL` or the Keychain item `FLOKTRON_CAL`; Mac: `scripts/install/calendar_link.command`). FLOKTRON never writes to the calendar.
- Morning message: *"Today in your calendar"* above the tasks for the rays in `calendar.rays`; `calendar.busy_only` shows only "busy". Every morning message gets an `.ics` with the due dates of its tasks — one tap adds them. A calendar that does not answer never stops the letters.
- `scripts/ics.py`: reads `.ics` (UTC and local times with TZID, all-day, folded lines, repeating events DAILY / WEEKLY with BYDAY / MONTHLY / YEARLY with INTERVAL, COUNT, UNTIL, EXDATE, cancelled events) and writes `.ics` files for due dates, meetings and schedules (`python3 scripts/ics.py --title … --start …`).
- `docs/CALENDAR.md`: where the private link is in each calendar, privacy (busy-only), switching on, troubleshooting, removal.
- Setup wizard v0.5 — **one path, closest things first**: I you → II your channels (mailbox, calendar) → III your work (departments, first messages) → IV around you (radar, supply chain) → V your voice (content, Telegram) → VI autopilot. Every step starts with "do you need this?", at most one secret per step, one visible result after each part.
- AGENTS rule 3 and TRANSPARENCY: the calendar link is a password. `read_secret()` in `mail/send.py` serves the mail password and the calendar link. Tests: 7 new.

## 0.12.0 — 19.11.2026 · supply chain watch
- `scripts/supply_watch.py`: your watch list of suppliers, big producers, listed companies, routes, reference prices, currencies and rules (sheet `Watchlist`). Light run: end-of-day prices (Yahoo Finance public chart data — also futures and currencies) with change vs 1 and 5 trading days, news of the last day by your query. `--full` (weekly): news of 7 days, weekly rows, a fingerprint of each supplier page — a change is flagged. Status 🟢 / 🟡 / 🔴 / ⚪ per line into `Watch_log`; sources that do not answer go to `Gaps`.
- News with alarm words (bankruptcy, fire, strike, force majeure, port closed, price increase…) are only **candidates** — `prompts/32_supply_chain.md` tells the AI agent to read each one and confirm or lower it; freight from the public Drewry World Container Index on the weekly run. Only 🔴 reaches the person the same evening; a quiet week is one line.
- `docs/SUPPLY_CHAIN.md`: the path from start to end — what you buy → who sets the price → how it travels → reference prices → rules → watch list → test → switch on → tune after 4 weeks; limits said plainly.
- `radar_create.py`: sheets `Watchlist` + `Watch_log` in every new radar; `--add-watch` adds them to an existing one. `run.py supply` / `supply_week`; optional `schedule.supply`, `schedule.supply_week`; `config.supply_chain` thresholds.
- Setup wizard step 6a; evening news slice step 6. TRANSPARENCY: Yahoo Finance and supplier pages added. Tests: 8 new (offline), network test updated.

## 0.11.0 — 19.11.2026 · Telegram block complete
- `docs/TELEGRAM.md`: what the bot and the channel watch do, setup in 9 steps, security table (token, account, fake BotFather, groups, manager, formulas, ports), what can and cannot be read, macOS + iCloud autostart, funnel source labels.
- Setup wizard v0.4: section 7a — the assistant writes the dialog with the person, never sees the token, tests every branch, sets the channel watch and autostart.
- `scripts/install/telegram/`: 1_token · 2_check · 3_bot_start · 4_autostart_on · 5_autostart_off (Mac, double-click).
- Bot runs the channel watch itself at `telegram.watch_times` (catches up after sleep) — one process, no extra scheduler. Second copy of the bot does not start.
- macOS: background services cannot read iCloud folders → autostart through Login Items. Learned in real use.
- AGENTS: a bot token is a password — never in chat; if shown, `/revoke`.

## 0.10.1 — 19.11.2026 · channel watch
- `scripts/tg_watch.py`: public Telegram channels from your list, checked by your keywords (text file or a column of your keyword workbook); new matches → `tg_signals.xlsx` and a Telegram message to the managers.
- Bot: a manager forwards any post from a public channel → the channel is added to the watch list; `/channels` shows the list. Private channels are refused with a note.
- Bot data folder and dialog file can live next to the config (`telegram.data_dir`, relative paths).

## 0.10.0 — 19.11.2026 · Telegram: bot and public channels
- `scripts/bot/telegram_bot.py`: Telegram bot with a dialog you write in YAML (`config/bot_flow.example.yaml`) — buttons, typed answers (text / phone with a share button / e-mail / number), several languages. The last step saves the lead to `data/floktron_leads.xlsx` (sheets Leads, Events, Stages) and tells the manager in Telegram. Source tracking with `t.me/<bot>?start=<label>` (QR code, website, letter signature…), so you see which channel brought the lead. Events show where people stop.
- Privacy: private chats only; `/privacy`, `/forget` (personal fields blanked, row kept as "Deleted"); typed text never becomes a formula; flood guard; old buttons ignored.
- Manager commands `/leads`, `/funnel`; `/id` shows a chat id for setup. Runs with `--loop` (always on) or `--once` (scheduler). `--flow-check` validates the dialog without network.
- `news_slice.py`: new feed type **T** — public Telegram channels through the public page `t.me/s/<channel>` (no account, phone or API key); posts with your keywords go to Signal_feed like news.
- `config.example.yaml`: `telegram:` section. TRANSPARENCY: api.telegram.org and t.me added. Tests: 9 new.

## 0.9.0 — 19.11.2026 · light news check
- `prompts/31_news_check.md`: before a news item becomes a post — scale (local / national / international), echo in other outlets, primary source, fact-checkers; status ✅ confirmed · ℹ️ one source · ⚠️ check · ⛔ do not use. Information, not a filter: one source is normal for local news; sites that could not be opened are "not checked", never "unconfirmed".
- Corrections watched for 14 days for news used in posts (`radar.correction_words`); the manager gets an e-mail to update or remove the post.
- Posting day: status re-checked the same morning; one news item → at most one post per platform.
- `config.example.yaml`: `radar.fact_check` (Re:Check, Melu detektors, EDMO, Google Fact Check Explorer — edit freely), `radar.correction_words`.
- SECURITY: section "False or corrected news".

## 0.8.9 — 18.11.2026 · start in one tap
- README: one-tap links that open ChatGPT, Claude or Perplexity with the start request already written; GitHub Copilot hint.
- `START.md`: the full text for assistants in one box with GitHub's copy button — copy, paste into any assistant, also on the phone. Built with `llms-full.txt`, kept current by a test.

## 0.8.8 — 18.11.2026 · what needs a mailbox
- Setup wizard: rays and the content plan need a mailbox (posts of the day come by e-mail); the radar alone does not.

## 0.8.7 — 18.11.2026 · offer the easy way first
- Every assistant first offers two ways: A — an assistant on the person's computer downloads, installs and sets up everything (one folder only, person approves each step); B — step by step in chat. Chat-only assistants say they are Way B and mention Way A (AGENTS.md, setup wizard, README, llms-full.txt).

## 0.8.6 — 18.11.2026 · fallback for chat assistants
- `llms-full.txt`: everything a chat-only assistant needs in one plain-text file (raw link or copy-paste) — for assistants that cannot open GitHub pages. Built by `scripts/build_llms_full.py`, kept current by `tests/test_llms_full.py`.
- README: "assistant cannot open this page?" fallback at the top of Start here.

## 0.8.5 — 18.11.2026 · support, responsibility, transparency
- Supported project: GitHub Issues, koagu@koagu.com (subject "FLOKTRON"), private vulnerability reports; answers on working days (README, AGENTS, SECURITY, FEEDBACK).
- `LICENSING.md`: responsibility and your data — the authors never receive, see, store or use user data; risks kept low but not zero; liability limited only as far as the law allows.
- `docs/TRANSPARENCY.md`: every place FLOKTRON connects to and every program it starts; how to check it yourself.
- `tests/test_network.py`: network and process code allowed only in the listed files.

## 0.8.4 — 18.11.2026 · open for everyone
- For anyone who runs work: freelancers, the self-employed, crews, teams, companies — not only companies (README, AGENTS, llms.txt, LICENSING).
- Use only the parts you need: rays are optional (one, a few or none); the radar and the content plan work on their own. Setup wizard asks first what the person wants FLOKTRON for.
- Status: early preview, open for testing.

## 0.8.3 — 18.11.2026 · testing by invitation
- Status: early preview, testing by invitation, for companies (B2B); use at own risk, no support guarantee (README, AGENTS).
- `AGENTS.md`: the assistant first tells the person that everything runs only on their computer and mailbox, the authors see nothing, and how to remove it.
- `docs/UNINSTALL.md`: switch off automatic runs (Mac / Windows / Linux), delete the app password, remove files, tell the people. Linked from README, AGENTS, SUPPORT.

## 0.8.2 — 18.11.2026 · public working name
- Public working name: **FLOKTRON**. README, LICENSING, NOTICE updated.
- Public working name: **FLOKTRON**. README, LICENSING, NOTICE updated.

## 0.8.1 — 18.11.2026 · licence
- `LICENSE.md`: Functional Source License 1.1, ALv2 Future License (FSL-1.1-ALv2); rights holder KOAGU ELEMENT SIA.
- `LICENSING.md`: what is free, what needs a commercial licence, conversion to Apache 2.0 after two years.
- `NOTICE`: third-party components (openpyxl, PyYAML — MIT).
- `CONTRIBUTING.md`: contribution terms (licence to KOAGU ELEMENT SIA incl. relicensing).
- README and AGENTS: licence line updated.

## 0.8.0 — 18.11.2026 · any AI assistant, safety, feedback
- **Any AI assistant can set FLOKTRON up from the link:** `AGENTS.md` (open standard read by Codex, Copilot, Cursor, Gemini CLI, Jules and 20+ other agents) as the single source; `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` point to it; `llms.txt` for chat assistants that read web pages.
- Two modes: A — the assistant runs commands and installs (asks before each change); B — chat only, guides the person step by step.
- **Safety:** outside text (mail, news, web, registries, cells) is data, never instructions — rule in `AGENTS.md` and at the top of every prompt; agent works only inside the FLOKTRON folder; no passwords in chat; separate mailbox; only known recipients; nothing published, paid or signed without a person; install only from this repository and pypi.org.
- `scripts/safe_xlsx.py`: text that starts with "=" (e.g. a reply `=HYPERLINK(…)`) can no longer become an Excel formula — every script that writes a base uses it.
- `news_slice.py`: feeds larger than 5 MB are skipped.
- `SECURITY.md`: what is protected and how, what cannot be protected, how to report, GitHub settings for maintainers.
- `requirements.txt` with pinned versions; GitHub Actions workflow with read-only permissions.
- `tests/test_safety.py`: no dangerous calls, formula guard, secrets ignored by git, no passwords in files, agent entry files present.
- Setup wizard v0.3: step 0 (mode, folder, test or real), separate mailbox, order dry → test → real, step 10 feedback.
- Feedback: `docs/FEEDBACK.md` + GitHub issue templates (feedback / bug).

## 0.7.0 — 18.11.2026 · registries, content, gaps, support
- `scripts/registry_lv.py`: new Latvian companies from open data, read as a stream; words in the name by stem (Latvian letters normalised: "flīzes" finds "Flīžu"); Client / Channel → Companies, Competitor → Players (internal); no duplicates; a source error → Gaps.
- `scripts/content_create.py` + `scripts/content_check.py`: content plan; every morning the posts of the day come by e-mail ready to copy; missed posts move to today; a picture already published on a platform is never planned there again.
- `scripts/gaps_report.py`: weekly list of what FLOKTRON could not do + runs that ended with an error → `mail.support_address`.
- Scheduler: content check daily 07:12, gaps Fri 16:10, registry Mon 07:00.
- Prompts: `25_registries_and_public_sites.md`, `40_content_plan.md`; setup wizard v0.2 (8 steps).
- `docs/SUPPORT.md`: how a support person finds and fixes problems remotely (log, gaps, typical errors).
- 13 automatic checks.

## 0.6.0 — 18.11.2026 · works by itself
- Automatic runs: `scripts/install/` for Mac (double-click), Windows (right-click → Run) and Linux (cron); times from `config.yaml → schedule`. `scripts/run.py` is the single entry: lock (no two runs at once), waits if the base is open in Excel, log in `data/run.log`.
- Evening reminder for today's open tasks (`send_morning.py --evening`).
- Retry when the mail server does not answer (after 10, then 20 minutes).
- Public holidays LV / LT / EE (incl. Easter-based) + company days off: no messages on holidays, "next working day" in routes skips them.
- `scripts/weekly_summary.py`: weekly page for the manager — per ray done / not done with reasons / open / no reply, tasks open > 24 h, replies from unknown addresses.
- `tests/` + GitHub Actions: 10 automatic checks (answers, sender check, marker, calendar, full cycle, routes, radar) on Python 3.9 and 3.12.

## 0.5.1 — 18.11.2026 · safety and clean-up
- Replies are accepted only from the ray's own address, its team lead or the manager. A reply from any other address is recorded as "Unknown sender" and changes nothing (anyone can type a subject line). `mail.allow_any_sender: true` switches this off.
- Texts cleaned of the origin company's name; scripts/README without internal file names.

## 0.5.0 — 18.11.2026 · radar
- `scripts/radar_create.py`: radar workbook — Keywords (one column per language), Sources (neutral catalogue of public tenders, consultations, registries for LV/LT/EE/DACH/EU with access notes from real runs), News_feeds (portal RSS + Google News queries), Signal_feed, Consultations, Players (internal), Demand, Demand_history, **Gaps**, Run_log.
- `scripts/news_slice.py`: news by the client's keywords from RSS/Atom and Google News; date window, no duplicates; a feed that fails → Gaps ("source blocked") instead of a crash.
- Prompts: `20_monitoring_weekly.md` (web, tenders, consultations, registries, news, Trends, scoring, gaps, report), `30_news_evening.md` (evening slice, post with a reason, slot rule), `35_reasons_without_news.md` (people, plans, joint work, behind the scenes, questions, numbers, tips, calendar).
- Keyword matching by word stem: "kanalizācija" also finds "kanalizācijas", "kanalizāciju" (LV/LT/EE/DE endings); several words must all appear.
- Tested on local feeds: keyword match with word endings, old item skipped by date, unrelated item skipped, failed feed → Gaps, second run adds nothing. Google News not reachable from the test machine — to be checked on the Mac.

## 0.4.1 — 18.11.2026 · first real test (Gmail inboxes via Proton Bridge)
- Real run: 3 morning messages (LV / EN / RU) to test Gmail inboxes, replies pressed on a phone, collected, escalation and repeat task created.
- Fix: e-mail signatures ("Best regards …", "Ar cieņu", "С уважением", "Sent from my iPhone", `--`) and the button's own text ("✅ Pieņemu.") are no longer stored as the answer.
- New: subject tag (`mail.marker`) and message colours (`colors`) in config — a second FLOKTRON can run in the same mailbox without mixing.

## 0.4.0 — 18.11.2026 · routes
- `scripts/route.py`: an answer becomes the next task by the rules in the "Routes" sheet (order → stock + finance, low stock → purchasing, goods bought → logistics …). Keywords decide which rule fires.
- Not done → repeated next working day (old task = Moved); second failure → manager (L0) decides.
- Runs automatically after `collect_replies.py`; `--dry` shows what would happen.
- Base: 9 default routes, column "Route" in Tasks, status "Moved".
- `docs/GMAIL_TEST.md` + `config/config.gmail-example.yaml`: step-by-step Gmail test with an app password.
- Tested: 3 answers → 4 new tasks (shipment, invoice, reorder, repeat); second failure → manager; repeated run creates nothing.

## 0.3.0 — 18.11.2026 · reading replies
- `scripts/collect_replies.py`: reads button replies; `+` → Done, `−` → Not done; OK / Q / NO for the whole message; TEST replies recorded only.
- Finds the person's answer anywhere in the reply (top or end, lines glued by mobile apps); cuts the quoted original.
- Every reply saved as a file `data/replies/<date>/…eml`; running twice is safe (Message-ID).
- Escalation: `−`, Q, NO → team lead of the ray (or manager); `--deadline`: no reaction at all is recorded separately as "No reply" and goes to the lead/manager.
- `scripts/mail/read.py`: one reader for Proton Bridge, Gmail, Outlook, any IMAP server, or a folder of .eml files.
- Base: Rays get a "Team lead e-mail" column; task status "Not done".
- Tested end to end on a local mail server: morning messages → 4 replies (incl. Russian text, mobile-style glued lines, quoted original, TEST) → statuses, 3 escalations, second run adds nothing.

## 0.2.0 — 18.11.2026 · morning messages
- `scripts/send_morning.py`: morning message per ray; every task has its own `+ / −` buttons carrying the task line; answer is written at the end after ✍️; `--dry`, `--only`, `--test`.
- `scripts/mail/send.py`: one sender for Proton Bridge, Gmail, Outlook and any SMTP; password only from environment or macOS Keychain.
- `scripts/i18n.py`: texts EN / LV / RU, polite business tone.
- Base: new column `Letter` in Tasks (which message a task went in).
- Tested: build, test send and real send against a local mail server; statuses New → Sent.

## 0.1.1 — 18.11.2026 · first working script
- `scripts/base_create.py`: creates an empty base from `config.yaml` (or default rays). No company data in the code.
- `templates/floktron_base_empty.xlsx`: empty base, 14 sheets.

## 0.1.0 — 18.11.2026 · repository created
- Private repository, structure: hands (`scripts/`) and head (`prompts/`).
- Docs: requirements, storage layout with task IDs and hash log, site module draft, roadmap.
- Decision: no blockchain inside one company — hash log instead (see docs/ROADMAP.md).
- Decision: workers on site → Telegram/WhatsApp bot; foremen and managers → e-mail.

## 0.0.9 — 18.11.2026
- Reply buttons must carry the task line (context); polite business tone in letters.
- New reply format planned: one `+ / −` per task instead of editing a table.

## 0.0.8 — 17.11.2026
- Evening check of the day's publications on live profiles; media sheet against duplicate posts.
- Instruction-consistency check script at chat start.

## 0.0.7 — 13.11.2026
- Decision: stay on Claude; later an always-on server. One mailbox for all FLOKTRON mail.

## 0.0.6 — 10–12.11.2026
- Test structure: test inboxes as departments, 3 directions + escalation worker → lead → manager.
- Reply collection (OK / NO / Q / R), routing rules, evening reports, manager ray L0.

## 0.0.5 — 09.11.2026
- Scheduled runs on Mac work without manual start (system scheduler + disk access).

## 0.0.4 — 08.11.2026

## 0.0.3 — 05.11.2026
- Evening news slice + retry (Baltic first, DACH and EN background); brand mentions and complaint sites.
- First department summary (marketing).

## 0.0.2 — 30.10–02.11.2026
- Proton Mail Bridge → automatic saving of public-consultation mail.
- Retry run, catch-up of missed weeks, weekly backup, new companies from registries.

## 0.0.1 — 10.10.2026 · birth
- Monitoring file: 34 keywords × 4 languages, first search in LV/LT/DE/CH/EN, Google Trends baseline.
