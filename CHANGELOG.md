# Changelog

History of FLOKTRON. Newest first.
Every change in this repository is also a git commit with date and description — the full archive.
Project started 2026-10-10 (first ray in production in an operating company); public since 2026-11-18.

## 0.37.1 — 27.11.2026 · «View site» button
- Dashboard, site cameras: the button of your own camera now reads «View site» (RU «Смотреть объект», LV «Skatīt
  objektu»); link-only examples (public webcams) keep «Open camera».

## 0.37.0 — 27.11.2026 · site cameras
- New `scripts/cameras.py` and docs/CAMERAS.md: list your cameras in `config.yaml → cameras`; `cameras.py snap`
  (also `run.py cameras`) takes ONE frame per camera — an HTTP snapshot address (most IP cameras, recorders, the ONVIF
  snapshot URI) or `rtsp://` through `ffmpeg` — and overwrites it in `data/cameras/`. No recording, no streaming, no
  face recognition; passwords in addresses are never printed.
- Dashboard: a new block «Site cameras» — online / no fresh frame, the latest frame, a button to open the camera live
  in its own app or page; a camera without a fresh frame also goes to «Needs your attention». A drawn placeholder is
  shown until the first frame.
- `demo: true` cameras are link-only examples (e.g. public city webcams): never fetched or embedded, marked «example»
  with the source, never presented as a customer site.
- For security and the state of a site only; the rules (GDPR, EDPB 3/2019, no watching how people work) are in
  docs/CAMERAS.md. TRANSPARENCY lists the new local network call and `ffmpeg`.
- New tests: `tests/test_cameras.py` (7, fictional company), demo `tests/fixtures/cameras/make_demo.py`.

## 0.36.1 — 27.11.2026 · work time: invite link
- `worktime.invites` in config.yaml: a personal link `t.me/<your bot>?start=<code>` per person. The person opens it,
  taps Start and is in the work-time record under the name you set — no chat ids to copy. The managers get one notice.
  Who joined is kept in `data/worktime_people.json` (next to the log) and stays after a bot restart.
- `/in` starts work without a location point (for a person who does not want to share it).
- The live box of the operating company runs on 0.36 now; tests: +1 (`test_invite_link_joins_the_team_once`).

## 0.36.0 — 27.11.2026 · work time
- New `scripts/worktime.py` and docs/WORKTIME.md: the team marks ▶ Start / ⏸ Pause / ⏹ End with buttons in the work
  chat with the bot. Optional: one location point at «Start» (`worktime.geo`), compared with your sites — inside ✓ or the
  distance. Nothing is tracked during the day; no photos, no biometrics.
- The bot asks «Still at work?» at `worktime.remind_at`; a shift without an end mark is flagged and NOT counted — hours
  are never made up. Night shifts count as one shift with separate night hours.
- Manager corrections only with a reason (`worktime.py fix`), kept as new lines: the log `data/worktime.jsonl` only grows.
- Dashboard: a new block «Work time» — at work now, hours today and this month, overtime, night, weekend/holiday hours,
  what to check; the warnings also go to «Needs your attention». Bot: `/hours` for everyone, `/who` for managers.
- `worktime.py month` → `data/worktime_<YYYY-MM>.xlsx` for the accountant (sheets Month and Days).
- Not tied to Telegram: `worktime.py mark --who … --action start --by kiosk` marks from any other channel (dashboard,
  kiosk, e-mail or SMS gateway); the dashboard shows the channel.
- New tests: `tests/test_worktime.py` (16, fictional company), demo data `tests/fixtures/worktime/make_demo.py`.

## 0.35.1 — 27.11.2026 · where to follow FLOKTRON
- README and the footer of floktron.com (9 languages) now link to the FLOKTRON pages: YouTube (step-by-step guides),
  LinkedIn, Facebook and X. Nothing changes in the program; support stays in Issues and support@floktron.com.

