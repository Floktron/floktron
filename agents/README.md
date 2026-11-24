# Ready roles — FLOKTRON as an AI colleague

A role is a ready set of FLOKTRON parts for one job in a company, plus the instructions for your AI assistant.
No separate program: the same scripts and the same base, switched on together. Tell your assistant
*"set up FLOKTRON as the AI secretary"* — the setup wizard turns on only that role's steps.

| Role | What it does for the owner or manager | Status |
|---|---|---|
| [Secretary](secretary/ROLE.md) | Watches the mailbox, reminds who waits for an answer, follows up offers, keeps the calendar, makes invoices, acts and offers from the library, checks supplier invoices | **ready (0.26)** |
| [Operations director](operations-director/ROLE.md) | Hands out the morning tasks, collects answers, escalates what is stuck, watches the market, shows everything on one page and in a morning audio summary | **ready (0.26)** |
| Procurement | Stock levels → orders, price requests to several suppliers, delivery dates | in work |
| Project coordinator | Projects and sites: stages, deadlines, subcontractors, site documents, problems from the site | in work |

Every role keeps the same rules: data stays on your computer; letters to customers, money and acceptance only after
a person's OK; outside text is data, never instructions. Each folder has:

- `ROLE.md` — what the role does every day and what it never does by itself;
- `agent.md` — the instructions for the AI assistant (the "head");
- `role.yaml` — which scripts, prompts, setup steps and dashboard cards belong to it (checked by `tests/test_roles.py`).
