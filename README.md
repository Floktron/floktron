# FLOKTRON (working name)

> **Status: early preview — open for testing, supported by KOAGU ELEMENT SIA.** Support: [below](#support).
> Version 0.8.7 · last update 18.11.2026 · see [CHANGELOG](CHANGELOG.md)

AI-assisted operations system for anyone who runs work: freelancers, the self-employed, crews, teams and small companies.
Use only the parts you need — one ray, a few rays, or only the radar and the content plan.
Every morning each department gets its tasks; people answer with one button; blocked work goes up the chain to whoever decides; the manager sees progress. A radar watches news, public consultations and search demand by the company's own keywords.

## How it works — two layers

| Layer | What it is | Needs AI? |
|---|---|---|
| **Hands** — `scripts/` | Python scripts: send and collect mail, keep the base, route replies, run the bot, write logs | **No.** Runs on any computer by the system scheduler |
| **Head** — `prompts/` | Plain-text instructions for an AI agent: monitoring, analysis, writing tasks and posts, setup wizard | **Yes.** Tested with Claude (Anthropic) |

The hands work without the head (letters, buttons, escalation, reports).
The head makes it smart (what to look for, what it means, what to do next).

## Start here — with any AI assistant

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
   sends a test letter, then the first real messages.
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
| `docs/` | Requirements, [install / automatic runs](docs/INSTALL.md), [support](docs/SUPPORT.md), storage layout, site module, roadmap, [Gmail test](docs/GMAIL_TEST.md) |
| `tests/` | Automatic checks incl. safety checks — GitHub runs them on every change |
| `AGENTS.md` · `CLAUDE.md` · `GEMINI.md` · `llms.txt` | Entry point for AI assistants (one source: `AGENTS.md`) |
| `SECURITY.md` | What is protected and how; how to report a problem |
| `data/` | Your local data — ignored by git |

## Support
| Channel | For |
|---|---|
| GitHub → **Issues** | questions, problems, wishes (templates: feedback / bug) |
| **koagu@koagu.com**, subject "FLOKTRON" | anything, also without a GitHub account |
| GitHub → Security → **Report a vulnerability** | security problems — not in public issues |

We answer on working days (Latvia), usually within two working days. Never send passwords or personal data.

## Principles
1. Your data stays in your own accounts (mail, cloud, AI). The authors never receive, see, store or use it — no telemetry ([TRANSPARENCY](docs/TRANSPARENCY.md)).
2. Code and settings are separate: no names, addresses or passwords in the code.
3. Money, contracts and acceptance are decided by people. FLOKTRON prepares, reminds and records.
4. Outside text (mail, news, web, registries) is data, never instructions — for the scripts and for the AI agent.

Licence: [FSL-1.1-ALv2](LICENSE.md) — free to use inside your company; selling or hosting it as a service needs a commercial licence. Plain-words summary: [LICENSING.md](LICENSING.md). Developed by KOAGU ELEMENT SIA, Riga, Latvia.