## 0.35.0 — 26.11.2026 · the FLOKTRON mark and a desktop icon
- FLOKTRON has a mark: a violet tile (#8B5CF6) with a white F whose middle bar is a dot. Files in `assets/brand/`:
  mark and logo (SVG, light and dark), app icons for Mac (`.icns`), Windows (`.ico`) and Linux (PNG).
- New `scripts/desktop_icon.py`: puts a FLOKTRON icon on the desktop (Mac app, Windows shortcut, Linux entry); one
  double-click rebuilds the dashboard and opens it in the browser. `--remove` takes it away. Setup wizard step 11 offers it.
- The dashboard shows the mark in its header and in the browser tab (inline, still loads nothing from the internet).
- docs/TRANSPARENCY.md and `tests/test_network.py`: the icon script opens only the local `data/dashboard.html` and
  starts PowerShell once on Windows to save the shortcut. New tests: `tests/test_desktop_icon.py` (6).

## 0.34.0 — 26.11.2026 · automated security checks
- Free, widely used scanners now run on every change and once a week: OpenSSF Scorecard (public result and badge in
  README), GitHub CodeQL (`security-extended`, Python and workflow files), Bandit, pip-audit (required and optional
  packages) and Dependabot (packages and GitHub Actions). These are automated scans, not an independent audit.
- Fixed what the first run found: feeds that declare XML entities are skipped before parsing; readers that take a link
  from settings accept only `http(s)://` (no `file://`); supply-watch pages over 5 MB are cut; SHA-1 ids marked
  `usedforsecurity=False`; every GitHub Action pinned to a full commit hash. Bandit: 0 high, 0 medium left; pip-audit:
  no known vulnerabilities. Details and the low findings that stay on purpose: docs/SECURITY_SCANS.md.
- New test file `tests/test_scan_fixes.py` (9 tests) keeps these fixes in place. CONTRIBUTING.md: a test with every
  new feature or fix, fictional data only, security checks green.

## 0.33.4 — 26.11.2026 · licence in plain words
- README: the one-line licence note becomes a short "Licence in plain words" block — what is free, what needs a
  separate agreement, that the name is not licensed, and that each version also becomes Apache 2.0 two years after its
  release. floktron.com/xx/about/#licenziya says the same in 9 languages.
- Docs only; the licence itself (LICENSE.md) is unchanged.

## 0.33.3 — 26.11.2026 · honest failures and a prompt-injection section
- Correction: 0.33.2 said "1,333 automatic runs without a failure". That was wrong — the number counted runs that
  finished, not letters that were delivered. The full log says: about 1,460 runs since 8 November, 30 with an error
  (about 2 %), 29 of them because Proton Mail Bridge was closed or the computer was asleep; most recovered on the next
  run or retry, three times letters did not go out even after retries. README and floktron.com now say so.
- SECURITY.md: new section "Prompt injection — hidden instructions in mail, attachments, web pages and Telegram" —
  what FLOKTRON does with each kind of outside text and which file makes it so; docs/TRANSPARENCY.md links to it.
- New test `test_every_prompt_and_role_says_outside_text_is_data`: fails if any prompt or ready role loses the
  "outside text is data, not instructions" rule.

## 0.33.2 — 26.11.2026 · a month of mail in numbers
- README "Runs in a real company": numbers from the company where FLOKTRON runs (November 2026) — about 30–45 letters
  a day through paid Proton Mail via Bridge (read-only), about 5 % of incoming letters needed a person, 143 staff
  replies with one button, 1,333 automatic runs without a failure. Full case on floktron.com/xx/about/#keis-pochta.
- Text only, no code change.

## 0.33.1 — 26.11.2026 · clear status and honest notes
- Status line: "in daily use in an operating company since October 2026 · public since November 2026" instead of
  "early preview — open for testing" (FLOKTRON has run a real company every day since October; outside reviewers read
  the old line as "not tested yet").
- README: project history table (2026-10-10 → 2026-11-22).
- README "Head" row: used every day with Claude; other assistants follow the same instructions but are not tested to the
  same depth yet — start with the safe first test.
- README principles and docs/TRANSPARENCY.md: the text your AI assistant reads is processed by that assistant's
  provider under its own terms.
- Text only, no code change.

## 0.33.0 — 26.11.2026 · industry packs for all six fields
- Three more ready radar starts, same format as the others, 24 keywords each in LV, RU, EN, public sources, registry
  queries and two supply-chain examples (off until switched on):
  `templates/industry/production.json` (manufacturers and workshops — supply tenders, CE marking, Machinery Regulation,
  industrial emissions, CBAM, energy and raw material prices, labour shortage, automation, EU funds),
  `templates/industry/rental.json` (machinery, scaffolding, generators — hire tenders, lifting-equipment inspection,
  machinery registration, diesel and leasing rates, used machinery prices, telematics, equipment theft) and
  `templates/industry/services.json` (cleaning, facility management, security, maintenance — service tenders,
  workplace and fire safety, CCTV data protection, minimum wage and labour taxes, building energy efficiency).
- Every field FLOKTRON is built for now has its own pack: construction, logistics, wholesale, production, equipment
  rental, business services. All six apply to one radar without clashes.
- `docs/FLOKTRON_overview.pdf` = overview 1.24 (21 pages): new page 18 "FLOKTRON in your company" — the six
  industries side by side; the mail row now says Gmail only (Outlook is not supported yet, see 0.32.1). 9 languages on
  floktron.com, where the home page has a switch with the same six industries.

## 0.32.1 — 26.11.2026 · honest about mail: which mailbox works and what it costs
- Outlook / Microsoft 365 is marked **not supported yet**: Microsoft no longer lets outside programs sign in with a
  password (Outlook.com since 16.09.2024), and FLOKTRON does not have the Microsoft sign-in yet. The setup wizard says
  so and offers a separate Gmail mailbox. Earlier docs listed Outlook as working — that was wrong.
- A free Proton account does not work: Proton Mail Bridge comes only with paid Proton plans. The wizard now asks
  whether the Proton plan is paid before anything else; `docs/REQUIREMENTS.md` says it plainly and lists Proton Mail
  Plus and Proton Unlimited with their public prices.
- When a mailbox refuses the connection, `scripts/mail/read.py` and `send.py` add one plain sentence: why, and what to
  take instead (`hint()` in `mail/send.py`, tests in `tests/test_mail_hints.py`).
- Website: floktron.com/xx/about/ gets "Our recommended set" (Proton Mail, Drive, Pass, Cloudflare — any other
  combination works too) and the cheapest working setup per month.

## 0.32.0 — 26.11.2026 · what it needs and what it costs a month
- `docs/REQUIREMENTS.md` rewritten: the computer per variant (text only · computer voice · voice reports turned into
  text on this computer · live cloud voice) and every monthly payment to outside services with the public price and
  its source — AI assistant, mail, Telegram, ElevenLabs, a server. The basic setup costs one AI subscription; a live
  cloud voice adds $6–22 a month.
- `scripts/capacity_check.py` now says which variants this computer can carry (✅ / ⚠️), also in `--json`.
- The morning audio reads better: `speech_text()` in `scripts/voice.py` turns symbols into words before any voice —
  € → euro, 12,50 € → 12 euro 50 cents, % → percent, dates and times in words, /commands, links, addresses and
  file names dropped, names said the way people say them.
- If the cloud voice fails (no key, no credits, offline), the summary is read with the computer's own voice and still
  arrives on time.
- `docs/REQUIREMENTS.md` also gives our security recommendations (separate mailbox, two-factor sign-in, keys in the
  keychain, disk encryption, weekly backup).
- Website: new page floktron.com/en/about/ in 9 languages — why FLOKTRON was made, what it costs a month, security.
- `docs/FLOKTRON_overview.pdf` = overview 1.23 (20 pages): new page 19 "What your computer needs and what a month costs".

## 0.31.1 — 26.11.2026 · overview PDF 1.22
- `docs/FLOKTRON_overview.pdf` = overview 1.22: page 17 now names all three industry packs; versions and tests updated.

## 0.31.0 — 26.11.2026 · industry packs: logistics and wholesale
- Two more ready radar starts, same format as construction: `templates/industry/logistics.json` (haulage, forwarding,
  warehousing — tenders, Mobility Package, tolls, border queues, fuel and freight rates, driver shortage, Rail Baltica)
  and `templates/industry/wholesale.json` (distributors — supply tenders, VAT, deposit scheme, packaging rules,
  recalls, supply-chain disruption, producer prices, late payments). 24 keywords each in LV, RU, EN, public sources,
  registry queries, two supply-chain examples (off until switched on).
- Two packs can go into one radar (a company that builds and transports): every pack has its own IDs.

## 0.30.1 — 26.11.2026 · overview PDF 1.21
- `docs/FLOKTRON_overview.pdf` = overview 1.21 (19 pages): new page 17 "The radar ready on day one — a keyword set
  for your industry"; every address now floktron.com, github.com/floktron/floktron, support@floktron.com.
  9 languages on floktron.com.

## 0.30.0 — 26.11.2026 · industry packs: the radar ready on day one
- A new company no longer invents 30 search words from scratch. `templates/industry/construction.json` — the first
  industry pack: 24 keywords in Latvian, Russian and English (demand, rules, environment, funding, costs, people, risk,
  market, events), typical public sources (EU construction tenders CPV 45, building permits, construction statistics,
  labour inspection, construction policy), registry queries for new construction companies and developers, two
  supply-chain examples (off until switched on).
- `scripts/industry_pack.py`: `list`, `show`, `apply <pack> --country --city --competitor …` (adds to the radar,
  never overwrites, never adds the same word twice; competitors go to Keywords and Players), `words`, `add`, `off`.
- The setup wizard (step 7) asks only three things: industry, country and city, 3–5 competitors.
- Telegram, managers only: `/words` — the words searched now, `/addword <words>`, `/delword <words>` (pauses, the row stays).
- `news_slice.py`: more than 8 keywords per language now go to Google News as several queries (up to 32), before only
  the first 8 were searched. Keyword priority `off` = paused.
- `docs/INDUSTRY_PACKS.md`. Next packs: logistics, wholesale.

## 0.29.5 — 25.11.2026 · safe first test on a clean install
- `tests/first_run_smoke.py`: on a computer with only `requirements.txt` installed, the two move-archive steps
  showed FAIL, because the password archive needs the optional package `pyzipper`. They are now marked
  "skipped, pyzipper not installed (the move buttons install it)", like the PDF steps without `reportlab`.
  Clean install: 16 of 16 passed; with `pyzipper`: 18 of 18.

## 0.29.4 — 25.11.2026 · new home: floktron.com
FLOKTRON has its own address now.
- Website: **https://floktron.com** (9 languages, the same pages as before). The old pages on koagu.com/…/floktron/
  forward there automatically.
- Repository: **github.com/floktron/floktron** (moved from github.com/koagu-element/floktron; old links and
  existing installations keep working — GitHub forwards them).
- Support e-mail: **support@floktron.com** (the old address still reaches us).
- The update check (`scripts/update_check.py`) now asks the new repository address. Nothing else changed: same code,
  same licence, same rights holder — KOAGU ELEMENT SIA.

## 0.29.3 — 25.11.2026 · overview PDF 1.20
- `docs/FLOKTRON_overview.pdf` version 1.20 (18 pages): on the page *Before you install — a safe first test* a new
  block *Tested on Windows and Linux*; open version and test count updated. The same PDF in 9 languages on
  koagu.com/floktron.

## 0.29.2 — 25.11.2026 · tested on Windows and Linux
FLOKTRON now runs the safe first test itself, on clean Windows and Linux, on every change — and the first Windows run
found real bugs, now fixed.
- Fixed on Windows: scripts stopped with an encoding error when their output went to a pipe, the Task Scheduler log or
  an AI assistant (arrows, ✅ and Latvian letters). Every script now writes UTF-8 (`scripts/utf8_console.py`).
- Fixed on Windows: time zones (Europe/Riga and others) were unknown — `tzdata` is now installed on Windows
  (`requirements.txt`, the Windows buttons).
- Fixed on Windows: branded PDF documents found no font — Arial / Segoe UI from Windows are used.
- Fixed on Windows: supplier invoices and mail watch did not match documents in sub-folders with the extraction file.
- Fixed on Windows: after a git download every shipped prompt looked like the company's own change in the move archive.
- Fixed on Windows: the security check-up stopped when FLOKTRON lives on another drive than the temp folder (C: / D:).
- Without reportlab `documents.py` says in one sentence what to install, instead of an error trace.
- New `tests/first_run_smoke.py`: the safe first test as one script — config, base, radar, library, documents,
  invoices, snapshot, dashboard, check-ups, scheduler entries (printed only), move pack → check → unpack, update
  check. Fictional data only; changes nothing outside a temporary folder. CI runs it with the tests on Windows
  (Windows Server 2025, Python 3.12) and Linux (Ubuntu, Python 3.10 and 3.12).

## 0.29.1 — 25.11.2026 · overview PDF 1.19
- `docs/FLOKTRON_overview.pdf` version 1.19 (18 pages): new pages *Order — yes / no in Telegram* (0.28.0) and
  *New versions — you know the same day what was fixed* (0.29.0). The same PDF in 9 languages on koagu.com/floktron.

## 0.29.0 — 25.11.2026 · new versions: know the same day what was fixed
A tester fights a bug for an evening — and the fix was already out that morning. Now FLOKTRON tells the manager itself.
Nobody collects contact details for this.
- `scripts/update_check.py`: once a day, with the morning run, one anonymous request to api.github.com for the list of
  FLOKTRON releases. A newer version than the one in `CHANGELOG.md` → ONE message per version to `mail.manager_address`
  and, if the bot is on, to `telegram.manager_chat_ids`: you have X, newer is Y, what was fixed and added (from the
  release notes, short), how to update. Only release news — no advertising, no support or partner links (a test checks).
  Offline or GitHub not answering → nothing happens, the morning run is not affected.
- `prompts/58_update.md` — *"update FLOKTRON"*: backup first (`scripts/move.py backup`), then `git pull --ff-only` or the
  release ZIP over the folder without `config.yaml`, `data/` and the company's own prompts, then the tests; red → back
  to the backup.
- Telegram bot: `/version` for managers; the new-version notice is passed on once (`data/update_notice.json`).
- Setup wizard step 11b *New versions*; `config.example.yaml` section `updates` (`check`, `mail`, `telegram`,
  `language`); `scripts/run.py update`. Messages in 9 languages (EN LV RU DE LT ET ES IT FR).
- `docs/UPDATES.md`; `docs/TRANSPARENCY.md` lists api.github.com — `tests/test_network.py` checks it. Without FLOKTRON:
  GitHub *Watch → Custom → Releases* or the feed `releases.atom`.
- `tests/test_updates.py` on TEST · FICTIONAL releases (Demo SIA), offline.

## 0.28.0 — 25.11.2026 · tidy: yes / no in Telegram, mail and tasks without old things
From a real company's first days: the manager got old resolved tasks every morning, mail-confirmation letters as
"unanswered", test messages, and Telegram notices that asked to write into sheets — and the bot greeted the manager
as a new client. Now:
- **Telegram yes / no** ([Telegram](docs/TELEGRAM.md#tasks-yes--no)): the manager and the team (`team_chat_ids`, voice
  users) never get the client dialog — free text and `/start` give a short help, `/client` tries the dialog. One task =
  one message with two buttons ✅ / ⛔: mail waiting for you, the top 3 new prospects, card payments without a document.
  A press turns the message into «✅ Closed · time» and goes to `data/task_actions.jsonl`; mail_watch, prospects and
  gateways move it into their sheets. A text reply to a task message closes it with the comment. New
  `scripts/task_notice.py`. No text about sheets or columns in Telegram.
- **Mail** ([Mail watch](docs/MAIL_WATCH.md)): new category *Service confirmation* ("verify your e-mail") — never a task,
  old open ones are closed; "we received your submission" is a notice. Reminders: the first nudge, then day 3, 7 and 14,
  then never (`remind_days`); any later message from you to that address or company domain = answered (the
  correspondence goes on); no answer after day 14 → `Closed · 14 days` (`close_after_days`).
- **The manager's tasks** (new [Tasks tidy](docs/TASKS_TIDY.md), `scripts/tasks_tidy.py`, after every collect and
  `run.py tidy`): the event happened (a message went to that company, a meeting day passed) → Done with the reason;
  tests and escalations of test rays → Cancelled; a task comes on its first day and day 3, 7, 14, then Archive
  (column Shown, `send_morning.py`).
- **Friendly letter about posts** (`content.engage`): only posts Scheduled or Published today, time · platform · topic ·
  first words → link, plus "yesterday also out"; "if you have a minute — like or comment if you want"; no deadline, no
  escalation; no post → no letter.
- Tests on a fictional Demo SIA: `tests/test_task_buttons.py`, `tests/test_tasks_tidy.py`, more in `test_mail_watch.py`.

## 0.27.1 — 25.11.2026 · overview PDF 1.17
- `docs/FLOKTRON_overview.pdf` version 1.17 (16 pages): new page *Move in one click — to another computer or another
  AI assistant*; open version 0.27.0. The same PDF in 8 languages on koagu.com/floktron.

## 0.27.0 — 25.11.2026 · move: the whole setup in one archive
A company changes its computer, moves from one AI assistant to another (Gemini to Claude, ChatGPT to Copilot…) or hands
the work to a new manager. Now one button packs everything the company set up into one password-protected file, and
any AI assistant sets it up again on the other computer. The same archive, made every week by itself, is the backup.
- New [MOVE](docs/MOVE.md) and `scripts/move.py` (`pack`, `check`, `unpack`, `backup`, `secrets`): config.yaml without
  passwords, everything in `data/` (bases, company library, documents, reports, `data/context/` — the company's notes
  for its assistant), only the company's own changes in `prompts/` and `agents/` (against the new
  `templates/shipped_prompts.json`), the schedule as a plain table, `SECRETS_TO_ENTER.md` (names of the passwords to
  type again, never values), `COMPANY_CONTEXT.md` (the company in one page for any assistant), `MANIFEST.json`
  (SHA-256 of every file) and `MOVE.md` + `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` for any agent that opens the folder.
