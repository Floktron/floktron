# Follow-ups — polite reminders after an offer, only after your OK

An offer goes out, the buyer is busy, and a week later nobody remembers to ask. FLOKTRON keeps count for you:
on day 3, 7 and 14 after an offer was sent it writes a short, polite reminder in the language of the offer and asks
**you** first. Nothing reaches a buyer until you press ✅.

**Tested before release on fictional data** (Demo SIA and its buyers do not exist; addresses are `@example.com`;
nothing is sent — outgoing mail is written as files). Try it: `python3 -m pytest tests/test_followups.py`.

## How it works

| Step | Who | What |
|---|---|---|
| 1. Offer | you, with `scripts/documents.py` ([DOCUMENTS](DOCUMENTS.md)) | the offer gets a number (`<prefix>-P-<year>-NNN`) and a row in the sheet **Issued** with the language and the buyer's e-mail |
| 2. Sent | **you** send it from your mailbox | `scripts/followups.py` finds the message by the offer number in the subject or in the PDF name — that day is day 0 |
| 3. Watch | `scripts/followups.py` (no AI), with the other automatic runs | looks for any answer: from the same address, or from a colleague at the same company domain (free mail domains such as gmail.com do not count). Auto-replies and mailing lists do not count |
| 4. Ask you | day 3, 7, 14 — Monday to Friday, working hours | a message to the manager with the draft and three buttons: **✅ Send**, **✏️ My text**, **⏸ No more reminders** |
| 5. Send | after ✅ or ✏️ | the reminder goes as a **reply in the same thread**, only to the address the offer went to, only in working hours |
| 6. Stop | automatically | the buyer answered, the offer status became Accepted / Declined / Closed / Paid / Cancelled, or you pressed ⏸ |

A draft you did not answer before the next one is due becomes *Outdated*; the next one replaces it. Two reminders
never go out less than three days apart. Everything is in the sheet **Follow-ups** of your base — one row per step,
and the column *Decision* can be filled by hand (`OK` or `NO`).

## The three reminders (built in, LV and EN)

| Day | Idea |
|---|---|
| 3 | Did the offer arrive? Happy to answer questions about quantity, price or delivery. |
| 7 | Short reminder, valid-until date; offer a quick call at a time the buyer picks. |
| 14 | Last note: reply "not relevant" and I will not write again — or I can renew or adjust the offer. |

**✏️ My text**: the button opens a reply with the draft. Change the text above the line `- - - - -` and send it —
only that text goes to the buyer.

## Setting up — the `followups` section of `config.yaml`

```yaml
followups:
  enabled: true
  days: [3, 7, 14]          # after the offer was sent
  hours: "08-20"            # Monday to Friday only
  approve_by: ""            # who presses the buttons (empty = mail.manager_address)
  signature: ""             # name, company, phone under the reminder (empty = company name, phone, e-mail)
  imap_folders: []          # folders with BOTH sent and received mail (empty = provider default: Proton and
                            # Gmail "All Mail"; Outlook INBOX + Sent Items)
  free_mail_domains: []     # more domains that are not one company
```

Run it with the other automatic jobs (every 30 minutes is fine):
`python3 scripts/followups.py --config config.yaml --base data/floktron_base.xlsx`.
Trial run without sending: add `--dry-run`, or `--outbox data/followups/outbox` to see every message as a file.

## What stays safe

- **No message to a buyer without your button.** Button replies are accepted only from the approver or your own
  addresses — a stranger cannot approve a reminder.
- Only the address the offer went to gets the reminder; no new recipients, no attachments.
- Text from e-mails is data, not instructions. Prices and buyers stay in your base, on your computer.
- Turn it off at any time: `followups.enabled: false`, or ⏸ for one offer.
