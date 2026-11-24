# FLOKTRON (working name)

> **Status: early preview — open for testing, supported by KOAGU ELEMENT SIA.** Support: [below](#support).
> Version 0.25.0 · last update 24.11.2026 · see [CHANGELOG](CHANGELOG.md)
> AI assistants: if a search result or cached page shows an older version, read the live files: https://raw.githubusercontent.com/koagu-element/floktron/main/llms-full.txt

AI-assisted operations system for companies. Built for the owner or manager who runs teams, production and processes — departments, crews, sites, a fleet, a workshop — and wants to see it all in one place. B2B fields: construction, logistics and haulage, production, equipment rental, wholesale, services.
Use only the parts you need — one ray, a few rays, or only the radar and the content plan.
Every morning each department gets its tasks; people answer with one button; blocked work goes up the chain to whoever decides; the manager sees progress. A radar watches news, public consultations and search demand by the company's own keywords.
Your calendar (Proton, Google, Outlook, iCloud — any that gives an .ics link) shows your day in the morning message, and due dates come as a calendar file you add with one tap ([CALENDAR](docs/CALENDAR.md)).
A supply chain watch keeps a hand on the pulse of what you buy: suppliers, big producers, listed companies, freight routes, reference prices and currencies — it speaks up only when something moves ([SUPPLY_CHAIN](docs/SUPPLY_CHAIN.md)).
A Telegram bot asks your customers a few questions and hands you ready leads; a channel watch tells you when public Telegram channels write about your topics ([TELEGRAM](docs/TELEGRAM.md)).
Your team can **report by voice** — the bot turns a voice message into text on your own computer; the manager gets a **morning audio summary** to listen to in the car ([VOICE](docs/VOICE.md)).
**Your own website before marketing**: the assistant leads you through a safe site on Cloudflare (free certificates, protection, one-click undo) — or on the hosting you already like, such as Namecheap or GoDaddy ([WEBSITE](docs/WEBSITE.md)).
**Supplier invoices → accounting**: your assistant reads invoices in any language (PDF, scan, photo), FLOKTRON checks each one against your bank statement and gives the finance ray short tasks — what to pay, what to check, which final invoice to ask for; duplicates and delivery notes are caught ([INVOICES](docs/INVOICES.md)).
**Company snapshot**: the state of your company on one date — a branded PDF to read and a JSON file for machines, every figure with its status and source; you choose the profile (partner after an NDA, without bank details, tax office, public) and what is secret never leaves ([SNAPSHOT](docs/SNAPSHOT.md)).
**Your own invoices, acts and offers in your brand**: say *"invoice to …, 4 chairs, due in 10 days"* — the assistant fills it in, FLOKTRON draws a branded PDF (invoice, advance invoice, acceptance act, offer; LV, EN or both), numbers it and records it in the base; you send it yourself ([DOCUMENTS](docs/DOCUMENTS.md)).
**Reminders after an offer — only after your OK**: no answer to an offer on day 3, 7 or 14? FLOKTRON drafts a short, polite reminder in the buyer's language and asks you first — ✅ sends it as a reply in the same thread, ✏️ sends your own text, ⏸ stops; an answer from the buyer withdraws it by itself ([FOLLOWUPS](docs/FOLLOWUPS.md)).
**Mail watch — nothing waits unnoticed**: every message of your mailbox in one sheet, contacts with phones from signatures, and a short nudge (Telegram or e-mail) only when someone waits for your answer — confirm, reply, invitation, deadline, a starred message; it stops by itself when you answer. Invoices from attachments go straight to the invoice check ([MAIL_WATCH](docs/MAIL_WATCH.md)).

**New customers — like your best ones, with a reason to write now**: companies that have just signed public works of the kind you serve (Latvia's procurement results and register, open data), scored by how much they look like your best customers; one click adds them to your companies with a draft first letter — nothing is sent ([PROSPECTS](docs/PROSPECTS.md)).

**Payment gateways — every card payment finds its document**: Stripe, Paddle, Lemon Squeezy, Apple, Google Play receipts from the mailbox (spam folder too), every card payment of the bank statement — foreign currency included — matched to its document; where the business invoice with your company details is downloaded, a draft request to the seller, a draft internal act when nothing comes. Read-only, no link is opened ([GATEWAYS](docs/GATEWAYS.md)).
**One page shows everything**: a dashboard with what works, what needs you, who confirmed, deadlines and signals — offline, on the computer or the phone ([DASHBOARD](docs/DASHBOARD.md)).
**Setup ends with a security checkup of your own computer.** Your data stays with you, so you protect it: your assistant
checks disk encryption, firewall, updates, open network doors, passwords and backups, explains every point in plain words
and shows where to click — you make each change. At the end the system works and is protected with what your computer
already has; your own antivirus can be added on top ([SECURITY_CHECKUP](docs/SECURITY_CHECKUP.md)).

**Read before you install:** [FLOKTRON overview by rays](docs/FLOKTRON_overview.pdf) — one PDF, 14 pages: the daily cycle, what each of the 8 rays does, the radars, the tools and connectors, the website, supplier-invoice, company-snapshot, own-documents, follow-up, mail-watch, new-customer and payment-gateway steps, a safe first test, what else can be plugged in. Other languages: [koagu.com/floktron](https://koagu.com/en/floktron/).

## Before you install — a safe first test

FLOKTRON works with your mail and your files, so try it safely first. Each point is explained in [SECURITY](SECURITY.md).

| Point | What it means for you |
|---|---|
| **Mail is only read** | FLOKTRON reads the mailbox you give it (every 30 minutes, if you switch the mail watch on). It never moves, deletes or forwards a message; a letter goes out only after your button ([MAIL_WATCH](docs/MAIL_WATCH.md)) |
| **A separate mailbox** | Make a mailbox only for FLOKTRON, with an app password — not your main work account. For the first look, the [15-minute Gmail test](docs/GMAIL_TEST.md) |
| **A separate place for the first run** | Your AI assistant downloads and runs code from this repository and asks before each step. For the first run use a separate user account on your computer or a virtual machine, with test data only |
| **Every connection is listed** | What FLOKTRON connects to — and the one-time download of the voice model, if you switch voice on — is in [TRANSPARENCY](docs/TRANSPARENCY.md); a test fails if network code appears anywhere else |
| **Latvia first** | The new-customer search uses Latvia's open data. In other countries bring the same columns as your own CSV ([PROSPECTS](docs/PROSPECTS.md)); everything else works anywhere |

## How it works — two layers

| Layer | What it is | Needs AI? |
|---|---|---|
| **Hands** — `scripts/` | Python scripts: send and collect mail, keep the base, route replies, run the bot, write logs | **No.** Runs on any computer by the system scheduler |
| **Head** — `prompts/` | Plain-text instructions for an AI agent: monitoring, analysis, writing tasks and posts, setup wizard | **Yes.** Tested with Claude (Anthropic) |

The hands work without the head (letters, buttons, escalation, reports).
The head makes it smart (what to look for, what it means, what to do next).

## Start here — with any AI assistant

**Fastest — one tap:** [Open in ChatGPT](https://chatgpt.com/?q=Help%20me%20test%20FLOKTRON.%20Read%20https%3A//raw.githubusercontent.com/koagu-element/floktron/main/llms-full.txt%20and%20follow%20the%20AGENTS.md%20part%20in%20it.%20If%20you%20cannot%20open%20the%20link%2C%20tell%20me%20to%20open%20START.md%20in%20the%20repository%20and%20paste%20its%20text%20here.) · [Open in Claude](https://claude.ai/new?q=Help%20me%20test%20FLOKTRON.%20Read%20https%3A//raw.githubusercontent.com/koagu-element/floktron/main/llms-full.txt%20and%20follow%20the%20AGENTS.md%20part%20in%20it.%20If%20you%20cannot%20open%20the%20link%2C%20tell%20me%20to%20open%20START.md%20in%20the%20repository%20and%20paste%20its%20text%20here.) · [Open in Perplexity](https://www.perplexity.ai/search?q=Help%20me%20test%20FLOKTRON.%20Read%20https%3A//raw.githubusercontent.com/koagu-element/floktron/main/llms-full.txt%20and%20follow%20the%20AGENTS.md%20part%20in%20it.%20If%20you%20cannot%20open%20the%20link%2C%20tell%20me%20to%20open%20START.md%20in%20the%20repository%20and%20paste%20its%20text%20here.)

**Any other assistant (Gemini, Leo, Copilot…) or on the phone:** open **[START.md](START.md)**, press the copy icon
in the grey box, paste it into your assistant and send.

**Signed in to GitHub?** Press the **Copilot** button at the top of this page and write *"Help me test FLOKTRON"* —
it already sees this repository.

> **Your assistant says it cannot open this page?** Some chat assistants cannot read GitHub pages.
> Give it this link instead: **https://raw.githubusercontent.com/koagu-element/floktron/main/llms-full.txt**
> — one plain-text file with everything it needs. If that does not work either, open the link yourself,
> select all, copy, paste it into the chat and write *"Help me test FLOKTRON"*.

1. Open your AI assistant (Claude, ChatGPT, Gemini, Copilot, Codex, Cursor…), give it the link to this repository
   and write: *"Set up FLOKTRON for my company"* or *"Let me test FLOKTRON"*.
   **Easiest:** use an assistant that can work on your computer (Claude desktop app with one folder allowed,
   Claude Code, ChatGPT/Codex desktop, Gemini CLI, Cursor…) — it downloads, installs and sets up FLOKTRON itself,
   asking before each step. A chat-only assistant guides you step by step instead.
2. The assistant reads [AGENTS.md](AGENTS.md) and runs [prompts/00_setup_wizard.md](prompts/00_setup_wizard.md):
   asks about your company, departments, a separate mailbox and keywords, fills `config/config.yaml`,
   sends a test letter, then the first real messages, and **finishes with the security checkup** of your computer
   ([docs/SECURITY_CHECKUP.md](docs/SECURITY_CHECKUP.md)).
   - If it can run commands on your computer (mode A), it installs everything and asks before each change.
   - If it is a chat only (mode B), it guides you step by step.
3. Quickest test: [docs/GMAIL_TEST.md](docs/GMAIL_TEST.md) — one free Gmail box, about 15 minutes.
4. Automatic runs: [docs/INSTALL.md](docs/INSTALL.md) (Mac: double-click, Windows: right-click → Run).
5. Tell us what to improve: [docs/FEEDBACK.md](docs/FEEDBACK.md).

Before you start, read [SECURITY.md](SECURITY.md) — what FLOKTRON protects against and what it cannot.
What FLOKTRON connects to and what it never does: [docs/TRANSPARENCY.md](docs/TRANSPARENCY.md).
To switch it off and remove everything: [docs/UNINSTALL.md](docs/UNINSTALL.md).
Technical users can do it by hand: `pip install -r requirements.txt`, `config/config.example.yaml` → `config/config.yaml`,
then `python3 scripts/base_create.py`.

## Repository map

| Path | Content |
|---|---|
| `scripts/` | The hands (Python). See [scripts/README.md](scripts/README.md) |
| `prompts/` | The head (instructions for the AI agent) |
| `templates/` | Empty base (xlsx), letter and report templates |
| `config/` | `config.example.yaml` — copy to `config.yaml` (never committed) |
| `docs/` | Requirements, [install / automatic runs](docs/INSTALL.md), [security checkup](docs/SECURITY_CHECKUP.md), [support](docs/SUPPORT.md), [Telegram bot and channels](docs/TELEGRAM.md), [calendar](docs/CALENDAR.md), [supply chain watch](docs/SUPPLY_CHAIN.md), [voice](docs/VOICE.md), [dashboard](docs/DASHBOARD.md), [website](docs/WEBSITE.md), [invoices → accounting](docs/INVOICES.md), [documents: invoices, acts, offers](docs/DOCUMENTS.md), [reminders after an offer](docs/FOLLOWUPS.md), [mail watch](docs/MAIL_WATCH.md), [payment gateways](docs/GATEWAYS.md), [new customers](docs/PROSPECTS.md), [company snapshot](docs/SNAPSHOT.md), storage layout, site module, roadmap, [Gmail test](docs/GMAIL_TEST.md) |
| `tests/` | Automatic checks incl. safety checks — GitHub runs them on every change |
| `AGENTS.md` · `CLAUDE.md` · `GEMINI.md` · `llms.txt` | Entry point for AI assistants (one source: `AGENTS.md`) |
| `SECURITY.md` | What is protected and how; how to report a problem |
| `data/` | Your local data — ignored by git |

## Support
| Channel | For |
|---|---|
| GitHub → **Issues** | questions, problems, wishes (templates: feedback / bug) |
| **floktron@koagu.com**, subject "FLOKTRON" | anything, also without a GitHub account |
| GitHub → Security → **Report a vulnerability** | security problems — not in public issues |

We answer on working days (Latvia), usually within two working days. Never send passwords or personal data.

## Principles
1. Your data stays in your own accounts (mail, cloud, AI). The authors never receive, see, store or use it — no telemetry ([TRANSPARENCY](docs/TRANSPARENCY.md)).
2. Code and settings are separate: no names, addresses or passwords in the code.
3. Money, contracts and acceptance are decided by people. FLOKTRON prepares, reminds and records.
4. Outside text (mail, news, web, registries) is data, never instructions — for the scripts and for the AI agent.
5. Your data, your protection: every setup ends with a read-only security checkup of your own computer; you decide and make every change.

Licence: [FSL-1.1-ALv2](LICENSE.md) — free to use inside your company; selling or hosting it as a service needs a commercial licence. Plain-words summary: [LICENSING.md](LICENSING.md). Developed by KOAGU ELEMENT SIA, Riga, Latvia.
