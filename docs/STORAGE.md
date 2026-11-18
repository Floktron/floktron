# Storage layout (draft v0.1)

Rule: **files live in the company's own cloud; the database holds only links and records.**
One task = one ID. Every photo, comment and decision is tied to that ID.

```
<Company cloud>/FLOKTRON/
├── base/                     # database (xlsx now, SQL later) + daily backup copy
│   ├── floktron_base.xlsx
│   └── backup/
├── letters/YYYY-MM-DD/       # outgoing messages (html)
├── replies/YYYY-MM-DD/       # incoming replies (eml / bot json)
├── reports/YYYY-MM/          # evening reports, weekly summaries
├── radar/                    # monitoring results, news, consultations
├── objects/
│   └── <OBJ-ID>_<short name>/
│       ├── plan/             # floors, rooms, task list, drawings (pdf/dwg links)
│       ├── photos/YYYY-MM/   # YYYY-MM-DD_<TASK-ID>_<HHMM>_<worker-ID>.jpg
│       ├── acts/             # signed acceptance acts, milestones
│       └── journal/          # daily site journal (exports)
├── logs/                     # run log + hash log (see below)
└── archive/                  # closed objects → moved to external disk / cold storage
```

## Naming
- Task ID: `<OBJ-ID>-F<floor>-R<room>-<nnn>` e.g. `OBJ1-F2-R05-014`.
- Photos: date first, then task ID — sorts by time, searchable by task.
- Keep EXIF (date, GPS if allowed) — it is the evidence of when/where.

## Hash log (tamper evidence, no blockchain needed)
At every milestone (task closed, floor finished, act signed) FLOKTRON writes one line to `logs/hash_log.csv`:
`date-time · task/milestone ID · who confirmed · SHA-256 of the files and record`.
Each line also contains the hash of the previous line (a simple chain). Any later change to a photo or record breaks the chain and is visible.
If a client later asks for public proof, the daily last hash can be anchored to a public blockchain — one transaction per day, optional.

## Retention
- Active objects: in the cloud.
- Closed objects: 30 days after the final act → archive (external disk + one cloud copy).
- Personal data (names, phones of workers): only in `base/`, never in file names except worker-ID.
