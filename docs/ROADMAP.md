# Roadmap (scenario, not commitments)

| Phase | When | What |
|---|---|---|
| F1 Stabilise | Nov–Dec 2026 | Button replies with context; automatic routing of replies; "no reaction" tracking; client follow-up reminders |
| F2 Media radar | Q1 2027 | TV/radio/podcast schedules and guest announcements LV/LT/EE; parliament/committee agendas; questions for live shows |
| F3 Mail hub | Q1 2027 | Mail adapters: Proton (Bridge), Gmail, Outlook/M365, generic IMAP |
| F4 Operations core | Q1–Q2 2027 | Stock, orders, purchase thresholds, rentals, supplier invoice intake |
| F5 Test package | from Dec 2026 (closed) | Private repository, config wizard, install guide (EN), invited testers |
| F3.5 Telegram | **done 19.11.2026 (0.11.0)** | Lead bot (YAML dialog, sources, funnel), channel watch, autostart — docs/TELEGRAM.md |
| F3.6 Supply chain watch | **done 19.11.2026 (0.12.0)** | Watchlist of suppliers, producers, routes, prices, currencies, rules; light daily + full weekly; page fingerprints — docs/SUPPLY_CHAIN.md. Next: 🔴 straight to the manager's Telegram |
| F3.8 Voice and dashboard | **done 22.11.2026 (0.16.0)** | Voice reports via the bot (local speech-to-text), morning audio summary, one-page offline dashboard — docs/VOICE.md, docs/DASHBOARD.md |
| F3.7 Calendar | **done 19.11.2026 (0.13.0)** | Read any .ics calendar (Proton, Google, Outlook, iCloud) into the morning message; due dates as .ics attachment; meeting files — docs/CALENDAR.md. Two-way sync (writing into calendars) deliberately later |
| F6 Site module | Q1–Q2 2027 | Telegram/WhatsApp bot for workers, storage layout, hash log |

## Blockchain — decision 18.11.2026
**Not needed inside one company.** A hash chain in `logs/hash_log.csv` (see STORAGE.md) already proves that records were not changed later, at zero cost.
Blockchain adds value only when several parties who do not trust each other (client, general contractor, subcontractors, bank) must share one record — e.g. milestone acceptance that triggers payment.
Keep as option **F7**: anchor the daily hash to a public chain on client request. Nothing to build now.
An AI assistant is not a smart contract: it advises and reminds, it is not deterministic. Money and acceptance stay with fixed rules + human confirmation.
