# Site module (draft v0.1)

Goal: the worker reports, the foreman decides, the manager sees progress.

## Roles
| Role | Channel | Does |
|---|---|---|
| Worker (master) | Telegram / WhatsApp bot | Morning: gets today's tasks by floor/room. Evening: ticks `+` / `−`, adds reason and photo |
| Team lead / foreman | Bot + e-mail | Gets blocked tasks with reasons; decides (e.g. "order dehumidifier"); assigns |
| Site manager (prorab) | E-mail + weekly summary | Sees progress %, blockers older than 24 h, decisions taken |
| Company manager | E-mail | Escalations only + weekly progress |

## Daily cycle
1. 07:00 tasks to workers (from the object plan).
2. During the day: photo / question any time → linked to task ID.
3. End of day: reminder if no report; report = ticks + reasons.
4. 20:00 foreman gets the list of `−` with reasons; decision buttons.
5. No decision in 24 h → escalation to site manager.

## Reason codes (start list)
`MAT` material missing · `DRY` drying / humidity · `PREV` previous trade not finished · `TOOL` tool/equipment · `INFO` drawing/decision missing · `OTHER` free text.

## Links to existing systems (later)
- Electronic working-time records on Latvian sites (EDLUS) show *who was on site*; FLOKTRON adds *what was done*. Read-only link, no duplication.
- Official construction journal stays where the law requires it (BIS / paper journal); FLOKTRON can export a draft.
- Drawings/CAD: links to files at first; viewers later.

## Example: site water log
For sites that treat their wash water: evening entry per container — litres, pH strip, treatment used, water reused / drained. Same task-ID logic.
