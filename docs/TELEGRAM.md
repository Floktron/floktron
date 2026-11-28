# Telegram — a bot that turns chats into leads, and a watch on public channels

Two optional parts. Both run on your own computer; nothing goes through the authors.

| Part | What you get | File |
|---|---|---|
| **Bot** | People open your bot, answer a few questions with buttons (what they need → company / crew / private → contacts). Each finished dialog is a lead in `floktron_leads.xlsx` and a Telegram message to you. | `scripts/bot/telegram_bot.py` |
| **Channel watch** | Public Telegram channels you choose are checked by your keywords at set times. Matches come to you in Telegram and go to `tg_signals.xlsx`. | `scripts/tg_watch.py` (run by the bot) |

## How setup goes (your AI assistant leads, you decide)
1. **Goal.** What should the bot do: take requests, orders, support questions, send you reports — or only watch channels?
2. **Dialog.** The assistant writes `config/bot_flow.yaml` from your answers: questions, buttons, branches (e.g. company / private), languages. It checks the file without internet: `python3 scripts/bot/telegram_bot.py --flow-check`. You read every text.
3. **Create the bot — you, in Telegram.** Search **@BotFather** — only the one with the blue check mark and exactly this name. `/newbot` → name → username ending in `bot`. Then `/setjoingroups` → **Disable**, `/setdescription`, `/setabouttext`, `/setcommands`.
4. **Token — you, never in chat.** BotFather gives a token (the key to your bot). Any computer:
   `python3 scripts/bot/telegram_bot.py --set-token` — paste it (nothing is shown); it goes into the system store
   (macOS Keychain; Windows Credential Manager or Linux Secret Service through the package `keyring`, Linux `secret-tool`)
   and is checked with Telegram. Mac: double-clicking `scripts/install/telegram/1_token.command` does the same. A server
   without a store: environment variable `FLOKTRON_TG_TOKEN`. Do not paste the token into any chat, file, e-mail or screenshot.
5. **Check:** `2_check.command` (or `python3 scripts/bot/telegram_bot.py --check`) → `OK — bot @…`.
6. **You become the manager.** Start the bot, open it in Telegram, send `/id`, put the number into `telegram.manager_chat_ids`, restart the bot.
7. **Test every branch** together with the assistant: each finished dialog must arrive to you and appear in `floktron_leads.xlsx`.
8. **Autostart:** `4_autostart_on.command` (Mac) — see "macOS and iCloud" below.
9. **Channels:** forward the bot any post from a public channel → it is added to the watch list (`/channels` shows the list). Times: `telegram.watch_times`, e.g. `["07:05", "18:40"]`.

## Who the bot talks to (0.38)
`telegram.strangers: ignore` (the default): the bot answers **only the team** — `manager_chat_ids`, `team_chat_ids`,
voice users and people who joined with a valid invite link. Anyone else gets no answer, no dialog, no buttons, and
nothing about them is kept (only a count per day in the log, no names, no text). `/id` answers a stranger only while
`manager_chat_ids` is still empty — for your first setup.
`telegram.strangers: dialog` switches the client dialog (leads) on for strangers. Leads are personal data: switch it on
only when you need it, and keep `/privacy` and `/forget` texts in your dialog.

## Tasks: yes / no
Your own chat with the bot is a work chat. The manager (`manager_chat_ids`), the team (`team_chat_ids`) and voice users
**never get the client dialog**: free text and `/start` give a short help, no lead is made. `/client` shows the dialog to try it.

One task = one message with two buttons — mail waiting for you ([Mail watch](MAIL_WATCH.md)), a new prospect
([Prospects](PROSPECTS.md), top 3 only), a card payment without a document ([Gateways](GATEWAYS.md)):

```
📬 Mail · Demo Partner SIA
«Offer for site 7?» · 19.11
waiting 6 d.
[✅ Answered] [⛔ Not needed]
```

- A press → the message turns into `✅ Closed · 25.11 10:31` (buttons gone); the bot writes one line to
  `data/task_actions.jsonl`; the script of that task moves it into its sheet on its next run.
- **Reply** to a task message with text (swipe → Reply) → ✅ with your comment.
- No text about sheets or columns; summaries with nothing to do come without buttons.
- Your own words: `telegram.team_texts` (help, closed_y, closed_n, toast, reply_closed, already).
- Another channel for some people: with [channels](CHANNELS.md) each person chooses Telegram, their own page (an app on
  the phone) or e-mail (+ push), and the same buttons work there; if Telegram is silent, the task goes to the backup channel.

## Work time: start, pause, end

With `worktime.enabled` the team gets three buttons under the message field: ▶ Start (with one location point when
`worktime.geo` is on) · ⏸ Pause · ⏹ End. `/hours` — my hours; `/who` — who is at work now (managers). The bot asks
«Still at work?» at `worktime.remind_at`. Details and what is kept: [WORKTIME](WORKTIME.md).

