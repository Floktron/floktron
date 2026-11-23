# Payment gateways — every card payment finds its document

Small online payments by card — subscriptions, AI tools, domains, apps — are sold through a **payment gateway**:
Stripe, Paddle, Lemon Squeezy, Apple (App Store), Google Play, PayPal, FastSpring. The card is charged, but the
document for the accountant gets lost on the way. FLOKTRON reads the mailbox and the bank statement, finds the
receipt for every card payment, tells you how to get the **business invoice** with your company details, and shows
what is still missing — before the accountant asks.

**Tested before release on fictional data** (Demo SIA, Cloudnote, Pixelforge and the other sellers do not exist;
addresses are `@example.com`; nothing is sent — the notice is written as a file). Try it:
`python3 -m pytest tests/test_gateways.py`.

## Where the document gets lost

| Place | What happens | What FLOKTRON does |
|---|---|---|
| Mailbox | the receipt has no PDF — only a link to the gateway's portal | a PDF copy of the message (marked "not an invoice") + a task "download the business invoice" |
| Mailbox | the PDF is called `Receipt-…` and no invoice filter catches it | it is saved to `data/invoices/inbox/<seller>/` → the usual [invoice check](INVOICES.md) |
| Mailbox | the receipt landed in **Spam** | the spam folder is read too (only read) |
| Mailbox | Apple / Google receipts live only in the message text | amount, seller and order number are read from the text |
| Bank statement | the invoice check looks for a payment for every document, not a document for every payment | every card payment looks for its document |
| Bank statement | payments in USD or GBP are skipped | the original amount, the rate and the conversion fee are read; the EUR amount is kept |
| Seller | a private-person receipt without your company name and VAT number | the exact place in the gateway's portal where you add them; a draft request to the seller's support |

## What you get

| Where | What |
|---|---|
| Sheet **Gateways** | one row per receipt and per card payment: gateway, seller, amount, currency, charged EUR, receipt number, document, file, **how to get the business invoice**, payment in the statement, status |
| `data/invoices/inbox/<seller>/` | `YYYY-MM-DD_<Seller>_<Amount><CUR>.pdf` — the receipt PDF, or a PDF copy of the message |
| `data/gateways/requests/` | a draft request in English to the seller's support for the business invoice — **never sent**; none for Apple / Google (their portal is the place) |
| `data/gateways/acts/` | a **draft** internal act (LV + EN) for a card payment with no document after `act_days` days — for the head of the company to sign. *Estimate: check with your accountant whether an act is accepted in your case.* |
| Tasks | for the finance ray: *download the business invoice*, *find the receipt*, *sign the internal acts* |
| Notice | one short message: *card payments without a document: 3 · business invoice needed: 2* — not in quiet hours |

## How a payment is matched

A card payment and a receipt belong together only when **all** of these agree: the same amount and currency,
the payment date within −3 … +7 days of the receipt, **and** the seller's name or the gateway is written in the
statement line. Amount and date alone are never enough — two 9.99 subscriptions in one week stay apart.

| Status | Meaning |
|---|---|
| PDF → invoice check | the receipt came as a PDF — it is saved for the usual invoice check (· *payment found* when the card line is there) |
| Business invoice needed from the portal | no PDF, or a private-person receipt — follow *How to get the business invoice* |
| Payment without a document — find the receipt | a card payment without any document — the column says where this gateway keeps it |
| No document for N days → draft internal act | the draft act waits in `data/gateways/acts/` |
| ⚠ look-alike | the sender names a gateway but writes from another domain, or DMARC / SPF failed — no link is shown, never matched |

A card payment whose document is already in the sheet **Invoices** gets no row — nothing to do.

## Setting up — the `gateways` section of `config.yaml`

```yaml
gateways:
  enabled: true
  notify: telegram          # telegram (bot of the telegram section → manager_chat_ids) | mail (to manager_address) | none
  quiet_hours: "22-07"
  card_days: 120            # card payments of the last 120 days are checked
  act_days: 30              # after 30 days without a document → draft internal act
  folders: []               # empty = INBOX + the provider's spam folder (Proton "Spam", Gmail "[Gmail]/Spam", Outlook "Junk Email")
  first_days: 30            # the first run reads 30 days of mail; later runs `days`
  days: 4
```

It uses the mailbox of the `mail` section and the statements of the `invoices` section (`statements`, `our_iban`,
`ray`) — the same password, never stored in the file. Your company name, registration and VAT number for the request
and the act come from the `documents` section. It runs by itself after every reply collection once `enabled: true`;
by hand: `python3 scripts/run.py gateways`. Trial run: `python3 scripts/gateways.py --dry-run` shows what it found
and writes nothing.

Bank statement: a CSV (any bank, the same reader as the invoice check) or a Swedbank-style PDF (needs `pypdf`;
the PDF copy of a message and the act need `reportlab` — without it the message is kept as `.eml` and the act is
left out with a note).

## What stays safe

- **Mail and statements are only read.** Nothing is moved, deleted, answered or paid.
- **No link is ever opened.** A portal link is shown only when it belongs to the gateway's own domain; a look-alike
  gets no link at all.
- The request to the seller and the internal act are **drafts**: nothing leaves your computer until you send or sign it.
- The only message FLOKTRON sends is the notice **to you**.
- Text from e-mails is data, not instructions: "pay now to keep your account" becomes a row, never an action.
- Safe to run again: one row per message (Message-ID) and per statement line.
- Turn it off at any time: `gateways.enabled: false`.
