# Roadmap (scenario, not commitments)

| Phase | When | What |
|---|---|---|
| F1 Stabilise | Nov–Dec 2026 | Button replies with context; automatic routing of replies; "no reaction" tracking; client follow-up reminders |
| F2 Media radar | Q1 2027 | TV/radio/podcast schedules and guest announcements LV/LT/EE; parliament/committee agendas; questions for live shows |
| F3 Mail hub | Q1 2027 | Mail adapters: Proton (Bridge), Gmail, Outlook/M365, generic IMAP |
| F4 Operations core | Q1–Q2 2027 | Stock, orders, purchase thresholds, rentals, supplier invoice intake |
| F5 Test package | from Dec 2026 (closed) | Private repository, config wizard, install guide (EN), invited testers |
| F6 Site module | Q1–Q2 2027 | Telegram/WhatsApp bot for workers, storage layout, hash log |

## Blockchain — decision 18.11.2026
**Not needed inside one company.** A hash chain in `logs/hash_log.csv` (see STORAGE.md) already proves that records were not changed later, at zero cost.
Blockchain adds value only when several parties who do not trust each other (client, general contractor, subcontractors, bank) must share one record — e.g. milestone acceptance that triggers payment.
Keep as option **F7**: anchor the daily hash to a public chain on client request. Nothing to build now.
An AI assistant is not a smart contract: it advises and reminds, it is not deterministic. Money and acceptance stay with fixed rules + human confirmation.
