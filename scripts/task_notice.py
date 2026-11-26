# -*- coding: utf-8 -*-
"""FLOKTRON · task_notice.py — one task = one Telegram message with two buttons: ✅ done · ⛔ not needed.

Used by mail_watch.py, prospects.py and gateways.py when the notice goes to Telegram (docs/TELEGRAM.md).
A press is caught by the bot (scripts/bot/telegram_bot.py): it writes one line to data/task_actions.jsonl
and the message turns into «✅ Closed · dd.mm hh:mm» (buttons gone). A text reply to the message = ✅ with a comment.
Each script then applies its own kind of presses to its own sheet on its next run (read_actions + its own offset).

    send(cfg, text, kind, key, lang, outbox=None)  → "" or an error text
    info(cfg, text, outbox=None)                   → a summary without buttons (nothing to do)
    read_actions(path, offset, kind)               → (presses of that kind, new offset)

callback_data: fk:<kind>:<key>:<y|n> (Telegram allows 64 bytes). Kinds: mail · prospect · gw.
No text about sheets or columns goes to Telegram: only the fact and the two buttons.
Network: none here — the message goes through the bot's Api (scripts/bot/telegram_bot.py)."""
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

LABELS = {  # kind → (✅, ⛔) per company.language
    "en": {"mail": ("✅ Answered", "⛔ Not needed"), "prospect": ("✅ Add to book", "⛔ Not a fit"), "gw": ("✅ Found", "⛔ Not needed")},
    "lv": {"mail": ("✅ Atbildēju", "⛔ Nav vajadzīgs"), "prospect": ("✅ Uz grāmatu", "⛔ Neder"), "gw": ("✅ Atradu", "⛔ Nav vajadzīgs")},
    "ru": {"mail": ("✅ Ответил", "⛔ Не нужно"), "prospect": ("✅ В книгу", "⛔ Не подходит"), "gw": ("✅ Нашёл", "⛔ Не нужно")},
    "de": {"mail": ("✅ Beantwortet", "⛔ Nicht nötig"), "prospect": ("✅ Ins Buch", "⛔ Passt nicht"), "gw": ("✅ Gefunden", "⛔ Nicht nötig")},
    "et": {"mail": ("✅ Vastasin", "⛔ Pole vaja"), "prospect": ("✅ Raamatusse", "⛔ Ei sobi"), "gw": ("✅ Leidsin", "⛔ Pole vaja")},
    "lt": {"mail": ("✅ Atsakiau", "⛔ Nereikia"), "prospect": ("✅ Į knygą", "⛔ Netinka"), "gw": ("✅ Radau", "⛔ Nereikia")},
}


def via_telegram(cfg, section_cfg=None):
    """True when this module's notice goes to Telegram (its own notify:, else telegram.enabled) — the same rule as mail_watch."""
    how = (section_cfg or {}).get("notify") or ("telegram" if (cfg.get("telegram") or {}).get("enabled") else "mail")
    return how == "telegram"


def key_of(s):
    """Short stable key for long ids (Message-ID)."""
    return hashlib.sha1(str(s).encode("utf-8"), usedforsecurity=False).hexdigest()[:10]


def buttons(kind, key, lang="en"):
    key = re.sub(r"[^A-Za-z0-9_\-]", "", str(key))[:40]
    yes, no = (LABELS.get(lang) or LABELS["en"]).get(kind) or ("✅", "⛔")
    return [[{"text": yes, "callback_data": f"fk:{kind}:{key}:y"}, {"text": no, "callback_data": f"fk:{kind}:{key}:n"}]]


def data_dir(cfg):
    tg = cfg.get("telegram") or {}
    d = os.path.expanduser(tg.get("data_dir") or os.path.join(ROOT, "data"))
    if not os.path.isabs(d):
        d = os.path.join(os.path.dirname(cfg.get("_path") or os.path.join(ROOT, "config", "x")), d)
    return d


def actions_path(cfg):
    return os.path.join(data_dir(cfg), (cfg.get("telegram") or {}).get("actions_file") or "task_actions.jsonl")


def _deliver(cfg, text, markup, outbox):
    if outbox:   # tests and trial runs: a file instead of Telegram
        os.makedirs(outbox, exist_ok=True)
        with open(os.path.join(outbox, "telegram_tasks.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"text": text, "buttons": markup or []}, ensure_ascii=False) + "\n")
        return ""
    tg = cfg.get("telegram") or {}
    ids = [str(x) for x in (tg.get("manager_chat_ids") or [])]
    if not ids:
        return "Telegram: telegram.manager_chat_ids is empty"
    try:
        from bot.telegram_bot import Api, token_from
        api = Api(token_from(tg), timeout=20)
    except Exception as e:  # noqa: BLE001
        return f"Telegram: {e}"[:120]
    for cid in ids:
        p = {"chat_id": cid, "text": text[:3900], "disable_web_page_preview": True}
        if markup:
            p["reply_markup"] = {"inline_keyboard": markup}
        try:
            res = api.call("sendMessage", **p)
        except Exception as e:  # noqa: BLE001
            return f"Telegram: {str(e)[:80]}"
        if markup and isinstance(res, dict) and res.get("message_id"):
            try:   # lets the bot find the task when someone replies with text
                with open(os.path.join(data_dir(cfg), "task_sent.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"chat": cid, "mid": res["message_id"], "y": markup[0][0]["callback_data"]}) + "\n")
            except OSError:
                pass
    return ""


def send(cfg, text, kind, key, lang="en", outbox=None):
    return _deliver(cfg, text, buttons(kind, key, lang), outbox)


def info(cfg, text, outbox=None):
    return _deliver(cfg, text, None, outbox)


def read_actions(path, offset=0, kind=None):
    """New presses after byte offset → (list of dicts, new offset). A half-written last line waits for the next run."""
    if not path or not os.path.exists(path):
        return [], 0
    if offset > os.path.getsize(path):
        offset = 0   # the file was made anew
    with open(path, "rb") as f:
        f.seek(offset)
        raw = f.read()
    end = raw.rfind(b"\n") + 1
    out = []
    for line in raw[:end].decode("utf-8", "replace").splitlines():
        try:
            a = json.loads(line)
        except ValueError:
            continue
        if isinstance(a, dict) and a.get("key") and a.get("ans") in ("y", "n") and (kind is None or a.get("kind") == kind):
            out.append(a)
    return out, offset + end


def note(a):
    """Text for the Comment column: «Telegram 25.11 10:31 ✅ “comment”»."""
    return f"Telegram {a.get('ts', '')}: {'✅' if a.get('ans') == 'y' else '⛔'}" + (f" «{str(a['comment'])[:200]}»" if a.get("comment") else "")
