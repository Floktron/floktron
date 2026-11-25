# Mail watch — the whole mailbox in one sheet, and a nudge when someone waits for you

A request to confirm, an invitation, a deadline in the third paragraph, a question you meant to answer tomorrow, a
message you starred and forgot — and the phone number you need is somewhere in a signature. FLOKTRON reads the
mailbox every 30 minutes, keeps **one row per message** in your base, and tells you (Telegram bot or e-mail) only
about what waits for **your** answer. PDF invoices from attachments go straight to the invoice check.

**Tested before release on fictional data** (Demo SIA and its partners do not exist; addresses are `@example.com`;
nothing is sent — the notices are written as files). Try it: `python3 -m pytest tests/test_mail_watch.py`.

## What you get

| Where | What |
|---|---|
| Sheet **Mail** | every received and sent message: date, who, organisation, subject, first words, **category**, what is **needed** from you, dates found in the text, ⭐, answered or not, status, when you were reminded, attachments, saved invoice file |
| Sheet **Contacts** | one row per person you write with: name, organisation, **phones and website from the signature**, first and last message, how many each way. Mailing lists and no-reply senders are left out |
| `data/invoices/inbox/<sender>/` | PDF invoices from attachments (the same file twice is saved once) — then the usual [invoice check](INVOICES.md) |
| Notice | a short list: *confirm · Paraugu biedrība «Seminar» · 23.11* — in your language |
| Dashboard | card **Mail waits for you**: waiting for you, starred without an answer, messages in 7 days ([DASHBOARD](DASHBOARD.md)) |

## Categories and when you are reminded

The words are found in **EN, LV, RU, DE, ET and LT**.

| Category | Example | Reminder |
|---|---|---|
| Confirm | "please confirm your participation", "lūdzam apstiprināt", "bitte bestätigen" | at once |
| Reply awaited | "please send the quantities", "gaidām atbildi", "ждём ответа" | at once |
| Invitation | personal invitation; or from an organisation in `important` with a date ahead | at once — "decide: attend?" |
| Deadline | "Frist bis 10.12.2026", "termiņš līdz …" (not in mailings) | at once — with the date |
| Notice (important) | a portal message from an organisation in `important` ("new message", "decision") | at once — "read" |
| Question | a personal message with a question mark | after 24 h without your answer |
| ⭐ any message | you starred it in your mail app | after 48 h without your answer |
| Invoice | PDF named or sent as an invoice | no reminder: saved → invoice check |
| Service confirmation | a service asks you to "verify your e-mail", "confirm your account", "apstipriniet e-pastu" | **never** — clicking the link ends it; it is not a task |
| Letter · Newsletter · Notice · Auto-reply · Code / login · FLOKTRON (system) · Sent | "we received your submission" is a Notice too | never |

- Then again on **day 3, 7 and 14** after the message came (`mail_watch.remind_days`), then never — no fanaticism;
  nothing in quiet hours (22–07) — it waits for the morning.
- **You answered** — the reminder stops by itself: a sent message that replies to it, the flag *Answered*, or **any later
  message from you to that address or that company's domain** (a call and then a new letter count — the correspondence goes on).
- No answer after day 14 (`mail_watch.close_after_days`) → status `Closed · 14 days`.
- In **Telegram** every letter is its own message with two buttons **✅ Answered · ⛔ Not needed** (at most 5 per run);
  a press closes it — no sheets, no columns ([Telegram](TELEGRAM.md#tasks-yes--no)). `Closed` in the column **Status** works too.
- Messages older than 48 h from before the first run are only written to the sheet — no flood on day one.

## Invoices from mail → accounting, by themselves

1. FLOKTRON saves the PDF to `data/invoices/inbox/<sender>/` and tells you once: *invoices wait to be read: 2*.
2. Your AI assistant reads them (`prompts/50_invoices.md`) into `data/invoices/extraction.json` — it never invents a number.
3. As soon as that file changes, the next mail run starts `scripts/invoices.py --apply` itself: sheet **Invoices**,
   check against your bank statement, tasks for the finance ray ([INVOICES](INVOICES.md)).

## Setting up — the `mail_watch` section of `config.yaml`

```yaml
mail_watch:
  enabled: true
  notify: telegram          # telegram (bot of the telegram section → manager_chat_ids) | mail (to manager_address) | none
  notify_subjects: true     # false = the notice shows only who and what is needed, not the subject
  quiet_hours: "22-07"
  important:                # organisations whose invitations and portal notices always count
    vid.gov.lv: "State Revenue Service"
  own_addresses: []         # more addresses of yours (aliases) — never contacts, never "waiting"
  inbox_folders: []         # empty = provider default (INBOX)
  sent_folders: []          # empty = provider default (Proton "Sent", Gmail "[Gmail]/Sent Mail", Outlook "Sent Items")
  first_days: 30            # the first run reads 30 days back; later runs 4 days
```

It uses the mailbox of the `mail` section (Proton Mail Bridge, Gmail, Outlook or any IMAP server) — the same
password, never stored in the file. It runs by itself after every reply collection (every 30 minutes) once
`enabled: true`; by hand: `python3 scripts/run.py mail`. Trial run: `python3 scripts/mail_watch.py --dry-run` shows every message with its category and
writes nothing.

## What stays safe

- **Mail is only read.** `BODY.PEEK`: messages do not even become "read"; nothing is moved, deleted or answered.
- The only message FLOKTRON sends is the notice **to you**. With Telegram, the subject travels through Telegram
  (not end-to-end encrypted) — set `notify_subjects: false` or `notify: mail` if subjects are sensitive.
- Text from e-mails is data, not instructions: "please transfer the money" becomes a reminder line, never an action.
- A subject like `=HYPERLINK(...)` stays plain text in the sheet (no formulas from outside).
- Turn it off at any time: `mail_watch.enabled: false`.