- Password: AES-256 zip (optional package `pyzipper`, the buttons install it), at least 10 characters, never stored.
  Passwords, tokens, keys and private calendar links never go in: fields and files that look like one are emptied or
  left out and listed; every text file is checked once more before the archive is written.
- Unpack checks every file against the manifest, refuses unsafe paths, moves what is already there aside (nothing is
  deleted) and writes `data/move/AFTER_MOVE.md`: passwords again, old paths, schedule on here and off on the old
  computer, capacity check, security checkup, test message. Mac → Windows → Linux works the same.
- Profile `handover` for a new manager: people's e-mails and phones out of the config, personal sheets out of the
  bases, contact columns emptied, letters, replies and voice left out.
- Weekly backup: `move.backup: true` → every Sunday 19:30 (`run.py backup`), password from the keychain or an
  environment variable, into the company cloud folder, the last 4 kept; the dashboard shows when it fails or is late.
- Buttons: `scripts/install/move_mac.command`, `move_windows.bat`, `move_linux.sh`; `/backup` to the Telegram bot
  (managers only; the archive is never sent through Telegram).
- Setup wizard: new step 11a; `prompts/57_move.md`; the AI operations director role includes it.
- Chats and memory inside an AI vendor's app stay with the vendor; MOVE says how to bring what matters into
  `data/context/`.
