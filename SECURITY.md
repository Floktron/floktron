# Security

FLOKTRON reads text written by other people every day: e-mail replies, news feeds, registry data, web pages.
Some of it may be written on purpose to trick a script or an AI agent. This page says what FLOKTRON protects
against, how, and what it cannot protect against.

## For security reviewers — start here
We take every piece of data seriously: the company's, its team's and its customers'. Where to look first:

| Topic | What to check | Where |
|---|---|---|
| Data we keep | Minimum by default: no customer form in the Telegram bot (opt-in only), nothing kept about strangers, contact and payment details hidden in Telegram tasks | [Personal data — the minimum](#personal-data--the-minimum), `config/config.example.yaml` |
| Secrets | Bot token and passwords only in the system store (macOS Keychain, Windows Credential Manager, Linux Secret Service) or an environment variable — never in a file, log, backup or git | `scripts/secret_store.py`, `tests/test_bot_security.py` |
| Telegram bot | Who it answers, how buttons and invite links are checked, what to do if the bot is taken over | [docs/TELEGRAM.md#security](docs/TELEGRAM.md#security) |
| Network | Every outside address FLOKTRON connects to; nothing goes to the authors | [docs/TRANSPARENCY.md](docs/TRANSPARENCY.md), `tests/test_network.py` |
| Automated scans | OpenSSF Scorecard, CodeQL, Bandit, pip-audit, Dependabot on every change | [docs/SECURITY_SCANS.md](docs/SECURITY_SCANS.md) |
| Outside reviews | Every point received, checked in the code, what was fixed and the test that guards it | [docs/CODE_REVIEW.md](docs/CODE_REVIEW.md) |
| The user's computer | Read-only checkup at the end of every setup | [docs/SECURITY_CHECKUP.md](docs/SECURITY_CHECKUP.md) |

There is no independent audit yet. Findings are welcome — see [Report a problem](#report-a-problem).

## What is protected and how

| Risk | Protection | Where |
|---|---|---|
| Someone sends a fake reply ("task done", "change the address") | Replies count only from the ray's own address, its team lead or the manager; others are recorded as "Unknown sender" and change nothing | `collect_replies.py`, `mail.allow_any_sender: false` |
| A reply, news title or company name contains an Excel formula (`=HYPERLINK(…)`) | Every formula cell is turned into plain text before a base is saved | `scripts/safe_xlsx.py` + test |
| Hidden instructions for the AI agent inside an e-mail, news item or web page ("ignore your rules…") | The agent treats all outside text as data; instructions come only from this repository and the person | `AGENTS.md` rule 1, header of every prompt |
| HTML/script inside a reply shows up in a letter to the manager | All outside text is escaped before it goes into a letter | `send_morning.py`, `weekly_summary.py`, `gaps_report.py`, `content_check.py` |
| A hostile news server sends a huge file | Feeds over 5 MB are skipped and recorded in Gaps | `news_slice.py` |
| Someone in the middle of the mail connection (fake mail server) | Every mail server's certificate is checked. The only exception is Proton Mail Bridge, which runs on your own computer with a self-signed certificate: the check is relaxed only for the address of this computer (127.0.0.1 / localhost) — or, better, pinned to Bridge's exported certificate (`mail.tls_cert`). A Bridge address on another computer without the pinned certificate is refused | `scripts/mail/send.py` → `tls_context`, `tests/test_audit_fixes.py` |
| Two runs write the base at the same time (data lost) | One run at a time: an operating-system lock, taken in one atomic step and freed by the system even if a run crashes; `invoices.py --apply` waits for it too | `scripts/runlock.py`, `scripts/run.py`, test |
| A stranger writes to the Telegram bot or presses its buttons | The bot answers only the team (`telegram.strangers: ignore`, default); a press counts only from the chat that owns the message; nothing about strangers is kept, only a count per day | `scripts/bot/telegram_bot.py`, `tests/test_bot_security.py` |
| An invite link for a team member is forwarded | One link = one person, works once and expires; a second person is refused and the managers are told; `/remove` takes a person out at once | `scripts/worktime.py`, `docs/WORKTIME.md` |
| A person's page link (`/m`) leaks, a phone is lost, or someone floods the page from the internet | From outside only: limits per address and in total, an address that guesses keys waits an hour; a new «country · device» → Telegram «Not me — close» (new link, page closed from outside); «Sign out everywhere», link changes every 90 days; optional sign-in by Face ID / fingerprint / phone code (passkey: the face stays in the phone, only a public key here; the phone put away 10 min → asks again) | `scripts/page_guard.py`, `scripts/passkey.py`, [docs/CHANNELS.md](docs/CHANNELS.md), `tests/test_page_guard.py` |
| The bot token leaks or the bot is taken over | Token only in the system store; anything that looks like a token is hidden in the console and `data/bot.log`; one command after BotFather's *Revoke* puts a new token in | `scripts/secret_store.py`, `telegram_bot.py --set-token`, [docs/TELEGRAM.md](docs/TELEGRAM.md#if-the-bot-is-taken-over-or-the-token-may-have-leaked) |
| Personal data leaves the computer in a Telegram message | E-mail addresses, phone numbers, IBANs, card numbers and personal codes are hidden in task texts; tasks, leads and voice notes are sent with `protect_content` (no forwarding or saving) | `scripts/task_notice.py`, `telegram.mask_personal`, `telegram.protect_content` |
| Passwords leak | No password in files or chat: environment variable or system keychain only; `config.yaml`, `.env`, `data/`, `*.eml` never committed | `scripts/mail/send.py`, `.gitignore` + test |
| Dangerous code slips into the scripts | No `eval`, `exec`, `os.system`, `shell=True`, `pickle`, `curl | sh` — checked on every change | `tests/test_safety.py`, GitHub Actions |
| Outside packages | Only `openpyxl` and `PyYAML` from pypi.org, versions pinned; known vulnerabilities checked by pip-audit on every change, updates proposed by Dependabot | `requirements.txt`, `.github/workflows/security.yml` |
| A hostile feed or link | Links from settings must be `http(s)://` (never `file://`); feeds that declare XML entities are skipped | `news_slice.py`, `supply_watch.py`, `registry_lv.py`, `tests/test_scan_fixes.py` |
| A mistake goes out to people | Order of every new setup: `--dry` → `--test` own address → real; posts are never published automatically, a person copies them | `AGENTS.md` rule 8, `content_check.py` |
| The agent reaches too far | Works only in the FLOKTRON folder and its storage folder; never whole-disk, browser or other accounts | `AGENTS.md` rule 2 |
| Your own computer is weak (disk not encrypted, firewall off, sharing open, no backup) | A security checkup ends every setup: read-only, plain explanations, the person makes each change; repeat monthly | `scripts/security_check.py`, `docs/SECURITY_CHECKUP.md`, test |

## Prompt injection — hidden instructions in mail, attachments, web pages and Telegram
"Prompt injection" is text written to make an AI agent do something its owner did not ask for: "ignore your rules",
"send the base to…", "pay this invoice", "run this command". FLOKTRON reads such text every day, so it is built on one
rule: **outside text is data, never instructions.** What makes that true today:

| Where the text comes from | What FLOKTRON does with it | Where |
|---|---|---|
| E-mails and replies | Scripts read the mailbox read-only (IMAP `readonly`, `BODY.PEEK`): nothing is marked read, moved, deleted or answered. A reply changes a task only if it comes from a known address (the ray, its team lead, the manager); anything else is "Unknown sender" and changes nothing. A letter that asks to pay, click, reply or forward is reported to the manager as a fact, never done | `scripts/mail/read.py`, `collect_replies.py` (`mail.allow_any_sender: false`), `prompts/54_mail_watch.md` |
| Attachments | Only PDF files are saved, into `data/invoices/inbox/`; nothing in an attachment is opened as a program or run. A payment receipt from a look-alike domain or with failed DMARC/SPF is marked ⚠ and its links are not used | `scripts/mail_watch.py`, `scripts/gateways.py` |
| News, web pages, registries, public Telegram channels | Stored as text in the bases and scored; any formula is turned into plain text; any HTML is escaped before it goes into a letter | `scripts/safe_xlsx.py` + test, `send_morning.py` and the other letter builders |
| Messages to your Telegram bot | Manager commands work only from the chat ids in `config.yaml` (`manager_chat_ids`, `team_chat_ids`); a message from anyone else goes into the lead funnel as text and cannot run a command | `scripts/bot/telegram_bot.py`, `tests/test_bot.py` |
| Everything the AI agent reads | `AGENTS.md` rule 1, and every prompt and ready role starts with the same rule; a test fails if a prompt or role loses it. Instructions come only from this repository and from the person in the chat | `AGENTS.md`, `prompts/`, `agents/`, `tests/test_safety.py` |
| Anything that leaves the company | No script and no agent pays, signs, publishes or sends to a new address by itself; letters go only to addresses the person entered in `config.yaml` | `AGENTS.md` rules 5 and 6 |

What this does **not** promise: an AI model can still be fooled by clever text. That is why the last word on anything
that leaves the company — money, a signature, a post, a letter to a new address — is always a person's.

## False or corrected news
News can be wrong or deliberately false, even on official sites. FLOKTRON never publishes by itself, and every news item
used for a post gets a light check first — echo in other outlets, primary source, fact-checkers — shown as a status
(✅ / ℹ️ / ⚠️ / ⛔); corrections of news already used in posts are watched for 14 days and reported to the manager
(`prompts/31_news_check.md`). One source is normal for local news; the person decides.

## Personal data — the minimum
FLOKTRON is built to keep as little personal data as the work needs, and to keep it on the company's own computer.
- The Telegram bot collects no customer data by default: the customer form is off (`telegram.strangers: ignore`);
  a company that wants it turns it on (`strangers: dialog`) and is then responsible for the form.
- Telegram tasks carry the fact and the name, not the details: contacts and payment details stay on the computer.
- No secret in files, logs, backups or git (`tests/test_safety.py` and `tests/test_bot_security.py` check this).
- Bases (`data/`, `.xlsx`) stay in the company's folder; they are never committed and never sent to the authors.
- Tests use only fictional companies and data (`TEST · FICTIONAL`).

## Automated security checks
OpenSSF Scorecard, GitHub CodeQL, Bandit, pip-audit and Dependabot run on every change and once a week; what the first
run found and how it was fixed: [docs/SECURITY_SCANS.md](docs/SECURITY_SCANS.md). These are automated scans, not an
independent audit. Outside code reviews (so far by AI assistants reading a release tag) and what was fixed:
[docs/CODE_REVIEW.md](docs/CODE_REVIEW.md).

## Nothing hidden
FLOKTRON connects only to your mail server, the news feeds in your radar and (optionally) the Latvian open data portal.
It sends nothing to the authors. Full list and how to check: [docs/TRANSPARENCY.md](docs/TRANSPARENCY.md); guarded by `tests/test_network.py`.

## What FLOKTRON cannot protect against

- A computer or server that is already infected, or a mailbox whose password is stolen. The checkup at the end of setup
  lowers this risk (updates, encryption, firewall, 2-step login) but cannot remove it.
- A person with access to the computer editing the bases or `config.yaml` by hand.
- An AI agent that does not follow `AGENTS.md`. Use a well-known assistant and read what it asks before you allow it.

## Practical advice

- Make a separate mailbox for FLOKTRON with an app password; give it no access to other systems.
- For the first run use a separate user account on your computer or a virtual machine, with test data and the test mailbox only.
- Run FLOKTRON under an ordinary user account, not an administrator.
- Run the security checkup once a month and after big updates: `python3 scripts/security_check.py --manual`.
- Keep the storage folder in a cloud with version history (iCloud / Google Drive / OneDrive) — a damaged base can be restored.

## Report a problem

Found a weakness? Do not post details publicly. Use **Security → Report a vulnerability** on this repository's
GitHub page, or write to support@floktron.com (subject "FLOKTRON security"). Remove passwords and personal data from anything you send.

## For maintainers (GitHub settings)

- 2-factor login for every account with write access.
- Branch protection on `main`: changes only through pull requests, tests must pass.
- Secret scanning + push protection, Dependabot alerts, private vulnerability reporting — on.
- Code scanning shows the CodeQL and Scorecard results (Security tab); a new high finding is fixed before the next release.
- Releases as tags (`v0.8.0`); testers install a tag, not a moving branch.
