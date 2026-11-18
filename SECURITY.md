# Security

FLOKTRON reads text written by other people every day: e-mail replies, news feeds, registry data, web pages.
Some of it may be written on purpose to trick a script or an AI agent. This page says what FLOKTRON protects
against, how, and what it cannot protect against.

## What is protected and how

| Risk | Protection | Where |
|---|---|---|
| Someone sends a fake reply ("task done", "change the address") | Replies count only from the ray's own address, its team lead or the manager; others are recorded as "Unknown sender" and change nothing | `collect_replies.py`, `mail.allow_any_sender: false` |
| A reply, news title or company name contains an Excel formula (`=HYPERLINK(…)`) | Every formula cell is turned into plain text before a base is saved | `scripts/safe_xlsx.py` + test |
| Hidden instructions for the AI agent inside an e-mail, news item or web page ("ignore your rules…") | The agent treats all outside text as data; instructions come only from this repository and the person | `AGENTS.md` rule 1, header of every prompt |
| HTML/script inside a reply shows up in a letter to the manager | All outside text is escaped before it goes into a letter | `send_morning.py`, `weekly_summary.py`, `gaps_report.py`, `content_check.py` |
| A hostile news server sends a huge file | Feeds over 5 MB are skipped and recorded in Gaps | `news_slice.py` |
| Passwords leak | No password in files or chat: environment variable or system keychain only; `config.yaml`, `.env`, `data/`, `*.eml` never committed | `scripts/mail/send.py`, `.gitignore` + test |
| Dangerous code slips into the scripts | No `eval`, `exec`, `os.system`, `shell=True`, `pickle`, `curl | sh` — checked on every change | `tests/test_safety.py`, GitHub Actions |
| Outside packages | Only `openpyxl` and `PyYAML` from pypi.org, versions pinned | `requirements.txt` |
| A mistake goes out to people | Order of every new setup: `--dry` → `--test` own address → real; posts are never published automatically, a person copies them | `AGENTS.md` rule 8, `content_check.py` |
| The agent reaches too far | Works only in the FLOKTRON folder and its storage folder; never whole-disk, browser or other accounts | `AGENTS.md` rule 2 |

## Nothing hidden
FLOKTRON connects only to your mail server, the news feeds in your radar and (optionally) the Latvian open data portal.
It sends nothing to the authors. Full list and how to check: [docs/TRANSPARENCY.md](docs/TRANSPARENCY.md); guarded by `tests/test_network.py`.

## What FLOKTRON cannot protect against

- A computer or server that is already infected, or a mailbox whose password is stolen.
- A person with access to the computer editing the bases or `config.yaml` by hand.
- An AI agent that does not follow `AGENTS.md`. Use a well-known assistant and read what it asks before you allow it.

## Practical advice

- Make a separate mailbox for FLOKTRON with an app password; give it no access to other systems.
- Run FLOKTRON under an ordinary user account, not an administrator.
- Keep the storage folder in a cloud with version history (iCloud / Google Drive / OneDrive) — a damaged base can be restored.

## Report a problem

Found a weakness? Do not post details publicly. Use **Security → Report a vulnerability** on this repository's
GitHub page, or write to koagu@koagu.com (subject "FLOKTRON security"). Remove passwords and personal data from anything you send.

## For maintainers (GitHub settings)

- 2-factor login for every account with write access.
- Branch protection on `main`: changes only through pull requests, tests must pass.
- Secret scanning + push protection, Dependabot alerts, private vulnerability reporting — on.
- Releases as tags (`v0.8.0`); testers install a tag, not a moving branch.