- Tests: `test_move.py` (fictional TEST · FICTIONAL Demo SIA only).

## 0.26.3 — 25.11.2026 · crypto support
- README "Support the project": crypto (BTC, ETH/USDC/USDT on Ethereum ERC-20, USDT on Tron TRC-20, SOL);
  addresses and QR codes are kept in one place — the support page (koagu.com/en/floktron/support/). PayPal still coming soon.

## 0.26.2 — 25.11.2026 · support the project
- README: new section "Support the project" — voluntary support via koagu.com/en/floktron/support/ (card or Apple Pay
  through Stripe, any amount; PayPal and crypto coming soon). Not charity; nothing is sold in return.
- `.github/FUNDING.yml`: the GitHub "Sponsor" button links to the support page and the Stripe link.

## 0.26.1 — 24.11.2026 · runs in a real company
- README, AGENTS.md, llms.txt: FLOKTRON runs the daily work of an operating manufacturing company; new features work there
  first, on real everyday actions. Public examples, tests and screenshots use fictional companies only; real company data
  never leaves the company.

## 0.26.0 — 24.11.2026 · breath: the computer does the routine, the AI does the thinking
FLOKTRON had a face (dashboard), a mouth (messages, morning audio), eyes (radar, watches), ears (replies, voice, bot)
and hands (scripts). Now it breathes: the routine runs on the company's own computer, and the AI assistant reads one
short summary and spends its work on judgement. Less AI work per day, the same result, the data stays with you.
- New [BREATH](docs/BREATH.md): what runs on the computer and what the assistant still does, task by task.
- New `scripts/capacity_check.py`: read-only check of the computer (system, cores, memory, free disk, Python) with
  ✅ / ⚠️ / ❌ and the breath table; report in `data/`. Nothing is changed, nothing is sent.
