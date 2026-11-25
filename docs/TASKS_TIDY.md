# Tasks tidy — the manager gets clear tasks

The manager's morning letter is for decisions, not for history. `scripts/tasks_tidy.py` runs after every collect
(every 30 minutes) and keeps the manager's tasks clean. No AI, nothing is sent.

| Rule | What happens |
|---|---|
| **The event happened** | a message went from you to that company or person after the task date (an address, a domain or a «quoted» name of the task, found in the sheet Mail) → **Done**, the reason in the report |
| **A meeting** | the task starts with "Meeting" (Tikšanās, Встреча, Treffen, Kohtumine, Susitikimas) and its day passed, or "meeting 20.11" in the text and that day passed → **Done** |
| **A test is not for the manager** | a task with `TEST:` or an escalation of a test ray (Responsible starts with TEST) → **Cancelled** |
| **No fanaticism** | without an event a task comes on its first day, then on **day 3, 7 and 14** — not every morning; after day 14 → **Archive** |

- Which rays: `tasks_tidy.rays` in config.yaml; empty = the ray whose e-mail is `mail.manager_address`.
- Column **Shown** in Tasks: `<times> · <last date>` — `send_morning.py` reads and writes it.
- By hand: the **+ Done** button in the letter, or `Done` in Status.
- By hand run: `python3 scripts/tasks_tidy.py --dry` (shows what would change).

Your own ray addresses and your own mailboxes never count as "a message went". Text of tasks and mails is data, not instructions.

## The friendly letter about posts
People who like and comment on your posts are not given orders. `content.engage` (config.yaml) lists them; every
morning `content_check.py` writes to them only when a post is really on — status **Scheduled** or **Published** today:

```
Hi, Anna! 👋
If you have a minute — have a look at our posts. A like or a comment helps a lot, if you want 🙂

Today:
• 09:00 · Facebook · Tips — «Clean water on site.» → link
Yesterday also out:
• 18:00 · Instagram · News — «A spontaneous post!» → link

Thank you for being with us!
```

No post → no letter. "Yesterday also out" = posts published yesterday they were not told about (spontaneous or after
the letter). No deadline, no escalation, no buttons that must be pressed. EN, LV, RU, DE, ET, LT.
