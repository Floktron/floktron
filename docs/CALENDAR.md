# Calendar — your day in the morning message, due dates in one tap

Optional. Works with any calendar that speaks `.ics` — Proton, Google, Outlook / Microsoft 365, Apple iCloud,
Nextcloud, Fastmail and others. Nothing to install, no app permissions, no sign-in to your calendar account.

| Part | What you get | How |
|---|---|---|
| **Read** | The morning message shows *"Today in your calendar: 10:00–12:00 Meeting (Office) …"* above the tasks, so tasks are planned around your day | FLOKTRON reads your calendar's private **read-only** link (`scripts/calendar_read.py`) |
| **Add** | Every morning message carries an `.ics` file with the due dates of its tasks — one tap adds them to your calendar. The assistant can also make an `.ics` for a meeting or a schedule (`scripts/ics.py`) | a standard calendar file, opened by every calendar app |

**FLOKTRON only reads.** It never creates, moves or deletes events in your calendar. Adding happens only when YOU tap
the attached file. Two-way sync (FLOKTRON writing into your calendar) is not part of FLOKTRON on purpose.

## Step 1 — find the private link of your calendar
| Calendar | Where | Notes |
|---|---|---|
| **Google** | Computer → calendar.google.com → ⚙ Settings → under *Settings for my calendars* click your calendar → *Integrate calendar* → **Secret address in iCal format** → copy | Not the "public address". Work/school accounts: the admin may hide it — ask them. Leaked? Press *Reset* |
| **Outlook / Microsoft 365** | outlook.com or outlook.office.com → ⚙ Settings → Calendar → **Shared calendars** → *Publish a calendar* → choose the calendar and *Can view all details* (or *Can view when I'm busy*) → Publish → copy the **ICS** link | Company accounts: publishing may be switched off by the admin. *Reset links* makes a new one |
| **Proton** | calendar.proton.me → Settings → All settings → Calendars → your calendar → *Share with anyone* → **Create link** → *Full view* (or *Limited view* = busy only) → Copy link | Needs a paid Proton plan. Changes may take a few hours to appear in the link |
| **Apple iCloud** | Mac Calendar app → point at the calendar → Share → **Public Calendar** → copy the link (`webcal://…`) | The link always shows full details to anyone who has it — use a separate calendar for work if you prefer. `webcal://` is fine, FLOKTRON reads it as `https://` |
| **Other** (Nextcloud, Fastmail, Zoho…) | look for "subscribe", "iCal", "ICS" or "share link" in the calendar settings | the link must open a file that starts with `BEGIN:VCALENDAR` |

**The link is a key to your calendar — treat it like a password.** Never paste it into a chat, an e-mail or a file.
Want titles to stay private? Choose the busy-only option of your calendar (Outlook, Proton), or set
`calendar.busy_only: true` — then FLOKTRON shows only *"10:00–11:00 busy"*.

## Step 2 — give the link to FLOKTRON (you, not the assistant)
- **Mac:** double-click `scripts/install/calendar_link.command`, paste the link, Enter, once more. It goes straight into the
  Keychain (item `FLOKTRON_CAL`) and FLOKTRON checks it: `OK — calendar read: N events…`.
- **Windows / Linux:** environment variable `FLOKTRON_CAL_URL` (same way as the mail password, `docs/GMAIL_TEST.md` step 4).

## Step 3 — switch it on
```yaml
calendar:
  enabled: true
  timezone: "Europe/Riga"     # your time zone
  rays: ["L1"]                # whose morning message shows the calendar — usually the person who owns it
  busy_only: false            # true → only "busy", no titles or places
  attach_due: true            # .ics with the due dates in every morning message
```
Check: `python3 scripts/calendar_read.py --check`, then `python3 scripts/calendar_read.py --day <tomorrow>`, then
`python3 scripts/send_morning.py --dry` — the letter in `data/letters/<today>/` shows the calendar and has the `.ics` next to it.

## If something goes wrong
- The calendar does not answer → the morning messages still go out, only without the calendar; the reason is in
  `data/run.log` (`calendar: not read — …`).
- *"not a calendar (.ics)"* → you copied the web page link, not the iCal/ICS link.
- Events missing → only the calendar whose link you gave is read; repeating events with unusual rules may not all be
  shown — tell us (`docs/FEEDBACK.md`).
- Remove: delete the Keychain item `FLOKTRON_CAL` (or the variable) and set `calendar.enabled: false`; reset the link in
  your calendar so the old one stops working.