## Security
| Risk | What happens | Protection in FLOKTRON |
|---|---|---|
| Token leaks | whoever has it controls the bot and reads what people send | system store / environment variable only; never in files, code, logs, backups or chat; anything that looks like a token is hidden in the bot's output and `data/bot.log`; `--set-token` replaces it in one step (below) |
| Your Telegram account is taken over | BotFather hands over all your bots | turn on **Two-Step Verification** (cloud password), passkey, login e-mail; check **Active sessions** (below) |
| Strangers write to the bot | spam, attempts to get data or press old buttons | `strangers: ignore` — they get nothing; buttons and commands work only for the team; a button press counts only from the person in whose chat it is |
| An invite link is forwarded | a stranger joins the team | a link works once, for one person, until its date; a second person is refused and the managers are told; `/remove <chat id>` |
| A task message is forwarded | names, sums go further | `protect_content`: tasks, leads and voice notes cannot be forwarded or saved; tasks hide e-mails, phones, IBANs, card numbers, personal codes (`mask_personal`) |
| Fake BotFather | look-alike names ask for the token or money | only @BotFather with the blue check mark |
| Bot added to strange groups | spam, data collection | works only in private chats; `/setjoingroups` → Disable |
| Someone pretends to be the manager | wants to see leads | manager commands work only from `manager_chat_ids` |
| A manager wants to know the FLOKTRON version | `/version` | only from `manager_chat_ids`; a newer version is also told to them once by itself (docs/UPDATES.md) |
| Someone wants the company's backup | `/backup` | only from `manager_chat_ids`; the archive is made on the computer and never sent through Telegram (docs/MOVE.md) |
| Harmful text in answers | a formula or link trap in Excel | every saved text is plain text; length limit; flood guard; old buttons ignored |
| Third-party bot builders | your leads on someone else's server | your own code, your own computer |
| Open server port | attack from outside | none: the bot fetches messages itself (long polling) |
| Bot chats are not end-to-end encrypted | as in normal Telegram cloud chats | send only what is needed: the task, not the letter; the details stay on your computer |

### Protect your own Telegram account (5 minutes, once)
1. Telegram → Settings → **Privacy and Security → Two-Step Verification** → set a cloud password (not used anywhere
   else) and a recovery e-mail. Without it, whoever gets one SMS code gets your account and all your bots.
2. Same screen → **Passkeys** (if offered) — sign-in with Face ID / fingerprint instead of an SMS code.
3. Settings → **Devices** (Active sessions): end every session you do not recognise; set «Automatically terminate old
   sessions» to 1 month or less.
4. Settings → Privacy → **Phone number** → «Who can see»: My contacts or Nobody.
5. Never type a login code anywhere except the Telegram app — Telegram itself never asks for it in a chat.

### If the bot is taken over (or the token may have leaked)
Signs: messages you did not send, the bot answers strangely, «Conflict: terminated by other getUpdates request» in
`data/bot.log` (someone else runs your bot), or the token was in a chat, a file, a screenshot.
1. **Stop the old key — 1 minute.** Telegram → @BotFather (blue check mark) → `/mybots` → your bot → API Token →
   **Revoke current token**. The old token stops working at once, for everyone.
2. **Put the new one in — one command:** `python3 scripts/bot/telegram_bot.py --set-token` (Mac: double-click
   `scripts/install/telegram/6_new_token.command`, it also restarts the bot). It checks the new token with Telegram
   and replaces the old one in the system store; nothing is shown or written to a file.
3. **Restart the bot** (`3_bot_start.command`, or your scheduler) and send it `/version` — it must answer you.
4. **Check who is in the team:** `manager_chat_ids`, `team_chat_ids`, `data/worktime_people.json`; remove anyone you
   do not know (`/remove <chat id>`). Make new invite links if old ones went around.
5. **Your account:** Two-Step Verification on, end unknown sessions (above). If your Telegram account itself was taken,
   first get it back (Telegram → «Forgot password» / support), then steps 1–4.
6. **Look at what could have been seen:** messages in the bot's chats stay in Telegram's cloud; tasks hide contact and
   payment details (`mask_personal`). If personal data of others may have been seen, the GDPR asks you to assess it
   and, where there is a risk to people, tell the authority within 72 hours.

People can type `/privacy` (what you keep) and `/forget` (personal fields are blanked; the row stays as "Deleted" for counting).

## Channel watch — what can and cannot be read
- **Public channels:** yes, through their public page `t.me/s/<channel>` — no Telegram account, phone or API key.
- **Private channels and groups:** no. Reading them would need a personal account logged in by a program — risk of a ban and of collecting other people's data. FLOKTRON does not do it.
- Choose official sources (media, authorities, municipalities, trade bodies). Anonymous "news" channels can carry propaganda or fakes; matches are data to check, never facts (see the news check in `prompts/31_news_check.md`).

## macOS and iCloud — read before autostart
macOS does not let background services (launchd) read folders in **iCloud Drive** or **Documents**: the bot would fail with `Operation not permitted`. Two ways:
- **FLOKTRON folder in iCloud/Documents:** `4_autostart_on.command` adds the bot to **Login Items** through Terminal (Terminal already has access). A Terminal window stays open — minimise it.
- **FLOKTRON folder elsewhere** (e.g. `~/FLOKTRON`) or Full Disk Access for Python (see `INSTALL.md`): the normal scheduler works.

## Funnels — how to use the source labels
Share links like `t.me/<your_bot>?start=<label>` — website, e-mail signature, QR on the product, social profiles. The label is saved with each lead, so you see which channel brings customers. `/funnel` shows at which question people stop.
