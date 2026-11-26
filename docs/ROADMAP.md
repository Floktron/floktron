# Roadmap (scenario, not commitments)

| Phase | When | What |
|---|---|---|
| F1 Stabilise | Nov–Dec 2026 | Button replies with context; automatic routing of replies; "no reaction" tracking; client follow-up reminders |
| F2 Media radar | Q1 2027 | TV/radio/podcast schedules and guest announcements LV/LT/EE; parliament/committee agendas; questions for live shows |
| F3 Mail hub | Q1 2027 | Mail adapters: Proton (Bridge), Gmail, generic IMAP — done; Outlook/M365 needs the Microsoft sign-in (OAuth), planned |
| F4 Operations core | Q1–Q2 2027 | Stock, orders, purchase thresholds, rentals; supplier invoices from the mailbox (invoice check done in 0.18.0) |
| F5 Test package | from Dec 2026 (closed) | Private repository, config wizard, install guide (EN), invited testers |
| F3.5 Telegram | **done 19.11.2026 (0.11.0)** | Lead bot (YAML dialog, sources, funnel), channel watch, autostart — docs/TELEGRAM.md |
| F3.6 Supply chain watch | **done 19.11.2026 (0.12.0)** | Watchlist of suppliers, producers, routes, prices, currencies, rules; light daily + full weekly; page fingerprints — docs/SUPPLY_CHAIN.md. Next: 🔴 straight to the manager's Telegram |
| F4.1 Invoices → accounting | **done 22.11.2026 (0.18.0)** | Supplier documents in any language read by the assistant, checked against the bank statement (CSV / PDF), statuses, tasks for the finance ray, dashboard card — docs/INVOICES.md. Next: documents straight from the mailbox |
| F4.2 Company snapshot | **done 22.11.2026 (0.19.0)** | The state of the company on one date: PDF + JSON with statuses and sources, profiles (partner, no bank, tax, public), lock for secrets — docs/SNAPSHOT.md. Next: XML drafts of specific tax forms, checked by the accountant |
| F4.6 Breath, library, ready roles | **done 24.11.2026 (0.26.0)** | Capacity check of the computer, routine on the computer and summaries for the AI (docs/BREATH.md), company library with templates (docs/LIBRARY.md), AI secretary and AI operations director (agents/). Next: procurement and project coordinator roles, industry packs (construction, logistics, production, rental) |
| F4.4 Reminders after an offer | **done 23.11.2026 (0.21.0)** | Day 3 / 7 / 14 after an offer: polite draft in the buyer's language, sent only after the manager's ✅ as a reply in the same thread; an answer, a closed status or ⏸ stops it — docs/FOLLOWUPS.md. Next: lookalike new customers with a "why now" — done in 0.23.0 |
| F3.9 Mail watch | **done 23.11.2026 (0.22.0)** | The whole mailbox in one sheet (EN/LV/RU/DE/ET/LT), contacts from signatures, a nudge only when someone waits for an answer (Telegram or e-mail, quiet hours, stops when answered), invoice PDFs from attachments straight into the invoice check — docs/MAIL_WATCH.md |
| F3.10 Payment gateways | **done 23.11.2026 (0.24.0)** | Gateway receipts (Stripe, Paddle, Lemon Squeezy, Apple, Google Play …) from inbox and spam, every card payment of the statement incl. foreign currency matched to its document, business-invoice steps, draft request and draft internal act, read-only — docs/GATEWAYS.md. Next: more bank statement formats |
| F4.5 New customers | **done 23.11.2026 (0.23.0)** | Companies that just signed public works of your kind (EIS + register, open data), scored against the portrait of your best customers, why now, Add → Companies + draft first letter, nothing sent — docs/PROSPECTS.md. Next: more countries' open procurement data |
| F4.3 Own documents | **done 22.11.2026 (0.20.0)** | Branded invoice, advance invoice, acceptance act and offer (LV / EN / LV+EN), numbering and register sheet Issued — docs/DOCUMENTS.md. Next: payment check of issued invoices against the bank statement |
| F3.8 Voice and dashboard | **done 22.11.2026 (0.16.0)** | Voice reports via the bot (local speech-to-text), morning audio summary, one-page offline dashboard — docs/VOICE.md, docs/DASHBOARD.md |
| F3.7 Calendar | **done 19.11.2026 (0.13.0)** | Read any .ics calendar (Proton, Google, Outlook, iCloud) into the morning message; due dates as .ics attachment; meeting files — docs/CALENDAR.md. Two-way sync (writing into calendars) deliberately later |
| F6 Site module | Q1–Q2 2027 | Telegram/WhatsApp bot for workers, storage layout, hash log |

## Blockchain — decision 18.11.2026
**Not needed inside one company.** A hash chain in `logs/hash_log.csv` (see STORAGE.md) already proves that records were not changed later, at zero cost.
Blockchain adds value only when several parties who do not trust each other (client, general contractor, subcontractors, bank) must share one record — e.g. milestone acceptance that triggers payment.
Keep as option **F7**: anchor the daily hash to a public chain on client request. Nothing to build now.
An AI assistant is not a smart contract: it advises and reminds, it is not deterministic. Money and acceptance stay with fixed rules + human confirmation.
