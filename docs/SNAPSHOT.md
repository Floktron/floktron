# Company snapshot — the state of your company on one date, in one file

A partner asks "where are you now?", an investor wants a one-pager before a call, the tax office asks for a summary.
Each time someone gathers the same facts again by hand. FLOKTRON builds them in one command:

- a **PDF** to read — branded with your colours, in English, Latvian or Russian;
- a **JSON** file for machines — the same rows, each with its **status** and **source**, plus the SHA-256 of the PDF,
  so anyone can check that the two files belong to one snapshot.

**You decide what goes out.** Pick a profile, then add or remove whole sections. What is marked *secret* never leaves.

Try it on the fictional company first (writes into `/tmp/snapshot`, touches nothing of yours):

```
python3 scripts/snapshot.py --test --all --out /tmp/snapshot
```

## Profiles

| Profile | For whom | What is in it |
|---|---|---|
| `partner` | a partner or investor, **after an NDA** | company, people, product and IP, stock / orders / purchases, invoices, finance, contracts, bank. Valuation only with `--plus valuation` |
| `no_bank` | the same, when bank details should stay home | as `partner`, without bank account and balances |
| `tax` | the tax office | company, people, operations, invoices, finance, contracts, bank — **only PUBLIC and DEAL figures**: no estimates, no plans |
| `public` | anyone | company, people, product — only PUBLIC facts marked `public` |

Add or remove sections: `--plus valuation`, `--minus bank,contracts`.
Sections: `company, people, product_ip, operations, invoices, finance, contracts, bank, valuation`.

## Every figure has a status

| Status | Means |
|---|---|
| PUBLIC | from an open source — a register, an annual report, your website |
| DEAL | a signed document or a completed transaction — a contract, an invoice, a bank statement |
| ESTIMATE | your own calculation |
| SCENARIO | a plan, not a fact |

A fact with an unknown status is treated as ESTIMATE — never shown as a fact.

## Your facts — `data/snapshot/facts.json`

Your AI assistant fills it with you (`prompts/51_snapshot.md`): public facts from the business register, the rest only
from you or your own files. One record per fact:

```json
{"company": {"name": "Example SIA", "reg_no": "40000000000", "vat_no": "LV40000000000", "address": "…"},
 "facts": [
  {"section": "finance", "id": "turnover_2025", "label": {"en": "Turnover 2025", "lv": "Apgrozījums 2025. g."},
   "value": "18 400,00 EUR", "status": "PUBLIC", "source": "annual report 2025", "as_of": "2026-05-31",
   "sensitivity": "public"}
 ]}
```

`sensitivity` decides who may see it:

| sensitivity | Goes into |
|---|---|
| `public` | every profile |
| `nda` | `partner`, `no_bank`, `tax` |
| `bank` | `partner`, `tax` (never `no_bank`, never `public`) |
| `valuation` | only when you add `--plus valuation` |
| `internal` | nowhere — notes for yourself |
| `secret` | **nowhere, ever** — and an unknown value counts as secret |

From the base (`data/floktron_base.xlsx`) the snapshot adds **counts and totals only**: stock lines, orders by status,
open purchases, rental items out, supplier invoices and what is still open. Names of clients and sites are never read.

## The lock

Not a switch. Before anything is written, the whole snapshot is checked for locked words — built in: passwords, keys,
tokens, PIN codes, recipes, formulations. Add your own in `config.yaml`:

```yaml
snapshot:
  facts: data/snapshot/facts.json
  out: data/snapshot/out
  locked_words: ["our secret ingredient", "prototype X"]
```

One hit stops the run, says which word was found, and **nothing is written**.

## For the tax office

The snapshot is **not a tax return**. Tax e-services take returns only in their own forms. The PDF can be attached to a
free-form application — in Latvia, an *Iesniegums* in the VID EDS. XML drafts of specific tax forms may come later; a
return is always checked and filed by you or your accountant.

## Rules

- Nothing is sent. You decide where each file goes.
- Read only: the facts file and the base are never changed.
- Make one snapshot per recipient and date; the JSON keeps only the number of rows left out, not what they were.
- PDF needs `pip install reportlab`; without it the JSON is written and the script says so.
