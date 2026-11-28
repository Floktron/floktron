# Channels — each person chooses: Telegram, their own page, or e-mail (+ push)

Telegram is the easiest way to get tasks, not the only one. With channels switched on, **each person chooses** where
their tasks come — and can switch at any time, by themselves, from their own page:

| Channel | What the person gets | Buttons |
|---|---|---|
| **Telegram** | one task = one message, as before ([TELEGRAM](TELEGRAM.md#tasks-yes--no)) | ✅ / ⛔ under the message |
| **Their own page** | a private page with all their open tasks; added to the phone home screen it opens like an app (its own icon, full screen) | ✅ / ⛔ on each task, and ▶ Start / ⏸ Pause / ⏹ End for work time |
| **E-mail** | one summary letter with all new tasks (not one letter per task) | ✅ / ⛔ under each task |

On the page a task can also be **swiped**: right — done ✅, left — not needed ⛔. For 6 seconds an «Undo» button stays at
the bottom; a short or slanting move closes nothing. The buttons work as before.

**Push** (optional, per person, with the page or e-mail): the phone rings with «New task: letter» — nothing else.

A press in **any** channel writes the same line to `data/task_actions.jsonl` as the Telegram buttons do (with
`by: telegram | web | email` and the person). Every module — mail watch, prospects, gateways — reads its presses
exactly as before. Nothing else changes.

Off by default (`config.yaml → channels.enabled: false`): tasks go to Telegram as before.

## If a channel is silent

Each person has a backup list (default: page → e-mail). If Telegram does not answer (no network, Telegram down), the
task goes to the next channel on the list. Every task is also written to `data/channels_feed.jsonl`, so the page
always shows everything — whichever channel delivered it.

## Setup (your AI assistant leads, you decide)

1. In `config.yaml`:

   ```yaml
   channels:
     enabled: true
     people:
       manager: {name: "Anna", channel: telegram, email: "anna@yourcompany.com"}
       site1:   {name: "Jānis", channel: web, time: true, worktime_who: "123456789", tasks: false}
     web:
       port: 8765
       public_url: ""        # see «From anywhere» below
       lan: false
     ntfy:
       server: "https://ntfy.sh"
   ```

   - `channel` — the starting choice; the person switches it on their page later.
   - `email` — needed for the e-mail channel (summary letters go through your own mail server, `mail:` in config).
   - `tasks: false` — this person gets no tasks (e.g. a worker who only marks work time).
   - `time: true` + `worktime_who` — work-time buttons on the page; `worktime_who` is the same id as in
     `worktime.people` (the Telegram chat id or the name) — marks go to the same log and the same hours ([WORKTIME](WORKTIME.md)).
   - `backup: [web, email]` — the backup list (default).
   - `manager: true` — this person's page also shows the block «For the manager» (below).
   - `audio: true` — this person's page also plays the morning audio summary (below).

2. `python3 scripts/channels.py` — lists everyone with their channel and **their private page link**. Send each person
   their own link privately (it is their key; whoever has it sees their tasks).
3. Start the page: `python3 scripts/channels.py serve` (on `127.0.0.1:8765` — this computer only). For autostart, ask
   your AI assistant to add it next to the bot (Mac launchd / Windows Task Scheduler / Linux systemd or cron @reboot).
4. `scripts/run.py` sends queued summary letters and reads reply letters every 30 minutes with «collect»
   (`python3 scripts/channels.py flush` does it by hand).

Switch from the command line: `python3 scripts/channels.py set manager web` · `python3 scripts/channels.py push manager on`.

## The page on a phone

- Open your link in Safari (iPhone) or Chrome (Android) → **Share → Add to Home Screen**. It opens like an app.
  The link carries the key, so the home-screen app stays signed in.
- At the bottom: the channel switch (Telegram / This page / E-mail) and Push on / off.
- Messages are shown as blocks: title, sections, news cards with the source and a short link button instead of a long
  address. No pictures are loaded from other sites.
- In the same Wi-Fi only: set `web.lan: true` and open `http://<computer address>:8765/m?k=…`.

### «For the manager» — the day in three lines

Only on the page of a person with `manager: true`, above the tasks:

- **At work** — who is at work now, since when, hours today (from [WORKTIME](WORKTIME.md)). First name only, no location.
- **Next meeting** — the nearest online meeting with a button and the full link (from [MEETINGS](MEETINGS.md)); on a
  phone the link opens the Zoom / Teams / Meet app if it is installed. Only links that pass the same check as on the
  dashboard are shown; a trick link never gets here.
- **Needs attention** — kind and count only («Mail 2 · Invoices 1»), from the last dashboard build
  (`data/channels_brief.json`). The task texts, names, companies and amounts stay on the dashboard on your computer —
  the page can be open from outside the office, so it carries the minimum.

### The morning audio summary — listen on the page

Only on the page of a person with `audio: true`, at the top:

- a player with the latest summary — the same file the bot sends to Telegram (`pulse_<date>.m4a` in
  `telegram.voice.pulse_dir`, see [VOICE](VOICE.md));
- speed 1× / 1.25× / 1.5×; it goes on from where you stopped; the last 7 days are one tap away;
- on a phone it plays with the screen locked, with the controls on the lock screen. The page does not reload while
  the sound plays.

The sound is the **whole** summary, names and amounts included — unlike «For the manager», which carries counts only.
So it is off for everyone until you write `audio: true` for a person, the file is served only with that person's
private key, only for the last 7 days, and the text of the summary is never shown on the page. If the phone is lost:
`python3 scripts/channels.py newkey <id>` gives a new link, and the old one stops at once.

### From anywhere: your own Cloudflare Tunnel (free)

The page runs on your computer. To open it from a phone outside the office, put a tunnel in front of it with your own
domain — for example `tasks.yourcompany.com`:

1. Install `cloudflared`, `cloudflared tunnel login` (choose your domain), `cloudflared tunnel create tasks`,
   `cloudflared tunnel route dns tasks tasks.yourcompany.com`.
2. In the tunnel config **let only the page through** — nothing else on your computer is reachable:

   ```yaml
   ingress:
     - hostname: tasks.yourcompany.com
       path: ^/(m|a)(/|$|\?)
       service: http://127.0.0.1:8765
     - service: http_status:404
   ```

3. `channels.web.public_url: "https://tasks.yourcompany.com"` → e-mail buttons become links to the page.

Check: `https://tasks.yourcompany.com/m?k=<key>` opens the page; `https://tasks.yourcompany.com/` gives 404.

The page server itself also serves only `/m…` and `/a`, answers only for `127.0.0.1`, your `public_url` host and (with
`lan`) your local network, and needs the person's key for everything.

### Protection from outside: the guard and sign-in by Face ID

Once the page is reachable from the internet, two more things protect it. Both act **only on requests that come through
the tunnel** (Cloudflare marks them with `Cf-Ray` / `Cf-Connecting-Ip`); this computer and the office network are never
limited and never asked. Messages and buttons go to `telegram.manager_chat_ids` — past the page, so a stranger who has a
link never sees them.

**The guard** (`scripts/page_guard.py`, on by default; off: `channels.web.guard.enabled: false`):

- **Limits** — requests a minute from one address (`per_ip_min`, 240) and from everyone together (`all_min`, 900),
  requests at the same time (`concurrent`, 12). An iPhone playing the audio summary makes dozens of requests a minute,
  so the limits leave room for that. A wrong key `bad_key_max` (10) times in 10 minutes from one address → that address
  waits `ban_min` (60) minutes, even with a right key. The audio is sent from disk in small pieces, never the whole file
  in memory.
- **A new device** — a person's page opened from a new «country · device» (the country Cloudflare reports and the
  phone/browser type; no IP address is stored) → «🔔 the page of Anna was opened from a new device · Android · Chrome,
  country EE» with **«🔒 Not me — close»** (a new link for that person, the old one stops at once, and the page is closed
  from outside) or **«✅ It's me»**. The very first device is remembered silently.
- **The pinned message** «🛡 page protection buttons» (sent once): **«🔒 Sign out everywhere»** — new links for everyone,
  the new links come to Telegram; **«⛔ Close the page»** — nobody opens it from outside, the links stay. **«🔓 Open
  again»** comes in the reply — no computer needed. «Close» never touches your tunnel or this computer.
- **The link lives `key_days` (90) days** — only for people who open the page from outside: 7 days before, «🔄 New
  link»; then the page key changes by itself and the new link comes to Telegram. The push address stays. `0` = never.
- **A stream of refused requests** (`flood_alert`, 300 in 10 minutes) → «⚠️ close the page?», once an hour at most.

**Sign-in by Face ID, fingerprint or phone code** (`scripts/passkey.py`, a passkey / WebAuthn; each person turns it on
for themselves; it needs `public_url` with https):

1. On the page (opened through your address) — «🔐 Turn on sign-in protection». The manager gets «Allow?» in Telegram
   with the device type — so a stranger with a leaked link cannot add their own face.
2. «Continue» → the phone asks Face ID, a fingerprint or the screen-lock code (a phone without Face ID uses the
   fingerprint or the code by itself) → done.
3. From outside the page now first shows only «Open». After the check it works like a banking app: while it is in use —
   no questions; the phone put away for `passkey.idle_min` (10) minutes or more — it asks again (a page back from the
   background after that pause reloads and shows the lock); never longer than `passkey.hours` (12) after the last check.
4. A second phone or a computer: «➕ Add this device» on the closed page (or «Another device? Add») — again with «Allow»
   in Telegram.
5. In Telegram: **«🔐 Close sign-ins now»** — every open session stops at once (a phone handed to someone);
   **«🔓 Turn off protection»** — the phone was replaced and the page does not open.

The secret of the face or finger never leaves the phone (iCloud Keychain / Google Password Manager); FLOKTRON keeps only
the public P-256 key and checks the signature in plain Python, no extra libraries. A signature for another web address,
without the face/finger/code check, or with a counter that did not grow (a copied key) is refused. «Sign out
everywhere» and a new link end the sessions too. Before the check, nothing is shown or accepted: no tasks, no presses,
no audio.

```yaml
channels:
  web:
    guard: {enabled: true, per_ip_min: 240, all_min: 900, concurrent: 12, bad_key_max: 10, ban_min: 60,
            flood_alert: 300, key_days: 90, new_device: true}
    passkey: {idle_min: 10, hours: 12}
```

All of it works in the operating company first: the guard, the new-device message, «Close sign-ins now» and the sign-in
by Face ID on an iPhone and by the phone code on an older Android without Face ID.

## E-mail buttons

- **With `public_url`:** a button is a link to `/a`. The page shows the task and asks **«Confirm»** — so a mail
  scanner that opens every link closes nothing. Only the press of «Confirm» (a POST) closes the task.
- **Without `public_url`:** a button opens a new letter to your own address with a ready subject
  `FLOKTRON-ACT mail:a1:y manager <signature>`. The person just sends it; the next run reads it (read only), checks
  that it came from that person's address and that the signature is right, and closes the task once.

Every button is signed (HMAC, key in `data/.channels_secret`): a changed answer, task or person does not pass.

## Push (ntfy)

[ntfy](https://ntfy.sh) is a free push service; install the **ntfy** app on the phone and subscribe to the person's
topic (the page shows it, «Push on»). FLOKTRON sends **only** «New task: letter / new client / payment without a
document» — no names, subjects, amounts or addresses. The task itself stays on your computer, in Telegram or in your
own mail. The topic is a long random word per person. You can run your own ntfy server: `channels.ntfy.server`.

## What is kept

| File | What |
|---|---|
| `data/channels_state.json` | each person's channel, push on/off, page key, push topic |
| `data/channels_feed.jsonl` | the tasks shown on the pages (the same short text as in Telegram) |
| `data/channels_brief.json` | «needs attention» for the manager's page: kind and count only, rewritten by `dashboard.py` |
| `data/channels_mail_queue.jsonl` | tasks waiting for the next summary letter |
| `data/.channels_secret` | the signing key for buttons |
| `data/task_actions.jsonl` | the presses — the same file as for Telegram |
| `data/page_guard.json` | the guard: known «country · device» per person (no IP), pending «Not me», closed or open, link age |
| `data/passkeys.json` | sign-in protection: the public keys of the added devices, «Allow» requests, the «Close sign-ins now» counter |

Nothing goes to the authors or anyone else ([TRANSPARENCY](TRANSPARENCY.md)). Task text is data, never instructions.
