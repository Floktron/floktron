# Industry packs — the radar ready on day one

The radar finds news, tenders and consultations by the company's own keywords. Writing 30 good keywords in three
languages takes an evening. An industry pack is a ready, neutral start: the company keeps what fits, removes the rest
and adds its own words. Nothing in a pack is secret and nothing is sent anywhere — it is a file in `templates/industry/`.

## Packs

| Pack | For | Keywords | Languages |
|---|---|---|---|
| `construction` | builders, finishing and renovation crews, building-material suppliers, construction services | 24 (10 every run, 14 first run of the month) | LV, RU, EN |
| `logistics` | road haulage, freight forwarding, warehousing, courier and last-mile companies | 24 (9 every run, 15 first run of the month) | LV, RU, EN |
| `wholesale` | wholesalers and distributors: food, building materials, equipment, consumables | 24 (9 every run, 15 first run of the month) | LV, RU, EN |
| `production` | manufacturers and workshops: metal, wood, food, plastics, building products, contract manufacturing | 24 (9 every run, 15 first run of the month) | LV, RU, EN |
| `rental` | rental of construction machinery, tools, scaffolding, generators, cabins and vehicles | 24 (8 every run, 16 first run of the month) | LV, RU, EN |
| `services` | companies serving other companies: cleaning, facility management, security, maintenance and repair | 24 (8 every run, 16 first run of the month) | LV, RU, EN |

A company in two industries can apply two packs — every pack has its own IDs, nothing is added twice. A pack for another industry: copy `construction.json`, change the words, keep the format.

## Three questions at setup

The setup wizard (step 7) asks only:

1. **Industry** — which pack.
2. **Country and city** — sources for that country, one keyword "<city> construction".
3. **3–5 competitors** — company names as people write them. They go to the Keywords sheet (searched every run) and to
   the Players sheet. INTERNAL: competitor names never go into posts or external documents.

```
python3 scripts/industry_pack.py list
python3 scripts/industry_pack.py show construction
python3 scripts/industry_pack.py apply construction --country LV --city Rīga --competitor "Name 1" --competitor "Name 2" --dry
python3 scripts/industry_pack.py apply construction --country LV --city Rīga --competitor "Name 1" --competitor "Name 2"
```

`apply` adds, never overwrites: rows already in the radar stay, the same keyword is never added twice, so it is safe
to run again. A working language the pack does not have (e.g. DE) gets an empty cell and the comment "translate DE" —
the AI assistant translates those rows with the person.

## What a pack adds

| Sheet | What |
|---|---|
| Keywords | the pack's words (ID `BU..`), the city (`Place`), competitors (`CO..`) |
| Sources | typical public sources of the industry for the chosen country and the EU (access "check" until the first run) |
| Registry_queries | words in the names of new companies (LV): competitors and possible clients |
| Watchlist | supply-chain examples, Active = No until the company switches them on (docs/SUPPLY_CHAIN.md) |
| Players | competitors named at setup |

## Changing the words later

- **In the table:** `data/floktron_radar.xlsx`, sheet Keywords. Priority A = every run, B = first run of the month,
  off = paused.
- **From the phone (managers):** `/words` — what is searched now · `/addword facade insulation` — add one (first
  language; the assistant translates later) · `/delword cement price` — pause one (the row stays, set A again to resume).
- **From the computer:** `python3 scripts/industry_pack.py add "…"` · `off "…"` · `words`.

Google News takes about 8 words per query, so FLOKTRON splits longer lists into several queries (up to 32 priority-A
words per language and run). Keep priority A for what really matters.
