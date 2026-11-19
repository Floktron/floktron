# Supply chain watch — keep a hand on the pulse of what you buy

Optional part of the radar. You list what your work depends on: suppliers, the big producers that set market prices,
listed companies, shipping routes and ports, reference prices (metals, energy), currencies, rules (duties, restrictions).
FLOKTRON checks them from public sources and tells you only when something moves.

| What | How it is checked | Code |
|---|---|---|
| Listed company, commodity future, currency | last close; change vs the day before and vs 5 trading days ago (Yahoo Finance public chart data) | `scripts/supply_watch.py` |
| News about a supplier, producer, route or rule | Google News by your query; titles with alarm words (bankruptcy, fire, strike, force majeure, port closed, price increase…) become **candidates** | `scripts/supply_watch.py` |
| Supplier website | weekly fingerprint of the page text; a change is flagged and your AI assistant describes what changed | `scripts/supply_watch.py --full` |
| What it all means for you | the AI assistant reads every candidate, confirms or lowers the status, writes one line | `prompts/32_supply_chain.md` |

Statuses: 🟢 normal · 🟡 attention · 🔴 urgent · ⚪ no data. A 🔴 reaches you the same evening; 🟡 goes into the weekly
summary; a quiet week is one line: *"Supply chain: no changes ✅"*.

**Your data stays yours.** The watch list is in your own radar file, on your own computer. FLOKTRON only reads public
pages; it never logs in, buys, orders, subscribes or writes to anyone. Do not put recipes, quantities, contract prices
or supplier contacts into the watch list — the names of the things you watch are enough.

## The path from start to end (your AI assistant leads, you decide)
1. **What do you buy?** Tell the assistant your main inputs (materials, packaging, energy, freight) — in plain words.
2. **From whom, and who sets the price?** Your suppliers; for each input the 2–5 biggest producers in the world or
   your region. The assistant may suggest names from public industry sources — you approve each one.
3. **How does it travel?** Country of origin, sea / rail / road, ports of loading and arrival. The assistant adds
   rows for the routes and ports (storms, closures, strikes) and, for sea freight from Asia, the public Drewry
   World Container Index (prompts/32_supply_chain.md tells it how to read it).
4. **Reference prices and currencies.** Futures and currency pairs as on finance.yahoo.com (e.g. `ALI=F` aluminium,
   `HG=F` copper, `TTF=F` EU gas, `EURUSD=X`, `EURCNY=X`). They are a *reference*, never your purchase price.
5. **Rules.** Duties or restrictions on your inputs (e.g. EU anti-dumping, chemical restrictions) — a news query each.
6. **Fill the watch list.** Old radar? `python3 scripts/radar_create.py --add-watch`. The assistant fills the sheet
   `Watchlist` in `data/floktron_radar.xlsx` with you: one row per item, `Active = Yes` only for what you approved.
   Thresholds: empty = `config.yaml → supply_chain` (5 % attention, 10 % urgent for a 5-day move); prices of
   commodities usually get 10 / 20, currencies 3 / 5.
7. **Test without writing:** `python3 scripts/supply_watch.py --dry`, then the weekly run `--full --dry`.
   Sources that do not answer are shown — the assistant records them in `Gaps`.
8. **First real run** writes the base line to `Watch_log` — the first week is your "normal".
9. **Switch on:** add to `config.yaml → schedule`: `supply: "19:10"` (every day) and `supply_week: "Mon 19:20"`,
   then run the installer again (`docs/INSTALL.md`). The AI part (reading candidates) runs with your evening
   news slice — `prompts/30_news_evening.md` step 6.
10. **After 4 weeks** look at the log together with the assistant and tune the thresholds: too many 🟡 → raise them.

## Limits — said plainly
- Public data only: no paid price services, no exchange feeds in real time; prices are end-of-day.
- A news title is not a fact. Every 🔴 candidate is read by the assistant before it reaches you, with the light check
  of `prompts/31_news_check.md`.
- Yahoo Finance, Google News or a supplier site may stop answering or change format — then you see ⚪ and a line in
  `Gaps`; nothing else breaks.
- FLOKTRON gives no forecasts and no investment advice. It shows what moved and where to look.
