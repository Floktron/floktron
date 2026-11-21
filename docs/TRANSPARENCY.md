# What FLOKTRON does on your computer — and what it never does

All code is open in this repository. Nothing is hidden, compiled or downloaded later. You (or your AI assistant)
can read every file and check every point below.

## FLOKTRON connects only to
| Where | Why | Code |
|---|---|---|
| Your own mail server (IMAP / SMTP), with the address and app password you set | send the morning letters, read the replies | `scripts/mail/read.py`, `scripts/mail/send.py` |
| News feeds (RSS) and public Telegram channel pages (`t.me/s/<channel>`) listed in your own radar base | the news slice by your keywords — no Telegram account or login is used | `scripts/news_slice.py` |
| Public Telegram channel pages `t.me/s/<channel>` from your own channel list (only if you use the channel watch) | posts with your keywords | `scripts/tg_watch.py` |
| api.telegram.org — only if you switch the Telegram bot on, with the bot token you created | receive messages people send to YOUR bot, answer them, tell the manager about a new lead | `scripts/bot/telegram_bot.py` |
| The private read-only link of YOUR calendar (.ics), only if you switch the calendar on | today's events for the morning message; FLOKTRON never writes to your calendar | `scripts/calendar_read.py` |
| Yahoo Finance public chart data (query1.finance.yahoo.com), Google News RSS and the supplier pages you put into your own Watchlist (only if you use the supply chain watch) | end-of-day prices of the tickers you listed; news about your suppliers, routes and rules; a fingerprint of the supplier page text | `scripts/supply_watch.py` |
| Latvian open data portal data.gov.lv (only if you switch the registry on) | new companies by words in the name | `scripts/registry_lv.py` |

There are no other network calls. An automatic test (`tests/test_network.py`) fails if network code appears
in any other file.

## FLOKTRON never
- sends anything to the authors (KOAGU ELEMENT SIA) or anyone else — no telemetry, no statistics, no "phone home";
- reads files outside its own folder and the storage folder you named in `config.yaml` — the one exception is the security
  checkup you start yourself: it reads system settings and the *names* of programs that start by themselves, never your files;
- stores passwords in files — only the environment variable or the system keychain;
- runs hidden commands. The only programs it starts are its own scripts (`scripts/run.py`) and, on a Mac,
  the system keychain tool `security` to read the mail password and the calendar link (`scripts/mail/send.py`) and the bot token
  (`scripts/bot/telegram_bot.py`); the security checkup starts only the system's own read-only settings tools
  (the list `READ_ONLY_COMMANDS` in `scripts/security_check.py`, guarded by a test) and connects to nothing.

## Check it yourself
1. Ask your AI assistant: *"Read all files in scripts/ and tell me every place where FLOKTRON connects to the internet
   or runs another program."* The answer should match the table above.
2. Run the checks: `pip install -r requirements.txt pytest && pytest -q` — the safety and network tests are included.
3. Search the code: `grep -rn "urlopen\|smtplib\|imaplib\|subprocess" scripts`.

Something looks wrong? Write to floktron@koagu.com (subject "FLOKTRON security") or use GitHub → Security → Report a vulnerability.
