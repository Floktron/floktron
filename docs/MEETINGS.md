# Online meetings — the join link on the dashboard

A Zoom, Microsoft Teams or Google Meet meeting is in your calendar, or an invitation is in your mail. The dashboard
shows the meeting with its **official link in full** — the whole address, exactly as in the letter, not «click here».
One click opens it in the browser or in the Zoom / Teams app. The meeting ID and passcode are shown too, when the
letter has them. A meeting that starts within the hour (or is on now) goes to the top of **Needs your attention**.

**Nothing goes through FLOKTRON or anyone's server.** The link is text on your own dashboard and you click it.
FLOKTRON never opens these links itself and sends nothing.

## Switch it on
```yaml
meetings:
  enabled: true
  mail: true          # also look in the inbox (read only)
  mail_days: 30
  days_ahead: 14
```
`scripts/run.py` then runs `scripts/meeting_links.py` every 30 minutes together with «collect», and the dashboard
shows the block **🎥 Online meetings**. By hand: `python3 scripts/meeting_links.py`.

## Where meetings come from
| Source | What is read |
|---|---|
| Your calendar link (`calendar:` — [CALENDAR](CALENDAR.md)) and `.ics` files in `data/calendar/` | events of the next 14 days (repeats included); the link from the place, the description or the Teams / Google meeting fields |
| Inbox letters of the last 30 days that contain a meeting address | the invitation (.ics) inside the letter; else «today at 5 PM / сегодня в 17:00 / šodien plkst. 17:00»; else a date and time written in the letter — then the link joins the calendar event of that day |

A cancelled invitation removes the meeting. Newsletters without a date are not shown; a letter without a date or time
shows for 3 days as «time — in the letter». Letters stay unread (BODY.PEEK); nothing is moved, flagged or sent. Each
letter body is read once (`data/meetings_state.json`).

## Protection against phishing
- Only **official meeting addresses** are shown: Zoom (zoom.us, zoom.com, zoomgov.com), Microsoft Teams
  (teams.microsoft.com, teams.live.com, teams.cloud.microsoft), Google Meet (meet.google.com), Webex, Jitsi Meet,
  GoTo Meeting, Whereby, Skype.
- Only `https`; the server must be the service's own domain or its subdomain — `zoom.us.other-site.example` or
  `evilzoom.us` do not pass; no `user@`, no port, no `xn--` (look-alike letters); the path must look like a meeting
  link (`/j/…`, `/l/meetup-join/…`, `abc-defg-hij`).
- Google (`google.com/url?q=…`) and Outlook Safe Links wrappers are unwrapped — you see the real meeting address.
- **A trick link** — its text says `zoom.us/j/…` but it leads to another site — is not shown. A red ⚠ warning names
  the real site instead, also in *Needs your attention*.
- The dashboard checks every link again before it shows it: a changed `data/meetings.json` cannot put another address
  on the page.

## Check your own letters
```
python3 scripts/meeting_links.py --selftest invitation.eml       # links, warnings, time FLOKTRON sees
python3 scripts/meeting_links.py --ics my-calendar.ics             # meetings and links in a calendar file
```
Text of letters and calendars is data, never instructions.