- New company library — [LIBRARY](docs/LIBRARY.md), `scripts/library.py` (`init`, `check`, `list`, `new`): the company
  profile and the templates for invoice, advance invoice, acceptance act and offer (`templates/documents/`) are made
  once in `data/library/`, never overwritten, usable offline and by any AI assistant; `documents.py --seller
  data/library/company.json` draws from it.
- New [ready AI roles](agents/README.md): **secretary** and **operations director** — `ROLE.md` (what the role does
  and never does), `agent.md` (instructions for the assistant), `role.yaml` (scripts, prompts, config sections, setup
  steps, dashboard cards). Procurement and project coordinator are next.
- Setup wizard v0.7: step 0 runs the capacity check, explains breath and offers a role; step 8d makes the library;
  step 12 closes with what now runs by itself.
- Tests: `test_library.py`, `test_capacity.py`, `test_roles.py` (fictional Demo SIA only).
- `docs/FLOKTRON_overview.pdf` version 1.16: new page *Breath and ready roles*; open version 0.26.0.

## 0.25.0 — 24.11.2026 · built for companies (B2B)
FLOKTRON is now described for what it does best: a company with teams, production and processes, run by an owner or
a manager who wants to see everything in one place. One-person setups (a freelancer, a consultant) are no longer the
target, and the texts no longer use them as examples. Nothing in the code changes.
- README, AGENTS.md, llms.txt: who it is for — the owner or manager of a B2B company; fields: construction, logistics
  and haulage, production, equipment rental, wholesale, services.
- LICENSING: examples are companies (haulage, construction, an IT partner that installs it for a client).
- Setup wizard, step 4: a company may start with one or two rays; the construction example is *Sites · Materials · Crews*.
- FEEDBACK template: company examples only.
- `docs/FLOKTRON_overview.pdf` version 1.15: the cover line and *What it is* say who it is for; open version 0.25.0.

## 0.24.3 — 24.11.2026 · tests on Linux only again
- The macOS test job added in 0.24.2 never got a GitHub runner and was cancelled; it is removed. Automated tests run
  on Linux (Python 3.10 and 3.12), as before 0.24.2.
- `docs/FLOKTRON_overview.pdf` version 1.14: the line about tests on macOS is corrected; open version 0.24.3.

