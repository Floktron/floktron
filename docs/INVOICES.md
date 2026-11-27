# Invoices → accounting — every supplier document read, checked against the bank, handed over

Supplier documents come in every language and shape: a Latvian *rēķins*, a German *Rechnung*, a Spanish *factura
proforma*, an Estonian *ettemaksuarve*, a scan from a phone, the same invoice forwarded twice, a delivery note that is
not an invoice at all. FLOKTRON reads them, checks each one against your bank statement and gives the finance ray
(by default L7) short tasks: what to pay, what to check, which final invoice to ask for, what to pass to the accountant.

**Tested before release on a fictional set** (no real company inside, every page marked *TEST · FICTIONAL*):
10 documents in 7 languages (LV, EN, DE, ES, LT, ET, RU) plus a Czech scan without a text layer, and a bank statement
as PDF and as CSV — `tests/fixtures/invoices/`. Try it yourself in one line (dry run, writes nothing):

```
python3 scripts/invoices.py --folder tests/fixtures/invoices/docs --extraction tests/fixtures/invoices/extraction.json \
  --statements tests/fixtures/invoices/statements_csv --today 2026-11-22 --test
```

## Two steps

| Step | Who | What |
|---|---|---|
| 1. Read | your AI assistant (`prompts/50_invoices.md`) | opens every new document (PDF, photo, scan), writes one record per document into `data/invoices/extraction.json`: supplier, VAT number, type, number, dates, net / VAT / total, how it is paid, words that identify the supplier in a bank payment. Never invents a figure: what it cannot read stays empty and is flagged |
| 2. Check and hand over | `scripts/invoices.py` (no AI, no network) | skips duplicates, finds every payment in your bank statement, sets a status, writes the sheet **Invoices** and tasks for the finance ray; the dashboard shows the card *Invoices → accounting* |

## What it catches

| Situation | Status | Task |
|---|---|---|
| Paid, payment found (invoice number or supplier name + amount + date) | `Paid <date>` | — (goes into the hand-over task) |
| The same document forwarded again (`FW_ …`, `(1).pdf`), a scan and a photo of the same invoice, or already in the base (number compared without spaces, dashes and case: `PR-2026/118` = `pr 2026 118`) | not added | — |
| A record with an empty total, number or date, or an unknown type (the assistant could not read it) | not booked, listed as *needs a look* until the record is corrected | — (tell the person) |
| Delivery note / *Lieferschein* / *pavadzīme* without amounts | `Not a payment document`, linked to its invoice | — |
| Proforma paid, final invoice set off against it | proforma `Closed by invoice …`, invoice `Paid by advance` | — |
| Proforma, order confirmation or advance invoice paid, no final invoice | `Paid · no final invoice` | ask the supplier for the final invoice |
| Not paid, due date ahead | `To pay by <date>` | pay by the due date |
| Not found in the statement | `Not found in statement` | check the payment |
| Same amount paid to someone else (e.g. a supermarket card payment) | **not** taken as the payment — `(similar payment)` | check the payment, with the similar one named |
| Same amount in another currency; a short number like `12` that also appears in a date; only a legal form (`SIA`, `GmbH`) in common | **not** taken as the payment | check the payment |
| VAT of another country charged / reverse charge | comment on the row | one task for the accountant (ESTIMATE — to confirm) |
| Several orders paid with one card payment | `one payment for N documents` | — |

## Folders (all inside your own `data/`, never in git)

```
data/invoices/inbox/<supplier>/<file>.pdf     ← documents, one folder per supplier (any names, any language)
data/invoices/statements/<file>.csv|.pdf      ← bank statements you download yourself
data/invoices/extraction.json                 ← what the assistant read (step 1)
```

**Bank statements.** Download them yourself from the internet bank — FLOKTRON never logs in to a bank.
CSV from any bank works (columns *date, counterparty, details, amount*, optional *currency*, in EN / LV / LT / ET / DE
names; incoming money is skipped — by the D/K column, or by the sign when outgoing payments are negative). The same
payment in two overlapping statements (October and October–November) counts once. PDF statements in the Swedbank layout work too if `pip install pypdf` is done; otherwise the script says so
and asks for CSV. Only statements of **your** account are read (`invoices.our_iban` in `config.yaml`); a private account
statement in the same folder is skipped.

## config.yaml

```yaml
invoices:
  our_iban: "LV00BANK0000000000000"   # your company account in the statements
  our_vat: "LV00000000000"            # your VAT number; its country is "home" for the VAT check
  ray: L7                             # who gets the tasks (finance)
```

## Rules

- **Nothing is paid, sent or deleted.** Tasks go into the morning message of the finance ray like any other task.
- **Dry run first**: `python3 scripts/invoices.py` shows everything and writes nothing; `--apply` writes.
- **Raw materials stay codes.** The base keeps supplier, number, dates and amounts — no product names, recipes or quantities.
- Every VAT remark is an ESTIMATE for your accountant to confirm, never advice.
- Supplier names and numbers come from outside: they are written as plain text, never as spreadsheet formulas.
- Test with fictional data first (`--test`: rows and tasks are marked TEST, the dashboard shows them with a *test* tag).
