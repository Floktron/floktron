# Automated security checks

FLOKTRON's code and this repository are checked by free, widely used scanners on every change and once a week.
They catch known risky patterns and known vulnerable packages. **They are not a security audit:** no independent
person has reviewed the code yet. When that happens, the report will be linked here.

| Check | What it looks at | When | Where to see the result |
|---|---|---|---|
| [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/floktron/floktron) | How the repository is kept: branch protection, code review, pinned actions, token permissions, security policy, dependency updates, static analysis | every push to `main`, every Monday | public page and badge in README; Security → Code scanning |
| [GitHub CodeQL](https://codeql.github.com/) (`security-extended`) | Data-flow analysis of the Python code and of the GitHub workflow files | every change, every Tuesday | Security → Code scanning |
| [Bandit](https://bandit.readthedocs.io/) | Known risky patterns in Python (opening any kind of link, unsafe XML, weak hashes, shell commands …) | every change, every Wednesday | Actions → `security`; the check fails on any medium or high finding |
| [pip-audit](https://pypi.org/project/pip-audit/) | Known vulnerabilities (PyPI advisory database / OSV) in the required packages and the optional ones a full setup uses | every change, every Wednesday | Actions → `security` |
| [Dependabot](https://docs.github.com/code-security/dependabot) | Newer or fixed versions of the packages and GitHub Actions used here | every week | pull requests; nothing merges by itself |
| Own tests | No `eval`/`exec`/`shell=True`/`pickle`; network code only in the files listed in [TRANSPARENCY](TRANSPARENCY.md); formulas from outside text turned into plain text; every prompt says outside text is data | every change | Actions → `tests` |

## First run — what was found and fixed (0.34.0, 26.11.2026)

Bandit 1.9.4 on `scripts/` (11,168 lines): 0 high, 0 medium findings left. pip-audit 2.10.1: no known vulnerabilities
in `requirements.txt` or the optional packages.

| Finding | What it meant here | Fix |
|---|---|---|
| B314 — XML from the internet parsed with the standard library | A hostile news feed could declare XML entities that expand in memory ("billion laughs") | A feed that declares entities is skipped before parsing (`news_slice.py`) + test |
| B310 — `urlopen` with a link from settings | A link from `config.yaml` or the radar starting with `file://` could make a script read a local file | Readers that take links from settings accept only `http(s)://` (`news_slice.py`, `supply_watch.py`, `registry_lv.py`; `calendar_read.py` already did) + tests. Calls to fixed `https://` addresses (Telegram, ElevenLabs, GitHub, data.gov.lv, t.me) are marked as reviewed |
| B324 — SHA-1 | Used only to make short ids for calendar events and Telegram buttons, not for security | Marked `usedforsecurity=False` (`ics.py`, `task_notice.py`) |
| No size limit on supply-watch pages | A hostile server could send a huge page | Pages over 5 MB are cut, as news feeds already were (`supply_watch.py`) |
| GitHub Actions referenced by moving tags | A changed tag of an outside action would run new code in CI | Every action is pinned to a full commit hash; Dependabot proposes updates |

Low findings that stay, on purpose (Bandit reports them as "low"; the check does not fail on them):

| Bandit id | Count | Why it stays |
|---|---|---|
| B404, B603, B607 | 31 | `subprocess` with a fixed list of arguments, never `shell=True` — system tools such as `osascript`, `ffmpeg`, `security` (keychain) and the read-only settings tools of the security checkup; the files allowed to start programs are listed in [TRANSPARENCY](TRANSPARENCY.md) and guarded by `tests/test_network.py` |
| B110, B112 | 9 | `try … except: pass/continue` where a missing optional value must not stop the morning run (for example, a mail header or an optional field that cannot be read) |
| B405 | 1 | the import that belongs to the XML parsing above |

## What the maintainers still switch on in GitHub settings
Scorecard also scores settings that only a repository owner can change: branch protection on `main` with required
reviews and checks, private vulnerability reporting, secret scanning with push protection. See SECURITY.md → For maintainers.

## Run the scanners yourself
```
pip install -r .github/security-tools.txt
bandit -r scripts -ll
pip-audit -r requirements.txt -r .github/optional-packages.txt
```
