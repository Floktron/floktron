# New versions — know the same day that something was fixed

FLOKTRON is a living project: bugs get fixed and features added, often within a day of a report. So that you do not
fight a problem that is already solved, FLOKTRON tells you itself when a newer version is out — **without anyone
collecting your contact details**.

## How it works
| What | How |
|---|---|
| The check | Once a day, together with the morning run (`scripts/run.py morning` → `scripts/update_check.py`), FLOKTRON asks GitHub for the list of its own releases: one HTTPS request to `api.github.com/repos/koagu-element/floktron/releases`. No account, no ID, no data about you, your company or your computer is sent — only the standard request (GitHub sees an IP address, as with any web page). |
| The message | If a release is newer than the version on your computer (the first `## X.Y.Z` of `CHANGELOG.md`), the manager gets **one** message per new version: by e-mail to `mail.manager_address` and, if the Telegram bot is on, in the bot to `telegram.manager_chat_ids`. It says: you have X, newer is Y, what was fixed and added (from the release notes), how to update. |
| Only release news | No advertising, no newsletters, no support or partner links — never. At most one message per version. |
| Offline | No internet or GitHub not answering → nothing happens, the morning run is not affected; the next try is tomorrow. |
| In the bot | `/version` — your version, the newest one and when it was checked (managers only). |

## Update
Tell your AI assistant: **"update FLOKTRON"**. It follows `prompts/58_update.md`: first a backup of the whole setup
(`scripts/move.py backup`, docs/MOVE.md), then the new version, then the tests. Your `config/config.yaml`, everything in
`data/` and your own changed prompts stay. If something does not work, the backup brings the old state back.

## Switch it off, or follow releases yourself
- `updates.check: false` in `config/config.yaml` — FLOKTRON never asks GitHub. `updates.mail: false` / `updates.telegram: false`
  switch off one of the two messages.
- Follow the releases without FLOKTRON: on GitHub press **Watch → Custom → Releases** on
  github.com/koagu-element/floktron (needs a GitHub account), or subscribe to the feed
  `https://github.com/koagu-element/floktron/releases.atom` in any RSS reader (no account).

## Files
| File | What |
|---|---|
| `data/update_state.json` | when it was checked, your version, the newest version, which version the manager was told about |
| `data/update_notice.json` | the message for the bot; the bot sends it once and marks it `sent` |