## 0.24.2 — 23.11.2026 · before you install: a safe first test
Learned from outside AI assistants that reviewed FLOKTRON: the safety advice was there, but deep in SECURITY.md and
AGENTS.md; a first look at the README did not show it. One gap was real: the speech model download was not listed.
- README: new section **Before you install — a safe first test** — mail is only read, a separate mailbox, a separate
  user account or virtual machine for the first run, every connection listed, Latvia first for new-customer search.
- [TRANSPARENCY](docs/TRANSPARENCY.md) and [VOICE](docs/VOICE.md): the one-time download of the speech model from
  huggingface.co (only if voice is switched on with the local engine) is now listed; after it speech → text works
  offline; `stt_model` may be a folder path for no download at all. New automated test keeps it listed.
- SECURITY: first run in a separate user account or virtual machine.
- Automated tests now also run on macOS.
- `docs/FLOKTRON_overview.pdf` version 1.13 (14 pages): new page *Before you install — a safe first test*.

## 0.24.1 — 23.11.2026 · overview PDF 1.12
- `docs/FLOKTRON_overview.pdf` (version 1.12, 13 pages): new page *New in version 0.24 — payment gateways: every
  card payment finds its document* (where the document gets lost and what FLOKTRON does, what you get, what stays
  safe); open version 0.24.0, 130 automated tests in the figures. Other languages on koagu.com/floktron were updated
  the same day.

## 0.24.0 — 23.11.2026 · payment gateways: every card payment finds its document
Learned in real use: card payments for subscriptions, software and domains often had no document — receipts without
a PDF, in the spam folder, in USD, or for a private person. The invoice check looked only from the document to the payment.
- **[GATEWAYS](docs/GATEWAYS.md)** — `scripts/gateways.py` (no AI): reads the inbox **and the spam folder** of the
  `mail` section (only read) and finds receipts of Stripe, Paddle, Lemon Squeezy, Apple, Google Play, PayPal and
  FastSpring — PDF, a link to the portal, or the receipt in the message text. Look-alikes (wrong domain, DMARC / SPF
  fail) are marked ⚠ and get no link; no link is ever opened.
- PDF → `data/invoices/inbox/<seller>/` and the usual invoice check; no PDF → a PDF copy of the message (not an
  invoice), a task with the exact place in the portal to add company name and VAT number, and a draft request in
  English to the seller's support (`data/gateways/requests/`, never sent; none for Apple / Google).
- The other direction: **every card payment** of the bank statement (CSV, or a Swedbank-style PDF with `pypdf`) of
  the last `card_days` days — **USD and other currencies included**, with rate and conversion fee — looks for its
  document (amount + currency + date −3 … +7 days + seller or gateway in the statement text; amount and date alone
  are never enough). Nothing found → *find the receipt*; after `act_days` → a DRAFT internal act (LV + EN) for the
  head to sign (`data/gateways/acts/`, check with your accountant).
- New sheet **Gateways**, tasks for the finance ray, one short notice (Telegram or e-mail, quiet hours); runs after
  every reply collection once `gateways.enabled: true`, by hand `python3 scripts/run.py gateways`.
- `prompts/56_gateways.md`, setup wizard step **8h Payment gateways**, config section `gateways`; no new network
  use; 6 new automated tests on fictional sellers (TEST · FICTIONAL, files built at test time).

## 0.23.1 — 23.11.2026 · overview PDF 1.11
- `docs/FLOKTRON_overview.pdf` (version 1.11, 12 pages): new page *New in version 0.23 — new customers: like your
  best ones, with a reason to write now* (where the facts come from, sheet Prospects, what stays safe); the row
  "New customer search" in *What else can be connected* now says running since 0.23; open version 0.23.0,
  124 automated tests in the figures. Other languages on koagu.com/floktron were updated the same day.

## 0.23.0 — 23.11.2026 · new customers: like your best ones, with a reason to write now
Learned in real use: the best first letters went to small firms that had just started a job of the right kind.
- **[PROSPECTS](docs/PROSPECTS.md)** — `scripts/prospects.py` (no AI): reads Latvia's public procurement results
  (EIS, data.gov.lv, updated daily) and finds companies that have just signed a contract of the kind you serve
  (words in the subject, `prospects.signals`; design, supervision and supplies are left out).
- The register (data.gov.lv) adds form, town and registration date; terminated companies drop out. Your best
  customers (`prospects.best_customers`) give the portrait — a prospect that looks like them scores higher.
- New sheet **Prospects** in the radar base: score and priority (ESTIMATE), *Why now*, contract, source link,
  data status. *Decision* `Add` → sheet **Companies** + a draft first letter in `data/prospects/drafts/`;
  `No` → never again. Companies already known or marked *Do not contact* are skipped. Nothing is ever sent.
- A short notice (Telegram or e-mail) only when there are new prospects; dashboard card **New customers: why now**
  (en / ru / lv); job `python3 scripts/run.py prospects` (once a day).
- `prompts/55_prospects.md`, setup wizard step **8g New customers**, config section `prospects`; network only through
  `scripts/registry_lv.py` (new helper `resources()`, `docs/TRANSPARENCY.md`); 8 new automated tests on fictional
  companies (TEST · FICTIONAL, files built at test time) — 124 in all.

## 0.22.1 — 23.11.2026 · overview PDF 1.10
- `docs/FLOKTRON_overview.pdf` (version 1.10, 11 pages): new page *New in version 0.22 — mail watch: nothing waits
  unnoticed* (what is in the mail and what FLOKTRON does, sheets Mail and Contacts, what stays safe); open version
  0.22.0, 116 automated tests in the figures. Other languages on koagu.com/floktron were updated the same day.

