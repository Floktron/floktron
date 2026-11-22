# Documents — invoices, advance invoices, acts and offers in your own brand

Most small companies write invoices in an online form or a word processor: a different look every time, numbers
kept by hand, nothing in the books until someone types it in. FLOKTRON makes the four documents a small company
sends most often, on one branded sheet, with the number and the register row done for you:

| Type | LV name | What is on it |
|---|---|---|
| `invoice` | Rēķins | all fields of an EU VAT invoice: seller and buyer with reg. and VAT numbers, number, date, delivery date, lines, net / VAT / total, amount in words, bank details, due date, "valid without signature" |
| `advance` | Avansa rēķins | the same, for a prepayment; says that a final invoice follows delivery |
| `act` | Pieņemšanas-nodošanas akts | goods or services handed over and accepted, two signature fields |
| `offer` | Komercpiedāvājums | lines and prices, valid-until date, notes, who offers |

Languages: `lv`, `en` or `lv+en` (both on one sheet, for buyers abroad). Colours come from the `colors` section of
`config.yaml` (the same as your messages), plus your logo.

**Tested before release on fictional data** (Demo SIA and its buyers do not exist; every page carries
*TEST · FICTIONAL*). Try it in one line — writes one PDF, touches nothing else:

```
python3 scripts/documents.py --seller tests/fixtures/documents/seller_demo.json \
  --doc tests/fixtures/documents/invoice_lv.json --out data/documents/test
```

## How it works

| Step | Who | What |
|---|---|---|
| 1. Ask | you, in words: *"invoice to Paraugs Būve, 4 chairs, due in 10 days"* | |
| 2. Fill | your AI assistant (`prompts/52_documents.md`) | writes `data/documents/in/<date>_<type>_<buyer>.json`: buyer from your own records or the public business register, lines and prices **only from your price list or from you**. Never invents a price, a VAT number or a bank account |
| 3. Make | `scripts/documents.py` (no AI, no network) | draws the PDF, takes the next number, adds the amount in words. Dry run first: nothing is recorded |
| 4. Record | you say *"yes"* → the same line with `--apply` | the number is fixed and one row goes to the sheet **Issued** in your base |
| 5. Send | **you** | FLOKTRON never sends a document to a customer by itself |

Payments: the invoices you issued can be checked against the bank statement the same way as supplier invoices
([INVOICES](INVOICES.md)).

## Setting up — the `documents` section of `config.yaml`

```yaml
documents:                 # optional: branded invoices, acts, offers (docs/DOCUMENTS.md)
  legal_name: ""           # as in the register, e.g. SIA "Example"; empty = company.name
  reg_no: ""
  vat_no: ""               # empty if you are not VAT registered (then use "vat_rate": 0 and say why in "notes")
  address: ""
  email: ""                # the public company address
  phone: ""
  web: ""
  bank: ""
  swift: ""
  iban: ""
  prefix: "INV"            # numbers look like INV-R-2026-001 (R invoice, AR advance, A act, P offer)
  logo: ""                 # PNG with a transparent background, next to config.yaml or a full path
```

Needs `reportlab` (`pip install reportlab`) and a font with Latvian letters — Liberation Sans, Arial or DejaVu Sans
(on macOS Arial is already there).

## The document file

```json
{"type": "invoice", "lang": "lv", "date": "2026-11-23", "due_days": 10, "supply_date": "2026-11-23",
 "buyer": {"name": "SIA \"Buyer\"", "reg_no": "…", "vat_no": "…", "address": "…", "email": "…"},
 "basis": "Contract No. 1",
 "lines": [{"desc": "Product", "note": "small grey line under it", "qty": 4, "unit": "pcs", "price": 89.90}],
 "vat_rate": 21, "notes": "optional"}
```

`act` may add `"place"`; `offer` adds `"valid_until"`, `"intro"`, `"signed_by"`; `"show_prices": false` hides prices
on an act; `"number"` fixes a number by hand (it is refused if it is already in the register); `"test": true`
prints the *TEST · FICTIONAL* mark.

## Rules that keep it safe

- **Numbers are never reused.** A wrong document gets a new number and a note in the base — the old row stays.
- **Dry run first**; `--apply` only after the person has seen the PDF.
- **No invented figures.** Prices, VAT numbers and bank accounts come from the person, the price list or a public
  register — never from memory.
- **EU buyers with a VAT number:** `"vat_rate": 0` and a note (e.g. *Intra-Community supply of goods, Directive
  2006/112/EC Art. 138*) — check the buyer's number in VIES first; when in doubt, ask your accountant.
- Your data stays on your computer: documents are in `data/documents/`, never in git.
