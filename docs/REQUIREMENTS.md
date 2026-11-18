# Requirements (minimum)

| Item | Minimum | Note | Status |
|---|---|---|---|
| Always-on machine | Any recent Mac / Windows / Linux, or a small cloud server | Runs scheduled tasks (morning, evening). Must not sleep at run times | Tested on Mac |
| Claude (Anthropic) | Paid plan | Engine for monitoring, letters, routing. authors' cost: ~100 €/month (actual) | Tested |
| Mailbox — Proton | Paid plan (Mail Plus / Unlimited / Business) | Needs Proton Mail Bridge (IMAP/SMTP on localhost) | Tested |
| Mailbox — Gmail | Free or Workspace | Direct IMAP/SMTP with app password, or Gmail API | Not tested yet |
| Mailbox — Outlook / M365 | Any | IMAP/SMTP or Microsoft Graph API; work accounts may need admin consent | Not tested yet |
| Cloud storage | iCloud / Google Drive / OneDrive | Office: <1 GB/month. Site photos: ~1–2 GB per active site per month (estimate: 20 photos × 3 MB × 22 days ≈ 1.3 GB) | Tested (iCloud) |
| Python | 3.10+ | `openpyxl`, standard library | Tested |
| Database | Excel file (`.xlsx`) at start | Move to SQLite/Postgres when >1 site or >20 people (estimate) | Tested (xlsx) |
| Telegram bot | Free | For site workers | Planned |
| WhatsApp Business Platform | Paid per message (Meta) | Only for people who opted in | Planned |

## Monthly cost for a tester (estimate, to be measured)
| Line | Range |
|---|---|
| Claude paid plan | depends on plan — see claude.com/pricing |
| Mail | 0 € (Gmail/Outlook) or Proton paid plan |
| Cloud storage | 0–10 € depending on photo volume |
| Server (if no always-on computer) | ~5–15 € small VPS (estimate) |
