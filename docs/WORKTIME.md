# Work time — start, pause, end in Telegram; hours on the dashboard

Your team marks the working day with three buttons in the work chat with your bot. The manager sees who is at work
now, the hours of today and of the month, and what needs a look. Once a month there is a table for the accountant.
Everything runs on your computer and stays in your `data/` folder.

## What a team member sees

Three buttons always stay under the message field:

| Button | What happens |
|---|---|
| **▶ Start** | the shift starts. With `worktime.geo: true` the phone asks once to share its location **at this moment**: one point is kept, nothing during the day |
| **⏸ Pause** / **▶ Back** | a break; the pause is not counted as work |
| **⏹ End** | the shift ends; the bot answers with today's hours |

`/hours` shows my hours today, this week and this month. The morning task (mail or Telegram) stays as before: the
person gets the task, then taps **▶ Start**.

At `worktime.remind_at` (default 20:00) the bot asks whoever has not ended: *"Still at work? Started 07:48, 12 h so far."*
with **⏹ End now** / **▶ Still working**. If nobody answers, the shift is marked **"no end mark"** and its hours are
**not counted**: FLOKTRON never makes hours up. The manager corrects the day.

A night shift (22:00 → 06:30) is one shift on the day it started; night hours are counted separately.

## What the manager sees

On the dashboard ([DASHBOARD](DASHBOARD.md)), the block **⏱ Work time**:

- four numbers: at work now (3/6), hours today, hours this month, marks to check;
- every person: green = working, blue = on pause, grey = finished or not here today; the site from the start mark
  — green ✓ when inside the site radius, orange with the distance when far;
- the month: days, hours, overtime (over `day_hours` a day), night hours, weekend and holiday hours;
- **to check**: no end mark, started far from the site, a very long day, every manager correction with its reason.
  The first ones also go to "Needs your attention".

In the bot, `/who` (managers only) lists who is at work now.

## Without Telegram

Telegram is the easiest channel, not the only one. Any other channel — the dashboard on the office computer, a
kiosk tablet at the entrance, an e-mail or SMS gateway you already have — marks the same way with one command:

    python3 scripts/worktime.py mark --who "Anna" --action start --by kiosk     # start | pause | back | end

The mark goes to the same log and the same hours; the dashboard shows which channel it came from.

## Corrections — only by the manager, always with a reason

    python3 scripts/worktime.py fix --who "Anna" --date 2026-11-26 --end 17:30 --why "forgot to tap End"

The original marks are never changed: the log `data/worktime.jsonl` only grows; a correction is a new line with who,
when and why. The dashboard and the month table show that the day was corrected.

## The month for the accountant

    python3 scripts/worktime.py month --month 2026-11      # → data/worktime_2026-11.xlsx

Sheet **Month**: person, days, hours, overtime, night, weekend/holiday, days without an end mark, corrected days.
Sheet **Days**: every shift with start, end, pause, hours, site and notes. Your accountant applies your own rules
(summed working time, rates, rest periods) — FLOKTRON gives the facts, it does not calculate pay.

## Setup

In `config/config.yaml`:

```yaml
worktime:
  enabled: true
  geo: true                    # one location point at «Start» (the phone asks); false = buttons only
  people:                      # Telegram chat id: name (write /id to the bot to see an id)
    "123456789": "Anna"
  sites:                       # optional: where work happens; the start point is compared with these
    - {name: "Site Park 12", lat: 56.9510, lon: 24.1130, radius_m: 250}
  remind_at: "20:00"
  day_hours: 8
  night: ["22:00", "06:00"]
  holidays: ["2026-11-18"]     # your public holidays (weekends are counted by themselves)
```

The bot must be running ([TELEGRAM](TELEGRAM.md)); the people above join the team automatically and never get the
client dialog.

**Invite link instead of chat ids.** Make one link per person — it works **once, for that one person, and only until
its date** (0.38):

```
python3 scripts/worktime.py invite --name "Anna" --days 7
→ https://t.me/<your bot>?start=wt-3f9c0a17b2d84e61   (works once, until 2026-12-04)
```

The person opens the link, taps Start and gets the three buttons; the managers get one message «Anna joined».
The first chat that opens a link owns it. If the link was forwarded and someone else opens it, they are refused and
the managers are told. Who joined is kept in `data/worktime_people.json`, made links in `data/worktime_invites.json`,
used ones in `data/worktime_invites_used.json`. A phone lost or the wrong person in? Send `/remove <chat id>` to the
bot (managers only) or run `python3 scripts/worktime.py remove --who "Anna"` — the person is out at once, no restart.
Codes written by hand in `worktime.invites` still work (`"wt-…": "Anna"` or `"wt-…": {name: "Anna", until: "2026-12-04"}`),
also once per person; a code used before 0.38 belongs to whoever joined with it.
A person who does not want to share a location writes `/in` instead of tapping ▶ Start. Reminders are sent by the bot itself; `python3 scripts/worktime.py remind` does the same from a scheduler.

## Personal data — keep it small

Working-time records are an employer's duty in many countries (in the EU see the Court of Justice judgment C-55/18,
2019; in Latvia the Labour Law requires a record of hours worked). FLOKTRON keeps only what that record needs:

| Kept | Not kept |
|---|---|
| name (from your config), chat id, start / pause / back / end times | personal code, photos, face or fingerprint (biometrics) |
| one location point at «Start», only with `geo: true`; the site name and the distance | location during the day, routes, live tracking |
| manager corrections with the reason | anything from the phone besides the tapped button |

Before you switch `geo` on, tell the team in writing what is kept, why and for how long (your privacy notice or work
rules), and decide how long you keep `data/worktime.jsonl`. A forwarded location is refused; a location chosen by hand
on the map cannot be told from a real one by Telegram, so the point is a check, not proof.

Camera monitoring of workplaces is **not** part of FLOKTRON.
