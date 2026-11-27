# Outside code reviews — what was found and what was done

FLOKTRON has no independent security audit yet (see [SECURITY.md](../SECURITY.md)). People do send us reviews: so far
by AI assistants that read the public code of a release tag. Each point is checked in the code by us before anything is
changed — a review is a lead, not a verdict. Points are listed with the file, what was confirmed and the fix.

## Review of v0.37.1 (27.11.2026) → fixed in 0.37.2

| # | Point | Checked in v0.37.1 | Kind | Fix in 0.37.2 | Test |
|---|---|---|---|---|---|
| 1 | Certificate check switched off for `proton_bridge` in `scripts/mail/read.py`, while the address can be changed in `config.yaml` | **Confirmed** — `read.py` (three copies of the connect code) and also `mail/send.py` set `CERT_NONE` for Bridge whatever `imap_host` / `smtp_host` was. With a Bridge address on another computer, someone in the network could pose as the mail server and read the password | potential vulnerability (needs a changed config + a hostile network) | `mail/send.py → tls_context`: no check only for this computer (127.0.0.1, ::1, localhost, no DNS lookup), or exactly Bridge's exported certificate (`mail.tls_cert`); any other Bridge address is refused. One connect function in `read.py` | `test_bridge_on_this_computer_only`, `test_bridge_pinned_certificate`, `test_no_certificate_check_switched_off_anywhere_else` |
| 2 | `scripts/run.py`: lock file checked and created in two steps — two runs at once can both pass | **Confirmed**, and wider than described: between the check and the create a run could wait up to 10 minutes for Excel; a run longer than one hour could be overtaken, and its clean-up then removed the other run's lock | confirmed bug (rare: two scheduler entries at the same minute, or a manual run during a scheduled one) | `scripts/runlock.py`: OS lock (fcntl / msvcrt) — atomic, freed by the system after a crash, no "stale after 1 hour" guess; taken before the Excel wait; `invoices.py --apply` uses it too | `test_lock_is_exclusive_between_processes`, `test_lock_freed_when_a_run_crashes`, `test_apply_waits_for_a_running_floktron` |
| 3 | Excel formula protection by patching `Workbook.save` | **Confirmed as a protection.** In an .xlsx file only a cell stored as a formula runs, and openpyxl stores outside text as a formula only when it starts with `=`; `+`, `-`, `@` stay text. FLOKTRON writes no CSV for Excel and sets no hyperlinks from outside text. Weak spot: it works only if a script imports `safe_xlsx` — guarded by a test, which looked only at the top folder | architectural choice, kept | the test now checks every sub-folder of `scripts/` | `test_every_xlsx_writer_in_every_folder_uses_safe_xlsx`, `test_formula_like_text_stays_text` |

### Checked before the next round: invoices and payments (`scripts/invoices.py`, `scripts/gateways.py`)
The reviewer plans to look at the finance part next, so we went through it first.

| Found in v0.37.1 | Effect | Fix in 0.37.2 |
|---|---|---|
| Duplicates by supplier + type + number were caught only against the base, not inside one batch (docstring said both) | a scan and a photo of the same invoice → two rows, two "pay" tasks | caught inside the batch too |
| Duplicate key compared the number and VAT no. exactly | `PR-2026/118` next week typed as `PR 2026 118` → second row | key without spaces, dashes and case |
| Invoice number found anywhere inside the payment text | number `12` "found" in `2026-11-12` → document wrongly marked paid | the number must stand on its own; a number shorter than 4 signs counts only together with the supplier's name |
| Any `bank_kw` word counted as the supplier's name | `SIA` matched every Latvian company | words under 4 letters and legal forms do not count |
| Amount compared without currency | a 100 USD invoice "paid" by a 100 EUR payment | same currency only; optional CSV column *currency* |
| CSV without D/K column: incoming money not recognised | a customer's 500 EUR payment could be taken as the payment of a 500 EUR supplier invoice | sign of the amount used when outgoing payments are negative |
| The same payment in two overlapping CSV statements counted twice | could mark a second, equal invoice paid | counted once; two equal payments in one file stay two |
| A record with an empty total (assistant could not read it — the prompt tells it to leave `null`) stopped the whole run | no invoice processed at all | listed as *needs a look*, not booked, the run goes on |
| New IDs taken from the row count | after deleting a row, an ID could repeat | IDs continue after the highest |
| Gateways: one Invoices row could cover several card payments of the same amount and day | a second charge without a document stayed unnoticed | one row covers one card payment |

Known limits (not changed): scripts started by hand other than `invoices.py --apply` (for example `documents.py`,
`worktime.py fix`) do not take the run lock yet — start them when no scheduled run is working; amounts are not split
for partial payments; PDF statements are read only in the Swedbank layout.
