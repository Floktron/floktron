# What FLOKTRON does on your computer — and what it never does

All code is open in this repository. Nothing is hidden or compiled. The only thing downloaded later is the speech
model — once, and only if you switch voice on (see the table). You (or your AI assistant) can read every file and
check every point below.

## Your AI assistant is a separate service
Scripts, bases and files stay on your computer. The text your AI assistant reads (a mail summary, a task, a document
you show it) is processed by that assistant's provider (Anthropic, OpenAI, Google…) under its own terms — FLOKTRON
does not control that. Show it only what you would show that service; for sensitive work use a business plan with no
training on your data.

Text from e-mails, attachments, web pages and Telegram is treated as data, never as instructions — how, in
[SECURITY.md](../SECURITY.md#prompt-injection--hidden-instructions-in-mail-attachments-web-pages-and-telegram).

## FLOKTRON connects only to
| Where | Why | Code |
|---|---|---|
| Your own mail server (IMAP / SMTP), with the address and app password you set | send the morning letters, read the replies; for reminders after an offer (if switched on) — see which offers were sent and answered; for online meetings (if switched on) — find inbox letters with a meeting link (read only, letters stay unread) | `scripts/mail/read.py`, `scripts/mail/send.py` |
| News feeds (RSS) and public Telegram channel pages (`t.me/s/<channel>`) listed in your own radar base | the news slice by your keywords — no Telegram account or login is used | `scripts/news_slice.py` |
| Public Telegram channel pages `t.me/s/<channel>` from your own channel list (only if you use the channel watch) | posts with your keywords | `scripts/tg_watch.py` |
| api.telegram.org — only if you switch the Telegram bot on, with the bot token you created | receive messages people send to YOUR bot, answer them, tell the manager about a new lead | `scripts/bot/telegram_bot.py` |
| The private read-only link of YOUR calendar (.ics), only if you switch the calendar on | today's events for the morning message; FLOKTRON never writes to your calendar | `scripts/calendar_read.py` |
| Yahoo Finance public chart data (query1.finance.yahoo.com), Google News RSS and the supplier pages you put into your own Watchlist (only if you use the supply chain watch) | end-of-day prices of the tickers you listed; news about your suppliers, routes and rules; a fingerprint of the supplier page text | `scripts/supply_watch.py` |
| api.elevenlabs.io — ONLY if you set `telegram.voice.stt_engine` or `tts_engine` to `elevenlabs`, with your own API key. By default voice stays on your computer (local Whisper model, the system voice) | turn a voice report into text / read the audio summary aloud | `scripts/voice.py` |
| huggingface.co — ONCE, only if you switch voice on with the local engine `faster-whisper` (or openaipublic.azureedge.net with `openai-whisper`) | the speech model is downloaded one time ("small" ≈ 460 MB) and kept on your computer; after that speech → text works offline. No voice, text or data is sent | the `faster-whisper` / `openai-whisper` package, called from `scripts/voice.py` |
| api.github.com — once a day with the morning run, unless you set `updates.check: false` (docs/UPDATES.md) | ask for the list of FLOKTRON releases to tell the manager that a newer version is out; one anonymous request — no account, no ID, nothing about you or your company is sent | `scripts/update_check.py` |
| Nothing outside your computer: the desktop icon (only if you make it) opens your own local `data/dashboard.html` (a `file://` page) in your default browser | open the dashboard with one double-click | `scripts/desktop_icon.py` |
| YOUR own cameras in your own network, at the addresses you wrote in `cameras.items` (only if you switch cameras on). Cameras marked `demo: true` are never contacted | one latest frame per camera, saved in `data/cameras/` and overwritten; no video is streamed or recorded, nothing is sent anywhere | `scripts/cameras.py` |
| Latvian open data portal data.gov.lv (only if you switch the registry on) | new companies by words in the name | `scripts/registry_lv.py` |
| data.gov.lv public procurement results (EIS) and the register (only if you switch prospects on) | who has just signed a contract of the kind you serve; form, town, registration date of those companies | `scripts/registry_lv.py` (used by `scripts/prospects.py`) |

There are no other network calls. An automatic test (`tests/test_network.py`) fails if network code appears
in any other file, or if the model download is missing from this list.

## FLOKTRON never
- sends anything to the authors (KOAGU ELEMENT SIA) or anyone else — no telemetry, no statistics, no "phone home"; the
  daily release check only reads the public release list on GitHub, and nobody collects your contact details to tell you about new versions;
- reads files outside its own folder and the storage folder you named in `config.yaml` — the one exception is the security
  checkup you start yourself: it reads system settings and the *names* of programs that start by themselves, never your files;
  and the move archive you point `scripts/move.py unpack` to (docs/MOVE.md) — the weekly backup is written only to
  `move.backup_dir`, the storage folder or `data/backups`;
- stores passwords in files — only the environment variable or the system keychain;
- runs hidden commands. The only programs it starts are its own scripts (`scripts/run.py`) and, on a Mac,
  the system keychain tool `security` to read the mail password, the calendar link and the backup password (`scripts/mail/send.py`) and the bot token
  (`scripts/secret_store.py`, used by `scripts/bot/telegram_bot.py`; on Linux also `secret-tool` if installed, and on any system the
  package `keyring` if you installed it — they read and save only the bot token, under the name in `telegram.keychain_service`); for voice (only if you switch it on) `scripts/voice.py` starts the system speech tools `say` and `afconvert` (Mac)
  or `espeak-ng` / `ffmpeg` (Linux) — the local speech model itself runs inside Python; the security checkup starts only the system's own read-only settings tools
  (the list `READ_ONLY_COMMANDS` in `scripts/security_check.py`, guarded by a test) and connects to nothing; the capacity
  check (`scripts/capacity_check.py`) starts only `sysctl -n hw.memsize` on a Mac to read the memory size. `scripts/desktop_icon.py` starts PowerShell once on Windows, only when you make the desktop icon, to save the shortcut. `scripts/cameras.py` starts `ffmpeg` (only if you list an `rtsp://` camera) to take one frame from YOUR camera.

## Check it yourself
1. Ask your AI assistant: *"Read all files in scripts/ and tell me every place where FLOKTRON connects to the internet
   or runs another program."* The answer should match the table above.
2. Run the checks: `pip install -r requirements.txt pytest && pytest -q` — the safety and network tests are included.
3. Search the code: `grep -rn "urlopen\|smtplib\|imaplib\|subprocess" scripts`.

Something looks wrong? Write to support@floktron.com (subject "FLOKTRON security") or use GitHub → Security → Report a vulnerability.
