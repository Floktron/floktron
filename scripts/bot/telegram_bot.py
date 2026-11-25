# -*- coding: utf-8 -*-
"""FLOKTRON · bot/telegram_bot.py — Telegram bot: a configurable dialog (funnel) that turns chats into leads.

The dialog lives in a YAML file (config/bot_flow.yaml, example: config/bot_flow.example.yaml):
steps with a text, buttons (choose → next step) or a typed answer (text / phone / email / number).
The last step saves the lead to data/floktron_leads.xlsx and tells the manager in Telegram.
Every step reached is written to the "Events" sheet, so you can see where people stop (the funnel).

No extra packages: only the Python standard library + openpyxl + PyYAML (already used by FLOKTRON).
The bot talks only to api.telegram.org. It stores nothing outside data/.

Setup (5 minutes):
    1. In Telegram open @BotFather → /newbot → copy the token.
    2. export FLOKTRON_TG_TOKEN=...            (or macOS Keychain, telegram.keychain_service in config.yaml)
    3. python3 scripts/bot/telegram_bot.py --check      # token works? shows the bot name
    4. Write /id to your bot → it answers your chat id → put it in telegram.manager_chat_ids
    5. python3 scripts/bot/telegram_bot.py --loop       # keep running (launchd/systemd keep it alive)

Other modes:
    --once     read new messages once and exit (for a scheduler every 1–2 minutes)
    --flow-check   validate the dialog file and print the step tree, no network
Voice (telegram.voice, optional): a team member sends a voice message → it is transcribed on this computer
(scripts/voice.py) → saved to data/voice_reports.xlsx and sent to the manager as text. Audio summary: when a text file
voice.pulse_dir/pulse_<YYYY-MM-DD>.txt appears (written by the morning AI run), the bot reads it aloud and sends the audio
to the managers — to listen in the car. See docs/VOICE.md.
The team (manager_chat_ids, team_chat_ids, voice users) never gets the client dialog: free text and /start give a short help;
tasks come one per message with two buttons ✅ / ⛔ (scripts/task_notice.py) — a press is written to data/task_actions.jsonl
and the message turns into «✅ Closed · dd.mm hh:mm»; a text reply to a task message closes it with the comment. /client — try the dialog.
Manager commands (only from manager_chat_ids): /leads — last 10 leads · /funnel — how many reached each step · /pulse — audio summary now ·
/channels — watched channels; forward a post from a public channel to add it (telegram.channels_file) ·
/backup — password-protected backup of the whole setup now, kept on the computer (docs/MOVE.md) ·
/version — this FLOKTRON version and the newest one (docs/UPDATES.md); a new version is told to the managers once
Anyone: /start (optionally /start <source>, e.g. t.me/<bot>?start=qr_bucket) · /menu · /privacy · /forget · /id
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, SCRIPTS)

API = "https://api.telegram.org/bot{token}/{method}"
MAX_TEXT = 500            # longest typed answer we keep
MAX_PER_MINUTE = 30       # messages from one chat per minute; more are ignored (flood guard)
SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")   # Telegram deep-link payload rules
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")
PHONE_RE = re.compile(r"^\+?[0-9 ()-]{7,20}$")
LEAD_COLUMNS = ["Date", "Lead ID", "Source", "Language", "Telegram", "Chat ID", "Stage", "Name", "Company",
                "Phone", "Email", "Answers", "Next step", "Owner", "Updated"]
CORE_FIELDS = {"name": "Name", "company": "Company", "phone": "Phone", "email": "Email"}
VOICE_COLUMNS = ["Date", "Chat ID", "Telegram", "Who / ray", "Seconds", "Transcript", "File", "Status"]
VOICE_TEXT = {  # replies to the person who sent a voice message (override in telegram.voice.texts)
    "saved": "✅ Report saved:\n«{text}»\nIf something is wrong — just send another voice message.",
    "later": "✅ Voice message received — it will be transcribed a little later.",
    "not_team": "Voice reports are accepted only from the team. Please write your question as text 🙂",
    "off": "Please write your message as text 🙂",
}


TEAM_TEXT = {  # replies in the team's own chat — managers never get the client dialog (override in telegram.team_texts)
    "help": "This is your work chat. One message = one task: ✅ done · ⛔ not needed.\n"
            "Or reply to a task message with text — it closes with your comment.\n/pulse — audio summary · /client — try the client dialog",
    "closed_y": "✅ Closed", "closed_n": "⛔ Not needed", "toast": "Saved ✅",
    "reply_closed": "✅ Closed with your comment.", "already": "ℹ️ This task is already closed.",
}


class BotError(Exception):
    pass


# ---------------------------------------------------------------- config and flow
def load_yaml(path):
    if not os.path.exists(path):
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def token_from(cfg):
    env = cfg.get("token_env", "FLOKTRON_TG_TOKEN")
    if os.environ.get(env):
        return os.environ[env].strip()
    service = cfg.get("keychain_service")
    if service and sys.platform == "darwin":
        r = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                           capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout.strip()
    raise BotError(f"No bot token: set environment variable {env}"
                   + (f" or Keychain item '{service}'" if service else ""))


def check_flow(flow):
    """Return a list of problems in the dialog file (empty = fine)."""
    probs = []
    steps = flow.get("steps") or {}
    langs = flow.get("languages") or ["en"]
    if flow.get("start") not in steps:
        probs.append(f"start step '{flow.get('start')}' is not in steps")
    finals = 0
    for sid, st in steps.items():
        if not isinstance(st, dict):
            probs.append(f"{sid}: must be a mapping")
            continue
        if not st.get("text"):
            probs.append(f"{sid}: no text")
        elif isinstance(st["text"], dict):
            miss = [l for l in langs if l not in st["text"]]
            if miss:
                probs.append(f"{sid}: text missing language(s) {', '.join(miss)}")
        kinds = [k for k in ("buttons", "input", "final") if st.get(k)]
        if len(kinds) != 1:
            probs.append(f"{sid}: needs exactly one of buttons / input / final (has {kinds or 'none'})")
        if st.get("final"):
            finals += 1
        if st.get("input") and st["input"] not in ("text", "phone", "email", "number"):
            probs.append(f"{sid}: input must be text / phone / email / number")
        if st.get("input") and not st.get("save"):
            probs.append(f"{sid}: input step needs 'save: <field>'")
        nexts = [b.get("next") for b in st.get("buttons") or [] if not b.get("url")]
        if st.get("input"):
            nexts.append(st.get("next"))
        for n in nexts:
            if n not in steps:
                probs.append(f"{sid}: next step '{n}' does not exist")
        for b in st.get("buttons") or []:
            if not b.get("label"):
                probs.append(f"{sid}: a button has no label")
            if b.get("url") and not str(b["url"]).startswith("https://"):
                probs.append(f"{sid}: link buttons must use https://")
    if not finals:
        probs.append("no final step (final: true) — leads would never be saved")
    return probs


def say(text, lang, fields=None):
    """Pick the language, fill {field} placeholders with the person's answers (never with code)."""
    if isinstance(text, dict):
        text = text.get(lang) or text.get("en") or next(iter(text.values()), "")
    fields = fields or {}
    return re.sub(r"\{(\w+)\}", lambda m: str(fields.get(m.group(1), "")), str(text or ""))


