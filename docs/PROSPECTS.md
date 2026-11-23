# New customers that look like your best ones — with a reason to write now

`scripts/prospects.py` (no AI, version 0.23.0). Only public open data, only company data. Nothing is sent.

## The idea
A good first letter needs two things: the right company and the right moment.
- **The right company** looks like your best customers: same legal form, same area, about as young.
  You give their reg. numbers (`prospects.best_customers`); FLOKTRON reads their facts from the register and builds the portrait.
- **The right moment** is a fresh contract: the company has just won and signed public works of the kind you serve.
  In a few weeks it will need what you sell.

## Where the facts come from
| Source | What is used | Status |
|---|---|---|
| Public procurement results of Latvia (EIS e-iepirkumi, data.gov.lv, CSV per year, updated daily) | winner and reg. no., buyer, subject, sum, signing date, works until, ended or not | PUBLIC |
| Register of Enterprises (register.csv, data.gov.lv) | legal form, registration date, town, terminated | PUBLIC |
| Kind of work | words in the contract subject (`prospects.signals`) — the file has no CPV code | ESTIMATE |
| Score, priority, "looks like" | the rules below | ESTIMATE |

No people, no personal contacts: the procurement file and the register hold company data only.

## What gets in
A contract counts when: the winner is a Latvian company (11-digit reg. no.), the contract is signed within
`days` (180), the sum is at least `min_eur` (10 000 EUR) in EUR, it was not ended, and the subject has words of one
of your signals and no exclude word (design, supervision, supply of goods, rent...). Companies that are already in
the sheet **Companies**, marked *Do not contact* there, terminated in the register, or are one of your best customers
are skipped.

## Score (ESTIMATE)
| Points | For |
|---|---|
| signal weight (finishing 3, building 2, networks 1 in the example) | kind of work |
| 3 / 2 / 1 | signed within 30 / 90 / 180 days |
| +1 | the works are still under way |
| +2 / +1 | contract up to `small_max_eur` / up to 5 × that (the size of a small contractor) |
| −2 | wins over `big_total_eur` in 12 months (a big general contractor) |
| +1 | two or more wins in 12 months |
| +1 each | same legal form, same area, not older than your oldest best customer + 3 years |

Priority 1 from 9 points, 2 from 6, else 3. At most `max_new` (40) new rows per run.

## Sheet "Prospects" (radar base)
ID, Found, Company, Reg. no., Score, Priority, **Why now** (e.g. "signed 10.11.2026 · 84 500 EUR · remont; works under way"),
Contract subject, Buyer, Sum EUR, Signed, Works until, Wins 12 months, Form, Town, Registered, Looks like,
Source (link to the procurement), Data status, **Decision**, Status, Draft, Comment.

**Decision**
- `Add` → the company goes to the sheet **Companies** (goal Client, work status New) and a draft first letter is
  written to `data/prospects/drafts/<ID>_<company>.txt` from your template (`prospects.letter`, placeholders
  `{company}`, `{works}`, `{pitch}`, `{product_line}`, `{signature}`).
- `No` → never suggested again.

The draft is **not sent**. You find the company's GENERAL address on its own website, check the text and send it
yourself — one personal business letter to one company, with a line to opt out. That is the line between a
business letter and spam; FLOKTRON does not cross it.

## Notice
When a run finds new prospects: one short Telegram message or e-mail (like mail watch, `prospects.notify`) with
the number and the top 3. No new prospects — no message.

## Settings (`config.yaml`)
```yaml
prospects:
  enabled: false
  notify: telegram          # telegram | mail | none
  best_customers: []        # reg. numbers of your best customers, e.g. ["40000000001"]
  home_area: []             # town words; empty = the towns of your best customers
  days: 180
  min_eur: 10000
  pitch: ""                 # two sentences for the draft letter
  letter: ""                # your own template file (optional)
  signals: [...]            # see config.example.yaml; stems in the language of the file; first match wins, `unless` steps aside
```

## Run
```
python3 scripts/prospects.py --dry-run          # look first, write nothing
python3 scripts/run.py prospects                # the daily run (scheduler: once a day, e.g. 07:20)
python3 scripts/prospects.py --eis-csv results.csv --register-csv register.csv   # files you downloaded yourself
```
Network: only data.gov.lv, through `scripts/registry_lv.py` (see `docs/TRANSPARENCY.md`).
Tests: `python3 -m pytest tests/test_prospects.py` — fictional companies (TEST · FICTIONAL), files built at test time.

## Limits
- Only Latvia so far (the EIS and UR open data). Other countries: the same columns from your own CSV via `--eis-csv`.
- The kind of work comes from words, not from a CPV code — read the subject before you write.
- Public contracts only; private building sites are not in any open file.
