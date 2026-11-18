# Changelog

History of FLOKTRON. Newest first.
Every change in this repository is also a git commit with date and description — the full archive.

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
