# Move and backup — the whole setup in one archive

A company changes its computer, moves from one AI assistant to another (for example from Gemini to Claude, or from
ChatGPT to Copilot), or hands the work to a new manager. FLOKTRON packs **everything the company set up** into one
password-protected file and sets it up again on the other computer — with any AI assistant. The same archive,
made every week by itself, is the backup.

Nothing is sent anywhere. The archive is one file on your own computer; you decide where it goes.

## One button

| What | Mac | Windows | Linux | Any AI assistant |
|---|---|---|---|---|
| Pack | double-click `scripts/install/move_mac.command` → `1` | double-click `scripts\install\move_windows.bat` → `1` | `sh scripts/install/move_linux.sh` → `1` | *"Pack FLOKTRON for a move"* |
| Unpack on the new computer | the same → `2` | the same → `2` | the same → `2` | *"Unpack the FLOKTRON move archive"* |
| Backup now | the same → `4`, or `/backup` to the Telegram bot | the same → `4` | the same → `4` | *"Make a FLOKTRON backup"* |

Behind the buttons is one script, `scripts/move.py` (`pack`, `check`, `unpack`, `backup`, `secrets`).

## What is in the archive

| Inside | What |
|---|---|
| `config/config.yaml` | your settings **without passwords** (any field that looks like a password or token is emptied) |
| `config/…` | the other settings files you made: bot dialog, channel list, keywords |
| `data/` | bases, company library, documents, reports, snapshots, audio; `data/context/` — the company's notes for its assistant |
| `custom/` | only the files in `prompts/` and `agents/` the company changed (compared with the shipped version) |
| `COMPANY_CONTEXT.md` | the company in one page for any AI assistant: name, departments, parts switched on, words that must never leave the company, and every note in `data/context/` |
| `SECRETS_TO_ENTER.md` | which passwords to type in again — **names only**, where they are read from (environment variable or keychain) |
| `SCHEDULE.md` | the automatic runs as a plain table and the one command that switches them on for each system |
| `MANIFEST.json` | version, date, profile, SHA-256 and size of every file, what was left out and why |
| `MOVE.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | "start here" for the person and for any agent that opens the folder |

**Never inside:** passwords, tokens, keys, private calendar links; files whose name or text looks like one
(`.env`, `*.pem`, `*.key`, Telegram or API tokens…) are left out and listed in `MANIFEST.json`. Before the archive is
written, every text file in it is checked once more — one hit stops the run and nothing is written.

## The password

- AES-256 (needs one extra package: `python3 -m pip install --user pyzipper` — the buttons install it).
- At least 10 characters, typed twice. It is **not stored** in the archive, next to it or in FLOKTRON. Write it down
  where the company keeps its passwords — without it the archive cannot be opened, also not by the authors.
- For the weekly backup the password comes from an environment variable or the macOS Keychain
  (`move.password_env`, `move.keychain_service`). Not set → the backup does not run and the dashboard shows it.
- `--no-password` exists for tests; then the archive must be kept like any other company document.

## On the new computer

1. Get FLOKTRON into one folder (github.com/floktron/floktron), with any AI assistant that works on the computer.
2. Put the archive into that folder and say: *"Unpack the FLOKTRON move archive"* (or press the button → `2`).
3. `move.py unpack` checks every file against `MANIFEST.json`. What is already in `data/` and `config.yaml` is moved
   aside into `data/data_before_move_<date>/` — nothing is deleted.
4. It writes `data/move/AFTER_MOVE.md` — the assistant goes through it with you: passwords again (you type them),
   paths that pointed to the old computer, the schedule (on here, **off on the old computer** so messages do not go out
   twice), the capacity check, the security checkup, a test message to your own address.
5. The company's own prompts and roles: same FLOKTRON version → put back in place (the shipped file is kept as
   `*.shipped`); a different version → kept in `data/move/restored_custom/`, the assistant compares and takes over
   what the company changed. Nothing is overwritten silently.

From Mac to Windows or Linux and back works the same: the schedule is stored as times, not as system entries.

## Profiles

| Profile | For | What changes |
|---|---|---|
| `full` (default) | your own move or backup | everything above |
| `handover` | a new manager or a new structure of the company | e-mails and phones of people are removed from the config; sheets *Mail*, *Contacts*, *Receipts*, *Voice*, *Leads* are left out of the bases and contact columns (e-mail, phone, messenger, responsible) are emptied; folders with letters, replies and voice are left out. The new team is entered again |

`--no-media` leaves audio, video and photos out (the company library always stays in).

## Chats and memory of the AI assistant

The chats and the memory inside an AI vendor's app belong to that vendor's account — FLOKTRON does not read them.
What the company wants its next assistant to know goes into **`data/context/`** (plain Markdown), and it travels in
every archive and in `COMPANY_CONTEXT.md`:

1. Ask the old assistant: *"Write down everything you remember about me and my company — rules, preferences,
   ongoing work — as plain text."* Read it, remove what is private, save it as `data/context/assistant_memory.md`.
2. The vendors also have their own tools (check their help pages, they change): ChatGPT and Claude can export all
   data from their settings; Gemini can import memory and chats from other assistants; Claude can import memory
   from other assistants. These move the chats — FLOKTRON moves the company.

## Weekly backup

```yaml
move:
  backup: true            # every Sunday 19:30 (schedule → backup to change)
  keep: 4                 # the last 4 archives are kept
  backup_dir: ""          # empty = <storage.root>/FLOKTRON_backup, else data/backups
  password_env: "FLOKTRON_MOVE_PASSWORD"
  keychain_service: "FLOKTRON_MOVE"   # Mac: security add-generic-password -s FLOKTRON_MOVE -a floktron -w
```

The backup goes to the company cloud folder when `storage.root` exists — so a lost computer does not take the backup
with it. Restore = the same `unpack`. Switch the automatic runs on again after changing `move.backup`
(`scripts/install/…` → `on`).

## Check it yourself

`python3 scripts/move.py check <archive>` opens the archive, recomputes every SHA-256 and lists the passwords to type
in again. `python3 -m pytest tests/test_move.py` runs the checks on a fictional company (TEST · FICTIONAL Demo SIA).