## 0.22.0 — 23.11.2026 · mail watch: nothing waits unnoticed
Learned in real use: a request to confirm, an invitation from an association, a deadline in the third paragraph,
a starred message — and the phone number you need is in a signature somewhere. Tested for days on a live mailbox first.
- **[MAIL_WATCH](docs/MAIL_WATCH.md)** — `scripts/mail_watch.py` (no AI): reads the mailbox of the `mail` section
  (Proton Mail Bridge, Gmail, Outlook, any IMAP) **read-only** — received and sent — and keeps one row per message in
  the new sheet **Mail**: category (Confirm, Reply awaited, Invitation, Deadline, Question, Invoice, Letter,
  Newsletter, Notice, Notice (important), Auto-reply, Code / login, FLOKTRON (system), Sent), what is needed from you,
  dates found in the text, ⭐, answered or not. Words in EN, LV, RU, DE, ET, LT.
- New sheet **Contacts**: name, organisation, phones and website from signatures, first / last message, counts.
- A short nudge by Telegram bot or e-mail, in your language, only when someone waits for **you**: at once for
  confirm / reply / invitation / deadline / important notices, after 24 h for a question, after 48 h for a starred
  message. At most twice, not in quiet hours (22–07); your answer or `Closed` in *Status* stops it. Mail from before
  the first run is not pushed.
- Invoice PDFs from attachments → `data/invoices/inbox/<sender>/` (same file once); as soon as the AI assistant has
  read them into `extraction.json`, the next run starts `scripts/invoices.py --apply` itself.
- Dashboard card **Mail waits for you** (en / ru / lv); runs after every reply collection (`scripts/run.py collect`)
  once `mail_watch.enabled: true`; by hand `python3 scripts/run.py mail`.
- `prompts/54_mail_watch.md`, setup wizard step **8f Mail watch**, config section `mail_watch`; 8 new automated tests
  on a fictional mailbox (14 messages in 6 languages, built at test time).

## 0.21.1 — 23.11.2026 · overview PDF 1.9
- `docs/FLOKTRON_overview.pdf` (version 1.9, 10 pages): new page *New in version 0.21 — follow-ups after an offer, only
  after your "yes"* (days 3 / 7 / 14, three buttons, what stays safe); "Follow-ups after an offer" marked as running in
  *What else can be plugged in*; open version 0.21.0, 107 automated tests in the figures.
  Other languages on koagu.com/floktron were updated the same day.

## 0.21.0 — 23.11.2026 · reminders after an offer, only after your OK
Learned in real use: an offer goes out, the buyer is busy, and nobody remembers to ask a week later.
- **[FOLLOWUPS](docs/FOLLOWUPS.md)** — `scripts/followups.py` (no AI): finds a sent offer in the mailbox by its number
  (subject or PDF name), watches for any answer from the buyer or a colleague at the same company domain
  (auto-replies and mailing lists do not count), and on day 3, 7 and 14 — Monday to Friday, working hours — drafts a
  short, polite reminder in the language of the offer (LV / EN).
- The manager gets the draft with three buttons: **✅ Send**, **✏️ My text**, **⏸ No more reminders**. Nothing goes to a
  buyer without OK; button replies count only from the approver or your own addresses. The reminder goes as a reply
  in the same thread, only to the address the offer went to.
- An answer, a closed status in **Issued** (Accepted, Declined, Closed, Paid, Cancelled) or ⏸ stops the reminders;
  an unanswered draft becomes *Outdated* when the next one is due. New sheet **Follow-ups**.
- `scripts/documents.py`: the sheet **Issued** also keeps the language and the buyer e-mail; for an offer the column
  *Due* is the valid-until date.
- `prompts/53_followups.md`, setup wizard step **8e Follow-ups**, config section `followups`; 9 new automated tests
  (107 in total) on fictional data.

## 0.20.1 — 22.11.2026 · overview PDF 1.8
- `docs/FLOKTRON_overview.pdf` (version 1.8, 9 pages): new page *New in version 0.20 — your own invoices, acts and
  offers* (four documents, three steps, what stays safe); open version 0.20.0, 98 automated tests in the figures.
  Other languages on koagu.com/floktron were updated the same day.

## 0.20.0 — 22.11.2026 · your own invoices, acts and offers in your brand
Learned in real use: a small company writes its invoices in an online form — a different look each time, numbers kept
by hand, nothing in the books until someone types it in.
- **[DOCUMENTS](docs/DOCUMENTS.md)** — `scripts/documents.py` (no AI, no network) draws four documents on one branded
  A4 sheet: invoice, advance invoice, delivery and acceptance act (two signature fields), commercial offer. All fields of
  an EU VAT invoice, amount in words, bank details, "valid without signature"; long documents flow over pages.
- Languages `lv`, `en` or `lv+en`; colours from the `colors` section of `config.yaml`, logo and bank details from the
  new optional section `documents`.
- Numbers `<prefix>-R|AR|A|P-<year>-NNN` from the new sheet **Issued**; dry run first, `--apply` records; a number is
  never reused.
- `prompts/52_documents.md`: the assistant fills the document file from your words — buyer from your records or the
  public register, prices only from you or your price list; never sends anything to a customer.
- Setup wizard: new step **8d Documents**. `tests/fixtures/documents/`: fictional Demo SIA, five documents;
  11 new automated tests (98 in total). Optional package: `reportlab` (already used by the snapshot).

