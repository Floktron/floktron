# AI operations director

**For:** the owner or manager who runs several departments, crews or sites and wants one picture every morning.

## Every day
| When | What the operations director does | Part |
|---|---|---|
| evening | Radars check news, registries, supply chain and Telegram channels; only what matters goes into the report | [SUPPLY_CHAIN](../../docs/SUPPLY_CHAIN.md), `prompts/30_news_evening.md` |
| morning | Every department (ray) gets 1–5 tasks with buttons *done / not done / question* | README · How it works |
| day | Answers are collected; no answer or *not done* goes up: doer → lead → manager | `scripts/route.py` |
| morning | The manager sees what is done, stuck, changed outside and whether the system is healthy — on one page and as audio for the car | [DASHBOARD](../../docs/DASHBOARD.md), [VOICE](../../docs/VOICE.md) |
| Monday | The weekly summary: *all normal* or exactly what moved; the gaps report | `scripts/weekly_summary.py`, `scripts/gaps_report.py` |
| on request | Company snapshot for a partner, the bank or the tax office | [SNAPSHOT](../../docs/SNAPSHOT.md) |

## Never by itself
Decides nothing about money, contracts or people · changes no task owner · publishes nothing.

## What you get
Every morning one page: what moves, what is stuck and who decides — without calling everyone.
