# Support — how to help a client remotely

The client does not need a terminal. The support person looks at three things and fixes.

## 1. What happened
| Where | What it tells |
|---|---|
| `data/run.log` (or `python3 scripts/run.py status`) | every run: `=== date job` … `--- exit 0` (0 = OK, other = error with the reason above it) |
| `data/reports/*-gaps.html` (weekly e-mail to `mail.support_address`) | what FLOKTRON could not do: blocked sites, missing subscriptions, missing functions, client wishes |
| `data/reports/*-weekly.html` | which ray answers, which does not |
| `floktron_base.xlsx → Run_log`, `floktron_radar.xlsx → Run_log` | the same per workbook |

## 2. Typical problems
| Symptom | Cause | Fix |
|---|---|---|
| `MAIL ERROR: Cannot connect … 127.0.0.1:1025` | Proton Mail Bridge is not running | start Bridge; the run retries after 10 and 20 min |
| `Username and Password not accepted` | wrong app password / 2-step verification off | new app password (docs/GMAIL_TEST.md) |
| no runs at all on a Mac | Python has no Full Disk Access | System Settings → Privacy → Full Disk Access → Python |
| `skipped — another FLOKTRON run is working` many times | a run hangs | look at the last `===` block; remove `data/.floktron.lock` |
| replies not counted | changed subject, or reply from another address | the weekly summary lists "unknown addresses"; add that address to the ray or ask to use the button |
| no messages on a working day | the day is in `company.holidays`, or a public holiday | correct `config.yaml` |
| news feed "error: 403" | the site blocks robots | use the Google News row for that country (Gaps says so) |

## 3. Switch off / remove
Follow [UNINSTALL.md](UNINSTALL.md): automatic runs off → app password deleted → files removed → people told.

## 4. Change something for the client
- Departments, people, addresses, languages → `config.yaml → rays` or the `Rays` sheet.
- Times → `config.yaml → schedule`, then run the installer once more (Mac: `install_mac.command` → on).
- Routes → `Routes` sheet. Keywords → radar `Keywords`. Colours → `config.yaml → colors`.
- A client wish that FLOKTRON cannot do yet → one row in radar `Gaps`, kind "client wish". This list is the roadmap.
