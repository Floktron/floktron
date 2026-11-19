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
4. **Token — you, never in chat.** BotFather gives a token (the key to your bot). Mac: double-click `scripts/install/telegram/1_token.command` and paste it — it goes straight into the Keychain. Windows/Linux: environment variable `FLOKTRON_TG_TOKEN`. Do not paste the token into any chat, file, e-mail or screenshot.
5. **Check:** `2_check.command` (or `python3 scripts/bot/telegram_bot.py --check`) → `OK — bot @…`.
6. **You become the manager.** Start the bot, open it in Telegram, send `/id`, put the number into `telegram.manager_chat_ids`, restart the bot.
7. **Test every branch** together with the assistant: each finished dialog must arrive to you and appear in `floktron_leads.xlsx`.
8. **Autostart:** `4_autostart_on.command` (Mac) — see "macOS and iCloud" below.
9. **Channels:** forward the bot any post from a public channel → it is added to the watch list (`/channels` shows the list). Times: `telegram.watch_times`, e.g. `["07:05", "18:40"]`.

## Security
| Risk | What happens | Protection in FLOKTRON |
|---|---|---|
| Token leaks | whoever has it controls the bot and reads what people send | Keychain / environment variable only; never in files, code or chat. Leaked? BotFather → `/revoke` → new token |
| Your Telegram account is taken over | BotFather hands over all your bots | turn on **Two-Step Verification** (cloud password), passkey, login e-mail |
| Fake BotFather | look-alike names ask for the token or money | only @BotFather with the blue check mark |
| Bot added to strange groups | spam, data collection | works only in private chats; `/setjoingroups` → Disable |
| Someone pretends to be the manager | wants to see leads | manager commands work only from `manager_chat_ids` |
| Harmful text in answers | a formula or link trap in Excel | every saved text is plain text; length limit; flood guard; old buttons ignored |
| Third-party bot builders | your leads on someone else's server | your own code, your own computer |
| Open server port | attack from outside | none: the bot fetches messages itself (long polling) |
| Bot chats are not end-to-end encrypted | as in normal Telegram cloud chats | ask only what you need: name, phone, e-mail |

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