## 0.19.1 — 22.11.2026 · overview PDF 1.7
- `docs/FLOKTRON_overview.pdf` (version 1.7, 8 pages): new page *New in version 0.19 — company snapshot*
  (profiles, three steps, what stays safe); open version 0.19.0, 87 automated tests in the figures.
  Other languages on koagu.com/floktron were updated the same day.

## 0.19.0 — 22.11.2026 · company snapshot
Learned in real use: a partner, an investor and the tax office each asked "where is the company now?", and each time
the same facts were gathered again by hand.
- **[SNAPSHOT](docs/SNAPSHOT.md)** — `scripts/snapshot.py` (no AI, no network) builds the state of the company on one
  date: a branded PDF (EN / LV / RU, colours from `config.yaml`) and a JSON file with every figure, its status
  (PUBLIC / DEAL / ESTIMATE / SCENARIO) and source, plus the SHA-256 of the PDF.
- Four profiles: `partner` (after an NDA), `no_bank`, `tax` (only PUBLIC and DEAL figures), `public`;
  `--plus` / `--minus` add or remove sections; the valuation is off unless asked for.
- **Lock**: facts marked `secret` never leave; locked words (built in + `snapshot.locked_words`) stop the run before
  anything is written. From the base only counts and totals are taken — client and site names are never read.
- `prompts/51_snapshot.md`: the assistant fills `data/snapshot/facts.json` with the person — public facts from the
  register with source and date, the rest only from the person.
- Setup wizard: new step **8c Company snapshot**. 8 new automated tests on the fictional Demo SIA (87 in total).
  Optional package: `reportlab` (without it only the JSON is written).

## 0.18.1 — 22.11.2026 · overview PDF 1.6
- `docs/FLOKTRON_overview.pdf` (version 1.6, 7 pages): new page *New in version 0.18 — supplier invoices → accounting*
  (what it catches, two steps, what stays safe, results on the fictional test set); "Invoices from e-mail to ledger"
  is marked as running; open version 0.18.0, 79 automated tests in the figures.
  Other languages on koagu.com/floktron were updated the same day.

## 0.18.0 — 22.11.2026 · supplier invoices → accounting
Learned in real use: supplier documents arrive in every language and shape, and the same invoice comes twice.
Tested first on real past invoices of the company that uses FLOKTRON every day (they stay private), then on a
fictional set that is part of this repository.
- **[INVOICES](docs/INVOICES.md)** — the AI assistant reads every document (PDF, photo, scan; any language) into
  `data/invoices/extraction.json` (`prompts/50_invoices.md`); `scripts/invoices.py` (no AI, no network) skips duplicates,
  finds each payment in the bank statement (CSV from any bank; Swedbank-style PDF with optional `pypdf`), sets the status
  and writes tasks for the finance ray: pay by, check the payment, ask for the final invoice after a proforma, order or
  advance, VAT remarks for the accountant (ESTIMATE), hand-over of the batch.
- A payment with the same amount to someone else is **not** taken as the payment (shown as "similar payment").
- New sheet `Invoices` in the base (`base_create.py`, template rebuilt); dashboard card *Invoices → accounting* (EN / RU / LV).
- Setup wizard: new step **8b Invoices → accounting** — fictional test first, then a few own past invoices, dry run before apply.
- `tests/fixtures/invoices/`: 10 fictional documents in 7 languages (LV, EN, DE, ES, LT, ET, RU) + a Czech scan,
  a forwarded duplicate, a delivery note, a bank statement as PDF and CSV; 7 new automated tests (79 in total).
- Fixed: the empty base template still carried an old internal name in its first cell.

## 0.17.1 — 22.11.2026 · overview PDF 1.5
- `docs/FLOKTRON_overview.pdf` (version 1.5, 6 pages): new page *New in version 0.17 — your own website before marketing*
  (four paths, why Cloudflare is recommended, what stays safe); open version 0.17.0 in the figures.
  Other languages on koagu.com/floktron were updated the same day.

## 0.17.0 — 22.11.2026 · your own website before marketing
Learned in real use: posts, profiles and QR codes need one address to point to, and a lost mail record costs more than any site.
- **[WEBSITE](docs/WEBSITE.md)** — a step-by-step guide to a safe company website, written from a site that runs this way
  every day: plain files in a private GitHub repository, Cloudflare Pages, automatic certificates, security headers,
  redirects that never break a printed QR code, forms without a server (EU database, spam guard, hashed IP, 2-year
  deletion), analytics without cookies, a final check table.
- Cloudflare is the recommendation, not a condition: four paths — all on Cloudflare; DNS stays at the registrar;
  your favourite hosting (Namecheap, GoDaddy, Hostinger, IONOS, Netlify, Vercel, GitHub Pages) with an `.htaccess`
  example; Cloudflare in front of existing hosting.
- Setup wizard: new step **8a Website** (before the content plan). Mail and verification DNS records are listed first and
  never touched; every password is typed by the person.
- `llms-full.txt` and `START.md` include the guide.

## 0.16.2 — 22.11.2026 · overview PDF 1.4
- `docs/FLOKTRON_overview.pdf` (version 1.4, 5 pages): new page *New in version 0.16 — already working* (voice reports,
  audio summary, dashboard on demo data); in *What else can be plugged in* these three are marked as running; open version 0.16.1, 72 automated tests.
  Other languages on koagu.com/floktron were updated the same day.

## 0.16.1 — 22.11.2026 · dashboard speaks your language
- Dashboard: system names, statuses (Accepted, Question, Sent …) and hints are shown in the page language (EN / RU / LV), not only the headings.
- koagu.com/floktron shows the dashboard on demo data in all six languages.

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