# ---------------------------------------------------------------- Telegram API
class Api:
    def __init__(self, token, timeout=60):
        self.token, self.timeout = token, timeout

    def call(self, method, **params):
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(API.format(token=self.token, method=method), data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                out = json.loads(r.read(2_000_000).decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                out = json.loads(e.read(100_000).decode("utf-8"))
            except ValueError:
                raise BotError(f"{method}: HTTP {e.code}") from None
        if not out.get("ok"):
            raise BotError(f"{method}: {out.get('description', 'error')}")
        return out.get("result")


    def download(self, file_id, dest):
        """Telegram file → local path (voice messages are small .oga files)."""
        info = self.call("getFile", file_id=file_id)
        url = "https://api.telegram.org/file/bot{}/{}".format(self.token, info["file_path"])
        with urllib.request.urlopen(url, timeout=self.timeout) as r, open(dest, "wb") as f:
            f.write(r.read(25_000_000))
        return dest

    def upload(self, method, field, path, **params):
        """Send a file (sendAudio / sendDocument) as multipart/form-data."""
        import uuid
        b = uuid.uuid4().hex
        body = b""
        for k, v in params.items():
            v = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        with open(path, "rb") as f:
            body += (f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{os.path.basename(path)}"\r\n'
                     f"Content-Type: application/octet-stream\r\n\r\n").encode() + f.read() + b"\r\n"
        body += f"--{b}--\r\n".encode()
        req = urllib.request.Request(API.format(token=self.token, method=method), data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(req, timeout=max(self.timeout, 120)) as r:
            out = json.loads(r.read(2_000_000).decode("utf-8"))
        if not out.get("ok"):
            raise BotError(f"{method}: {out.get('description', 'error')}")
        return out.get("result")


# ---------------------------------------------------------------- storage
class Store:
    """data/bot_state.json — sessions and the update offset; data/floktron_leads.xlsx — leads and events."""

    def __init__(self, data_dir=DATA, leads_file=None):
        os.makedirs(data_dir, exist_ok=True)
        self.state_path = os.path.join(data_dir, "bot_state.json")
        self.leads_path = leads_file or os.path.join(data_dir, "floktron_leads.xlsx")
        self.state = {"offset": 0, "sessions": {}, "flood": {}}
        if os.path.exists(self.state_path):
            with open(self.state_path, encoding="utf-8") as f:
                self.state.update(json.load(f))

    def save_state(self):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.state_path)

    def _wb(self):
        import openpyxl
        import safe_xlsx  # noqa: F401 — typed answers never become formulas
        if os.path.exists(self.leads_path):
            return openpyxl.load_workbook(self.leads_path)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Leads"
        ws.append(LEAD_COLUMNS)
        wb.create_sheet("Events").append(["Date", "Session", "Source", "Step", "Answer"])
        wb.create_sheet("Stages").append(["Stage", "Meaning"])
        for s in [("New", "came from the bot, nobody answered yet"),
                  ("Contacted", "manager wrote or called"),
                  ("Qualified", "real need, volume and timing known"),
                  ("Offer", "offer or calculation sent"),
                  ("Test", "introductory stage on the client's water"),
                  ("Won", "paid / contract"),
                  ("Lost", "no — reason in Next step"),
                  ("Deleted", "person asked to forget their data")]:
            wb["Stages"].append(list(s))
        return wb

    def add_event(self, session, source, step, answer=""):
        wb = self._wb()
        wb["Events"].append([now_str(), session, source, step, str(answer)[:120]])
        self._save(wb)

    def add_lead(self, row):
        wb = self._wb()
        wb["Leads"].append([row.get(c, "") for c in LEAD_COLUMNS])
        self._save(wb)

    def forget(self, chat_id):
        """Blank personal data of this chat in Leads (row stays for counting, stage = Deleted)."""
        if not os.path.exists(self.leads_path):
            return 0
        wb = self._wb()
        ws, n = wb["Leads"], 0
        idx = {c: i for i, c in enumerate(LEAD_COLUMNS)}
        for row in ws.iter_rows(min_row=2):
            if str(row[idx["Chat ID"]].value) == str(chat_id):
                for c in ("Telegram", "Chat ID", "Name", "Company", "Phone", "Email", "Answers"):
                    row[idx[c]].value = ""
                row[idx["Stage"]].value = "Deleted"
                row[idx["Updated"]].value = now_str()
                n += 1
        self._save(wb)
        return n

    def add_voice(self, row, path=None):
        """data/voice_reports.xlsx, sheet Voice: one row per voice message."""
        import openpyxl
        import safe_xlsx  # noqa: F401
        path = path or os.path.join(os.path.dirname(self.state_path), "voice_reports.xlsx")
        if os.path.exists(path):
            wb = openpyxl.load_workbook(path)
        else:
            wb = openpyxl.Workbook()
            wb.active.title = "Voice"
            wb.active.append(VOICE_COLUMNS)
        wb["Voice"].append([row.get(c, "") for c in VOICE_COLUMNS])
        for _ in range(5):
            try:
                wb.save(path)
                return path
            except PermissionError:
                time.sleep(3)
        raise BotError("voice_reports.xlsx is locked (open in Excel?)")

    def last_leads(self, k=10):
        if not os.path.exists(self.leads_path):
            return []
        rows = list(self._wb()["Leads"].iter_rows(min_row=2, values_only=True))
        return rows[-k:]

    def funnel(self):
        if not os.path.exists(self.leads_path):
            return {}
        seen = {}
        for d, sess, src, step, ans in self._wb()["Events"].iter_rows(min_row=2, values_only=True):
            seen.setdefault(step, set()).add(sess)
        return {k: len(v) for k, v in seen.items()}

    def _save(self, wb):
        for _ in range(5):
            try:
                wb.save(self.leads_path)
                return
            except PermissionError:      # open in Excel — wait a little
                time.sleep(3)
        raise BotError("data/floktron_leads.xlsx is locked (open in Excel?) — lead kept in bot_state.json")


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def session_id(chat_id, started):
    return hashlib.sha256(f"{chat_id}:{started}".encode()).hexdigest()[:10]


# ---------------------------------------------------------------- the bot
class Bot:
    def __init__(self, api, flow, cfg, store):
        self.api, self.flow, self.cfg, self.store = api, flow, cfg, store
        self.steps = flow["steps"]
        self.langs = flow.get("languages") or ["en"]
        self.managers = {str(x) for x in cfg.get("manager_chat_ids") or []}
        self.config_path = cfg.get("_config_path")
        voice_users = (cfg.get("voice") or {}).get("users") or {}
        # the team: managers + team_chat_ids + voice users — tasks, buttons ✅/⛔, never the client funnel
        self.team = self.managers | {str(x) for x in cfg.get("team_chat_ids") or []} | {str(k) for k in voice_users}
        self.ttext = {**TEAM_TEXT, **(cfg.get("team_texts") or {})}

    # ---- sending
    def send(self, chat_id, text, keyboard=None, contact_button=None):
        p = {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True}
        if keyboard:
            p["reply_markup"] = {"inline_keyboard": keyboard}
        elif contact_button:
            p["reply_markup"] = {"keyboard": [[{"text": contact_button, "request_contact": True}]],
                                 "resize_keyboard": True, "one_time_keyboard": True}
        else:
            p["reply_markup"] = {"remove_keyboard": True}
        return self.api.call("sendMessage", **p)

    def show(self, chat_id, sess):
        sid = sess["step"]
        st = self.steps[sid]
        lang = sess.get("lang") or self.langs[0]
        text = say(st["text"], lang, sess["fields"])
        if st.get("buttons"):
            kb = []
            for i, b in enumerate(st["buttons"]):
                label = say(b["label"], lang)[:64]
                if b.get("url"):
                    kb.append([{"text": label, "url": b["url"]}])
                else:
                    kb.append([{"text": label, "callback_data": f"s:{sid}:{i}"[:64]}])
            self.send(chat_id, text, keyboard=kb)
        elif st.get("input") == "phone":
            self.send(chat_id, text, contact_button=say(self.flow.get("share_phone_label", "Share phone"), lang))
        else:
            self.send(chat_id, text)
        if not sess.get("logged_" + sid):
            sess["logged_" + sid] = True
            self.store.add_event(sess["id"], sess.get("source", ""), sid)
        if st.get("final"):
            self.finish(chat_id, sess)

    def finish(self, chat_id, sess):
        f = dict(sess["fields"])
        answers = "; ".join(f"{k}: {v}" for k, v in f.items() if k not in CORE_FIELDS)
        lead_id = "TG-" + datetime.date.today().strftime("%y%m%d") + "-" + sess["id"][:4].upper()
        row = {"Date": now_str(), "Lead ID": lead_id, "Source": sess.get("source", ""),
               "Language": sess.get("lang", ""), "Telegram": sess.get("user", ""), "Chat ID": str(chat_id),
               "Stage": "New", "Answers": answers, "Next step": self.flow.get("next_step", "Contact within 1 hour"),
               "Owner": "", "Updated": now_str()}
        for k, col in CORE_FIELDS.items():
            row[col] = f.get(k, "")
        try:
            self.store.add_lead(row)
        except BotError:
            self.store.state.setdefault("unsaved_leads", []).append(row)
        note = [f"🆕 {lead_id} · {row['Source'] or 'direct'} · {row['Language']}",
                f"{row['Name']} {('· ' + row['Company']) if row['Company'] else ''}".strip(),
                f"☎ {row['Phone'] or '—'} · ✉ {row['Email'] or '—'} · {row['Telegram'] or ''}",
                answers]
        for m in self.managers:
            try:
                self.send(int(m), "\n".join(x for x in note if x))
            except BotError:
                pass
        sess["done"] = True

    def start(self, chat_id, user, payload=""):
        started = time.time()
        source = payload if SOURCE_RE.match(payload or "") else ""
        sess = {"id": session_id(chat_id, started), "step": self.flow["start"], "fields": {},
                "source": source, "user": user, "started": started,
                "lang": self.langs[0] if len(self.langs) == 1 else ""}
        self.store.state["sessions"][str(chat_id)] = sess
        self.show(chat_id, sess)

    # ---- receiving
    def flood(self, chat_id):
        key, minute = str(chat_id), int(time.time() // 60)
        rec = self.store.state["flood"].get(key, [minute, 0])
        rec = [minute, rec[1] + 1] if rec[0] == minute else [minute, 1]
        self.store.state["flood"][key] = rec
        return rec[1] > MAX_PER_MINUTE

    def handle(self, upd):
        if "callback_query" in upd:
            q = upd["callback_query"]
            chat_id = q["message"]["chat"]["id"]
            if str(q.get("data", "")).startswith("fk:"):     # task buttons ✅ / ⛔ (scripts send them to the team)
                return self.on_task_button(q)
            try:
                self.api.call("answerCallbackQuery", callback_query_id=q["id"])
            except BotError:
                pass
            if self.flood(chat_id):
                return
            self.on_button(chat_id, q.get("data", ""), q.get("from", {}))
            return
        msg = upd.get("message")
        if not msg or msg.get("chat", {}).get("type") != "private":
            return                                  # the bot works only in private chats
        chat_id = msg["chat"]["id"]
        if self.flood(chat_id):
            return
        user = "@" + msg["from"]["username"] if msg.get("from", {}).get("username") else \
            (msg.get("from", {}).get("first_name") or "")
        text = (msg.get("text") or "").strip()
        lang = (self.store.state["sessions"].get(str(chat_id)) or {}).get("lang") or self.langs[0]
        if msg.get("voice") or msg.get("audio") or msg.get("video_note"):
            return self.on_voice(chat_id, user, msg)
        team = str(chat_id) in self.team
        if team and text in ("/start", "/menu", "/help") or (team and text.startswith("/start ")):
            return self.team_help(chat_id)
        if team and text == "/client":
            return self.start(chat_id, user, "team_test")
        if text.startswith("/start"):
            return self.start(chat_id, user, text[6:].strip())
        if text == "/menu":
            return self.start(chat_id, user, (self.store.state["sessions"].get(str(chat_id)) or {}).get("source", ""))
        if text == "/id":
            return self.send(chat_id, f"chat id: {chat_id}")
        if text == "/privacy":
            return self.send(chat_id, say(self.flow.get("privacy", "We keep only what you type here."), lang))
        if text == "/forget":
            self.store.state["sessions"].pop(str(chat_id), None)
            self.store.forget(chat_id)
            return self.send(chat_id, say(self.flow.get("forgotten", "Done — your data is deleted."), lang))
        if str(chat_id) in self.managers and text == "/pulse":
            return self.send_pulse(force=True, only=chat_id)
        if str(chat_id) in self.managers and text == "/backup":
            return self.backup_now(chat_id)
        if str(chat_id) in self.managers and text == "/version":
            return self.version_info(chat_id)
        if str(chat_id) in self.managers and text in ("/leads", "/funnel", "/channels"):
            return self.manager(chat_id, text)
        if str(chat_id) in self.managers and self.cfg.get("channels_file"):
            origin = msg.get("forward_origin") or {}
            ch = origin.get("chat") if origin.get("type") == "channel" else msg.get("forward_from_chat")
            if ch:
                return self.add_channel(chat_id, ch)
        sess = self.store.state["sessions"].get(str(chat_id))
        if team and not (sess and not sess.get("done") and sess.get("source") == "team_test"):
            return self.on_team_text(chat_id, msg, text)      # the team is never a client
        if not sess or sess.get("done"):
            return self.start(chat_id, user)
        st = self.steps.get(sess["step"], {})
        if st.get("input"):
            value = text
            if st["input"] == "phone" and msg.get("contact"):
                value = msg["contact"].get("phone_number", "")
            self.on_input(chat_id, sess, st, value)
        else:
            self.send(chat_id, say(self.flow.get("use_buttons", "Please use the buttons ↑"), lang))
            self.show(chat_id, sess)

    # ---- the team's tasks: one message = one task, buttons ✅ / ⛔, reply with text = ✅ with a comment
    def actions_file(self):
        return os.path.join(os.path.dirname(self.store.state_path), self.cfg.get("actions_file") or "task_actions.jsonl")

    def team_help(self, chat_id):
        self.store.state["sessions"].pop(str(chat_id), None)   # an unfinished client dialog of a team member — gone
        return self.send(chat_id, self.ttext["help"])

    def close_task(self, chat_id, msg, data, frm, comment=""):
        parts = str(data).split(":")
        if len(parts) != 4 or parts[0] != "fk" or parts[3] not in ("y", "n"):
            return ""
        who = "@" + frm["username"] if frm.get("username") else str(frm.get("first_name") or chat_id)
        rec = {"ts": now_str(), "chat": str(chat_id), "by": who, "kind": parts[1], "key": parts[2], "ans": parts[3],
               "comment": re.sub(r"[\x00-\x1f]", " ", comment or "").strip()[:MAX_TEXT]}
        with open(self.actions_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        label = self.ttext["closed_y" if parts[3] == "y" else "closed_n"]
        text = (msg.get("text") or "").rstrip() + f"\n\n{label} · {datetime.datetime.now():%d.%m %H:%M}"
        if rec["comment"]:
            text += f"\n💬 {rec['comment'][:300]}"
        try:   # no reply_markup → Telegram removes the buttons
            self.api.call("editMessageText", chat_id=chat_id, message_id=msg["message_id"], text=text[:4000],
                          disable_web_page_preview=True)
        except (BotError, KeyError):
            pass
        return self.ttext["toast"]

    def on_task_button(self, q):
        chat_id = q["message"]["chat"]["id"]
        toast = ""
        if str(chat_id) in self.team and not self.flood(chat_id):
            toast = self.close_task(chat_id, q["message"], q.get("data", ""), q.get("from", {}))
        try:
            self.api.call("answerCallbackQuery", callback_query_id=q["id"], text=toast)
        except BotError:
            pass

    def task_of(self, chat_id, rep):
        """callback_data of ✅ under the message the team member replied to ('' = not an open task)."""
        for row in (rep.get("reply_markup") or {}).get("inline_keyboard") or []:
            for b in row:
                d = str(b.get("callback_data", ""))
                if d.startswith("fk:") and d.endswith(":y"):
                    return d
        sent = os.path.join(os.path.dirname(self.actions_file()), "task_sent.jsonl")   # written by scripts/task_notice.py
        found = ""
        if rep.get("message_id") and os.path.exists(sent):
            with open(sent, encoding="utf-8") as f:
                for line in f:
                    try:
                        s = json.loads(line)
                    except ValueError:
                        continue
                    if str(s.get("chat")) == str(chat_id) and s.get("mid") == rep["message_id"]:
                        found = str(s.get("y", ""))
        if found and any(self.ttext[k] in (rep.get("text") or "") for k in ("closed_y", "closed_n")):
            return "closed"
        return found

    def on_team_text(self, chat_id, msg, text):
        rep = msg.get("reply_to_message") or {}
        data = self.task_of(chat_id, rep) if rep else ""
        if data == "closed":
            return self.send(chat_id, self.ttext["already"])
        if data and text:
            self.close_task(chat_id, rep, data, msg.get("from", {}), comment=text)
            return self.send(chat_id, self.ttext["reply_closed"])
        return self.team_help(chat_id)

    def on_button(self, chat_id, data, frm):
        sess = self.store.state["sessions"].get(str(chat_id))
        parts = data.split(":")
        if not sess or len(parts) != 3 or parts[0] != "s" or parts[1] != sess["step"] or sess.get("done"):
            return                                  # old button from an earlier message — ignore
        try:
            b = self.steps[parts[1]]["buttons"][int(parts[2])]
        except (KeyError, IndexError, ValueError):
            return
        for k, v in (b.get("set") or {}).items():
            if k == "lang" and v in self.langs:
                sess["lang"] = v
            else:
                sess["fields"][k] = v
        self.store.add_event(sess["id"], sess.get("source", ""), parts[1], say(b["label"], "en"))
        sess["step"] = b["next"]
        self.show(chat_id, sess)

    def on_input(self, chat_id, sess, st, value):
        lang = sess.get("lang") or self.langs[0]
        value = re.sub(r"[\x00-\x1f]", " ", value or "").strip()[:MAX_TEXT]
        kind = st["input"]
        ok = bool(value) and (
            kind == "text" or (kind == "email" and EMAIL_RE.match(value))
            or (kind == "phone" and PHONE_RE.match(value))
            or (kind == "number" and re.match(r"^\d{1,7}([.,]\d{1,2})?$", value)))
        skip = st.get("optional") and value.lower() in ("-", "—", "nav", "нет", "no", "skip")
        if not ok and not skip:
            self.send(chat_id, say(st.get("error") or self.flow.get("bad_input", "Please check and send again."), lang))
            return
        sess["fields"][st["save"]] = "" if skip else value
        self.store.add_event(sess["id"], sess.get("source", ""), sess["step"], "(skipped)" if skip else "(answer)")
        sess["step"] = st["next"]
        self.show(chat_id, sess)

    def add_channel(self, chat_id, ch):
        """A manager forwarded a post: put its public channel on the watch list (scripts/tg_watch.py reads it)."""
        name = ch.get("username") or ""
        if not re.match(r"^[A-Za-z0-9_]{4,64}$", name):
            return self.send(chat_id, f"⚠️ «{ch.get('title', '')}» — private channel, it cannot be watched (no public page).")
        path = self.cfg["channels_file"]
        have = set()
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                have = {l.split("#")[0].strip().lower() for l in f}
        if name.lower() in have:
            return self.send(chat_id, f"ℹ️ @{name} is already watched.")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{name}  # {str(ch.get('title', ''))[:60]} · added {now_str()}\n")
        return self.send(chat_id, f"✅ @{name} added to channel monitoring ({str(ch.get('title', ''))[:60]}).")

    def backup_now(self, chat_id):
        """/backup: the password-protected archive of the whole setup, made on this computer (docs/MOVE.md).
        The archive is NOT sent to Telegram — it stays on the computer / in the company cloud."""
        self.send(chat_id, "⏳ Backup is being made on the computer…")
        try:
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "move.py"), "backup"], cwd=ROOT,
                               capture_output=True, text=True, timeout=1800)
            line = (r.stdout.strip().splitlines() or ["❌ no answer"])[-1]
        except subprocess.TimeoutExpired:
            line = "❌ backup took longer than 30 minutes — see data/run.log"
        return self.send(chat_id, line.replace(ROOT, "FLOKTRON") + "\nThe archive stays on the computer; it is not sent here.")

    # ---- new FLOKTRON versions (scripts/update_check.py writes the notice; the bot only passes it on)
    def update_paths(self):
        dirs = [os.path.dirname(self.store.state_path), DATA]
        return [os.path.join(d, n) for d in dict.fromkeys(dirs) for n in ("update_notice.json", "update_state.json")]

    def _read_json(self, p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def version_info(self, chat_id):
        from update_check import local_version
        st = next((x for x in map(self._read_json, self.update_paths()[1::2]) if x), {}) or {}
        cur = local_version() or "?"
        latest, checked = st.get("latest") or "—", st.get("checked") or "—"
        tail = ("\nNewer version available — tell your AI assistant: \"update FLOKTRON\"."
                if latest not in ("—", cur) else "")
        return self.send(chat_id, f"FLOKTRON {cur}\nNewest on GitHub: {latest} (checked {checked}){tail}")

    def update_due(self):
        """Pass a new-version notice to the managers once (only release news; no links besides the releases page)."""
        for p in self.update_paths()[0::2]:
            n = self._read_json(p)
            if not n or n.get("sent") or not self.managers:
                continue
            for m in self.managers:
                try:
                    self.send(m, str(n.get("text") or "")[:3500])
                except Exception as e:  # noqa: BLE001 — never stop the bot
                    print(f"{now_str()} update notice: {e}")
            n["sent"] = True
            with open(p, "w", encoding="utf-8") as f:
                json.dump(n, f, ensure_ascii=False)

    def manager(self, chat_id, cmd):
        if cmd == "/channels":
            path = self.cfg.get("channels_file") or ""
            lines = [l.strip() for l in open(path, encoding="utf-8")] if path and os.path.exists(path) else []
            lines = [l for l in lines if l and not l.startswith("#")]
            return self.send(chat_id, "Watched channels:\n" + ("\n".join(lines) or "— none yet. Forward any post from a public channel to add it."))
        if cmd == "/leads":
            rows = self.store.last_leads()
            lines = [f"{r[1]} · {r[6]} · {r[7] or '—'} · {r[8] or ''} · {r[9] or r[10] or ''}" for r in rows]
            return self.send(chat_id, "\n".join(lines) or "No leads yet.")
        f = self.store.funnel()
        order = list(self.steps)
        lines = [f"{s}: {f[s]}" for s in order if s in f]
        return self.send(chat_id, "Reached each step (sessions):\n" + ("\n".join(lines) or "—"))

    # ---- voice
    def vcfg(self):
        return self.cfg.get("voice") or {}

    def vtext(self, key):
        return (self.vcfg().get("texts") or {}).get(key) or VOICE_TEXT[key]

    def on_voice(self, chat_id, user, msg):
        vc = self.vcfg()
        if not vc.get("enabled"):
            return self.send(chat_id, self.vtext("off"))
        users = {str(k): str(v) for k, v in (vc.get("users") or {}).items()}
        is_mgr = str(chat_id) in self.managers
        if str(chat_id) not in users and not is_mgr and not vc.get("accept_unknown"):
            return self.send(chat_id, self.vtext("not_team"))
        media = msg.get("voice") or msg.get("audio") or msg.get("video_note") or {}
        if int(media.get("duration") or 0) > int(vc.get("max_seconds", 300)):
            return self.send(chat_id, f"⚠️ Max {int(vc.get('max_seconds', 300)) // 60} min per message — please split it.")
        vdir = os.path.join(os.path.dirname(self.store.state_path), "voice")
        os.makedirs(vdir, exist_ok=True)
        ext = ".oga" if msg.get("voice") else ".mp4" if msg.get("video_note") else ".m4a"
        path = os.path.join(vdir, datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{chat_id}{ext}")
        who = users.get(str(chat_id), "manager" if is_mgr else "unknown")
        row = {"Date": now_str(), "Chat ID": str(chat_id), "Telegram": user, "Who / ray": who,
               "Seconds": media.get("duration", ""), "File": os.path.basename(path), "Status": "New"}
        try:
            self.api.download(media["file_id"], path)
            import voice
            row["Transcript"] = voice.stt(path, lang=vc.get("stt_lang"), engine=vc.get("stt_engine", "auto"),
                                          model=vc.get("stt_model", "small"))[:3000]
        except Exception as e:  # noqa: BLE001 — keep the file, transcribe later
            row["Transcript"], row["Status"] = "", f"not transcribed: {str(e)[:120]}"
        rp = vc.get("reports_file")
        if rp and not os.path.isabs(os.path.expanduser(rp)):
            rp = os.path.join(os.path.dirname(self.config_path or self.store.state_path), rp)
        self.store.add_voice(row, rp and os.path.expanduser(rp))
        if row["Transcript"]:
            self.send(chat_id, self.vtext("saved").replace("{text}", row["Transcript"][:1500]))
        else:
            self.send(chat_id, self.vtext("later"))
        note = f"🎙 {who} · {user} · {row['Seconds']} s\n" + (row["Transcript"][:3000] or "(" + row["Status"] + ")")
        for m in self.managers:
            if m != str(chat_id):
                try:
                    self.send(int(m), note)
                except BotError:
                    pass

    def pulse_paths(self, day=None):
        d = self.vcfg().get("pulse_dir")
        if not d:
            return None, None
        d = os.path.expanduser(d)
        if not os.path.isabs(d):
            d = os.path.join(os.path.dirname(self.config_path or self.store.state_path), d)
        day = day or datetime.date.today().isoformat()
        return os.path.join(d, f"pulse_{day}.txt"), os.path.join(d, f"pulse_{day}.m4a")

    def send_pulse(self, force=False, only=None):
        """Read today's summary text aloud and send it to the managers (once a day; /pulse = now)."""
        txt, audio = self.pulse_paths()
        if not txt:
            return only and self.send(only, "Audio summary is off (telegram.voice.pulse_dir).")
        if not os.path.exists(txt):
            return only and self.send(only, "No summary text for today yet — it appears after the morning run.")
        vc = self.vcfg()
        if not os.path.exists(audio) or os.path.getmtime(audio) < os.path.getmtime(txt):
            import voice
            with open(txt, encoding="utf-8") as f:
                voice.tts(f.read(), audio, lang=vc.get("tts_lang", "en"), engine=vc.get("tts_engine", "auto"),
                          voice=vc.get("tts_voice"))
        cap = "🎧 " + (vc.get("pulse_caption") or "Morning summary") + " · " + datetime.date.today().strftime("%d.%m")
        for m in ([str(only)] if only else self.managers):
            try:
                self.api.upload("sendAudio", "audio", audio, chat_id=int(m), caption=cap, title=cap[2:])
            except (BotError, OSError) as e:
                print(f"{now_str()} audio summary → {m}: {e}")
        if not only:
            self.store.state["pulse_sent"] = datetime.date.today().isoformat()
            self.store.save_state()

    def pulse_due(self):
        if not self.vcfg().get("pulse_dir") or self.store.state.get("pulse_sent") == datetime.date.today().isoformat():
            return
        txt, _ = self.pulse_paths()
        if txt and os.path.exists(txt):
            try:
                self.send_pulse()
            except Exception as e:  # noqa: BLE001 — never stop the bot
                print(f"{now_str()} audio summary: {e}")
                self.store.state["pulse_sent"] = datetime.date.today().isoformat()   # do not retry every minute

    def watch_due(self):
        """Channel watch inside the bot: run tg_watch at telegram.watch_times (e.g. ["07:05", "18:40"]).
        A time already passed today and not yet run (Mac was asleep, bot just started) runs now."""
        if not self.config_path or not self.cfg.get("watch_times"):
            return
        now = datetime.datetime.now()
        done = self.store.state.setdefault("watch_done", {})
        for t in self.cfg["watch_times"]:
            hh, mm = (int(x) for x in str(t).split(":"))
            if (now.hour, now.minute) >= (hh, mm) and done.get(str(t)) != now.strftime("%Y-%m-%d"):
                done[str(t)] = now.strftime("%Y-%m-%d")
                self.store.save_state()
                try:
                    from tg_watch import run as watch_run
                    watch_run(self.config_path)
                except Exception as e:  # noqa: BLE001 — the watch must never stop the bot
                    print(f"{now_str()} channel watch: {e}")

    def poll(self, once=False):
        timeout = 0 if once else 50
        while True:
            self.watch_due()
            self.pulse_due()
            self.update_due()
            try:
                ups = self.api.call("getUpdates", offset=self.store.state["offset"], timeout=timeout,
                                    allowed_updates=["message", "callback_query"])
            except (BotError, OSError) as e:
                print(f"{now_str()} getUpdates: {e}")
                if once:
                    return
                time.sleep(15)
                continue
            for u in ups or []:
                self.store.state["offset"] = u["update_id"] + 1
                try:
                    self.handle(u)
                except Exception as e:  # noqa: BLE001 — one bad message must not stop the bot
                    print(f"{now_str()} update {u.get('update_id')}: {e}")
            self.store.save_state()
            if once:
                return


def main():
    ap = argparse.ArgumentParser(description="FLOKTRON Telegram bot")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "config.yaml"))
    ap.add_argument("--flow", default="")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--loop", action="store_true")
    g.add_argument("--once", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--flow-check", action="store_true")
    a = ap.parse_args()
    cfg = load_yaml(a.config).get("telegram") or {}
    flow_path = a.flow or cfg.get("flow") or os.path.join(ROOT, "config", "bot_flow.yaml")
    flow_path = os.path.expanduser(flow_path)
    if not os.path.isabs(flow_path):          # relative to the config file (or to the box without one)
        base = os.path.dirname(os.path.abspath(a.config)) if os.path.exists(a.config) else ROOT
        flow_path = os.path.join(base, flow_path)
    flow = load_yaml(flow_path)
    probs = check_flow(flow)
    if a.flow_check:
        print(f"flow: {flow_path}")
        for sid, st in (flow.get("steps") or {}).items():
            kind = "final" if st.get("final") else f"input:{st.get('input')}" if st.get("input") else \
                f"{len(st.get('buttons') or [])} buttons"
            print(f"  {sid:<18} {kind}")
        print("OK" if not probs else "PROBLEMS:\n  " + "\n  ".join(probs))
        sys.exit(1 if probs else 0)
    if probs:
        sys.exit("Dialog file has problems (run --flow-check):\n  " + "\n  ".join(probs))
    try:
        api = Api(token_from(cfg))
        if a.check:
            me = api.call("getMe")
            print(f"OK — bot @{me.get('username')} ({me.get('first_name')}). Managers: {cfg.get('manager_chat_ids') or 'none yet'}")
            return
        data_dir = os.path.expanduser(cfg.get("data_dir") or DATA)
        if not os.path.isabs(data_dir):
            data_dir = os.path.join(os.path.dirname(os.path.abspath(a.config)), data_dir)
        leads = cfg.get("leads_file") and os.path.expanduser(cfg["leads_file"])
        if cfg.get("channels_file") and not os.path.isabs(os.path.expanduser(cfg["channels_file"])):
            cfg["channels_file"] = os.path.join(os.path.dirname(os.path.abspath(a.config)), cfg["channels_file"])
        cfg["_config_path"] = os.path.abspath(a.config)
        print(f"{now_str()} bot running — data in {data_dir}. Channel watch at {cfg.get('watch_times') or 'off'}. Stop: Ctrl+C")
        Bot(api, flow, cfg, Store(data_dir=data_dir, leads_file=leads)).poll(once=a.once)
    except BotError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    main()
