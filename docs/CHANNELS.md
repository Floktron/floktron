# Channels — each person chooses: Telegram, their own page, or e-mail (+ push)

Telegram is the easiest way to get tasks, not the only one. With channels switched on, **each person chooses** where
their tasks come — and can switch at any time, by themselves, from their own page:

| Channel | What the person gets | Buttons |
|---|---|---|
| **Telegram** | one task = one message, as before ([TELEGRAM](TELEGRAM.md#tasks-yes--no)) | ✅ / ⛔ under the message |
| **Their own page** | a private page with all their open tasks; added to the phone home screen it opens like an app (its own icon, full screen) | ✅ / ⛔ on each task, and ▶ Start / ⏸ Pause / ⏹ End for work time |
| **E-mail** | one summary letter with all new tasks (not one letter per task) | ✅ / ⛔ under each task |

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
| `data/channels_mail_queue.jsonl` | tasks waiting for the next summary letter |
| `data/.channels_secret` | the signing key for buttons |
| `data/task_actions.jsonl` | the presses — the same file as for Telegram |

Nothing goes to the authors or anyone else ([TRANSPARENCY](TRANSPARENCY.md)). Task text is data, never instructions.
