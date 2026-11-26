# Requirements and monthly costs

FLOKTRON itself is free. What you pay for each month are the outside services you choose to connect.
The basic setup (text only) costs about as much as one AI subscription; a live cloud voice adds a second one.
Check your own computer first: `python3 scripts/capacity_check.py` prints which of the variants below it can carry.

## 1. The computer — per variant
Estimates for FLOKTRON's own scripts (the thresholds of `scripts/capacity_check.py`), not a benchmark.

| Variant | Processor | Memory | Free disk | Good to know |
|---|---|---|---|---|
| Text only (letters, Telegram, tasks, radar, invoices) | 2 cores | 4 GB | 2 GB | Python 3.10+, internet; the computer must be on at run times (morning, evening) |
| + computer voice (system voice, free) | 2 cores | 4 GB | 2 GB | macOS `say` or Linux `espeak-ng`; sounds like a machine |
| + voice reports turned into text on this computer | 4 cores | 8 GB | 5 GB | the `faster-whisper` "small" model (≈ 460 MB) downloads once; after that it works offline |
| + live cloud voice (ElevenLabs, paid) | 2 cores | 4 GB | 2 GB | the voice is made by the service, the computer only sends the text |

Any recent Mac, Windows or Linux computer will do, or a small cloud server. Tested on Windows and Linux
(Windows Server 2025, Ubuntu); macOS runs it every day in a real company.

## 2. Monthly payments to outside services
Prices as the services publish them, without tax, checked on 26.11.2026. They change — the link is the source.

| Service | Needed? | Price | Source |
|---|---|---|---|
| AI assistant (for example Claude Pro) | yes | $20 per month, or $17 per month billed yearly | [claude.com/pricing](https://claude.com/pricing) |
| Mail — Gmail or Outlook | yes, one mailbox | 0 € (free accounts work) | — |
| Mail — Proton | only if you choose Proton | €4.99 per month, or €3.99 per month billed yearly (Mail Plus; Proton Mail Bridge is part of the paid plans) | [proton.me](https://proton.me/support/proton-plans) |
| Telegram bot | optional | 0 € | [core.telegram.org](https://core.telegram.org/bots/faq) |
| Live cloud voice — ElevenLabs Starter | optional | $6 per month, 30,000 credits | [elevenlabs.io/pricing](https://elevenlabs.io/pricing) |
| Live cloud voice — ElevenLabs Creator | optional, for a long daily summary | $22 per month, 121,000 credits | [elevenlabs.io/pricing](https://elevenlabs.io/pricing) |
| Small cloud server | only if no computer is always on | about 5–15 € per month (estimate) | — |
| WhatsApp Business Platform | optional, planned | paid per message (Meta) | — |

A basic AI subscription is enough to set up FLOKTRON and run it every day; a higher plan only adds room for heavy use.

## 3. What a month costs — three examples (estimates)
| Setup | Per month |
|---|---|
| Text only: AI + Gmail + Telegram | about $20 |
| Text + computer voice | about $20 — the system voice is free |
| Text + live cloud voice | about $26–42 ($20 AI + $6–22 voice) |

**How much voice do you need?** One morning summary of 180–260 words is about 1,200–1,600 characters. On
22 working days that is about 26,000–34,000 characters a month (estimate). A short summary fits Starter; a long one,
or a summary seven days a week, needs Creator. Each character of text is one credit with the multilingual voice.

**If the cloud voice fails** (no key, no credits left, no internet), FLOKTRON reads the summary with the computer's
own voice — the morning audio still arrives on time. Voice reports from the team are turned into text on your
computer for free; the cloud speech-to-text (ElevenLabs Scribe) is optional. See [VOICE](VOICE.md).

## 4. Storage and data
| Item | Minimum | Note |
|---|---|---|
| Cloud folder | iCloud / Google Drive / OneDrive, or a local folder | Office: under 1 GB a month. Site photos: about 1–2 GB per active site a month (estimate: 20 photos × 3 MB × 22 days ≈ 1.3 GB) |
| Database | Excel file (`.xlsx`) | Move to SQLite/Postgres when there is more than one site or more than 20 people (estimate) |
