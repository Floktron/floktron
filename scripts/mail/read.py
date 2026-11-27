# -*- coding: utf-8 -*-
"""FLOKTRON · mail/read.py — read FLOKTRON replies from a mailbox (IMAP) or from a folder of .eml files.

Providers (config.yaml → mail.provider), same names as mail/send.py:
    proton_bridge  127.0.0.1:1143, STARTTLS, folders "All Mail", "Spam"
    gmail          imap.gmail.com:993, SSL, folders INBOX, "[Gmail]/Spam" — needs an app password
    outlook        outlook.office365.com:993, SSL, folders INBOX, Junk — not working yet (see mail/send.py)
    smtp           any server: set imap_host / imap_port yourself
The password is taken the same way as for sending (environment variable or macOS Keychain).
Certificates are checked the same way as for sending (mail/send.py → tls_context: Bridge only on this computer,
or exactly the exported Bridge certificate in mail.tls_cert).
"""
import datetime
import email
import imaplib
import os
from mail.send import MailError, _password, tls_context, with_hint

PRESETS = {
    "proton_bridge": {"host": "127.0.0.1", "port": 1143, "ssl": False, "self_signed": True,
                      "folders": ['"All Mail"', '"Spam"']},
    "gmail": {"host": "imap.gmail.com", "port": 993, "ssl": True, "self_signed": False,
              "folders": ["INBOX", '"[Gmail]/Spam"']},
    "outlook": {"host": "outlook.office365.com", "port": 993, "ssl": True, "self_signed": False,
                "folders": ["INBOX", "Junk"]},
    "smtp": {"host": "", "port": 993, "ssl": True, "self_signed": False, "folders": ["INBOX"]},
}


def _open(mail_cfg, p, host, port):
    """Log in to the mailbox: SSL or STARTTLS, certificate checked by tls_context (never silently off)."""
    ctx = tls_context(host, p["self_signed"], mail_cfg)   # raises MailError for a non-local Bridge address
    try:
        if p["ssl"]:
            M = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        else:
            M = imaplib.IMAP4(host, port)
            M.starttls(ssl_context=ctx)
        M.login(mail_cfg.get("user") or "", _password(mail_cfg))
    except Exception as e:
        raise MailError(with_hint(f"Cannot open mailbox {host}:{port} — {e}", mail_cfg)) from e
    return M


def from_imap(mail_cfg, days=2, marker="FLOKTRON#"):
    """Yield raw messages (bytes) whose subject contains the marker, from the last `days` days."""
    provider = mail_cfg.get("provider", "smtp")
    p = PRESETS.get(provider)
    if not p:
        raise MailError(f"Unknown mail.provider '{provider}'")
    host = mail_cfg.get("imap_host") or p["host"]
    port = int(mail_cfg.get("imap_port") or p["port"])
    folders = mail_cfg.get("imap_folders") or p["folders"]
    M = _open(mail_cfg, p, host, port)
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    seen = set()
    try:
        for box in folders:
            try:
                if M.select(box, readonly=True)[0] != "OK":
                    continue
                _, data = M.search(None, f'(SINCE {since} SUBJECT "{marker}")')
            except imaplib.IMAP4.error:
                continue
            for num in data[0].split():
                _, md = M.fetch(num, "(RFC822)")
                raw = md[0][1]
                mid = email.message_from_bytes(raw).get("Message-ID", "") or f"{box}-{num.decode()}"
                if mid not in seen:
                    seen.add(mid)
                    yield raw
    finally:
        try:
            M.logout()
        except Exception:
            pass


def all_messages(mail_cfg, folders, days=60):
    """Yield every raw message (sent and received) of the last `days` days from the given folders — read-only
    (BODY.PEEK: messages do not become "read"). Used by followups.py to see sent offers and the answers to them."""
    p = PRESETS.get(mail_cfg.get("provider", "smtp"), PRESETS["smtp"])
    host = mail_cfg.get("imap_host") or p["host"]
    port = int(mail_cfg.get("imap_port") or p["port"])
    M = _open(mail_cfg, p, host, port)
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    try:
        for box in folders:
            try:
                if M.select(box, readonly=True)[0] != "OK":
                    continue
                _, data = M.search(None, f"(SINCE {since})")
            except imaplib.IMAP4.error:
                continue
            for num in data[0].split():
                _, md = M.fetch(num, "(BODY.PEEK[])")
                yield md[0][1]
    finally:
        try:
            M.logout()
        except Exception:
            pass


def from_folder(path):
    """Yield raw messages from .eml files in a folder (for tests, or mail exported by another tool)."""
    for name in sorted(os.listdir(path)):
        if name.lower().endswith(".eml"):
            with open(os.path.join(path, name), "rb") as f:
                yield f.read()


def with_flags(mail_cfg, boxes, days=4, skip_ids=()):
    """Mail watch (scripts/mail_watch.py): yield one dict per message of the last `days` days in the given folders —
    read-only (BODY.PEEK). boxes = [(folder, outgoing), ...]. Keys: outgoing, flags (IMAP flags text), mid,
    refs (In-Reply-To + References text), raw (the whole message; None when its Message-ID is in skip_ids)."""
    p = PRESETS.get(mail_cfg.get("provider", "smtp"), PRESETS["smtp"])
    host = mail_cfg.get("imap_host") or p["host"]
    port = int(mail_cfg.get("imap_port") or p["port"])
    M = _open(mail_cfg, p, host, port)
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    skip = set(skip_ids)
    try:
        for box, outgoing in boxes:
            try:
                if M.select(box, readonly=True)[0] != "OK":
                    continue
                _, data = M.search(None, f"(SINCE {since})")
            except imaplib.IMAP4.error:
                continue
            for num in data[0].split():
                _, hd = M.fetch(num, "(FLAGS BODY.PEEK[HEADER.FIELDS (MESSAGE-ID IN-REPLY-TO REFERENCES)])")
                h = email.message_from_bytes(hd[0][1])
                mid = (h.get("Message-ID", "") or "").strip()
                raw = None
                if mid and mid not in skip:
                    _, md = M.fetch(num, "(BODY.PEEK[])")
                    raw = md[0][1]
                yield dict(outgoing=outgoing, flags=hd[0][0].decode("utf-8", "replace"), mid=mid, raw=raw,
                           refs=(h.get("In-Reply-To", "") or "") + " " + (h.get("References", "") or ""))
    finally:
        try:
            M.logout()
        except Exception:
            pass
