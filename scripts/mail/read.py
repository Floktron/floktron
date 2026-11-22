# -*- coding: utf-8 -*-
"""FLOKTRON · mail/read.py — read FLOKTRON replies from a mailbox (IMAP) or from a folder of .eml files.

Providers (config.yaml → mail.provider), same names as mail/send.py:
    proton_bridge  127.0.0.1:1143, STARTTLS, folders "All Mail", "Spam"
    gmail          imap.gmail.com:993, SSL, folders INBOX, "[Gmail]/Spam" — needs an app password
    outlook        outlook.office365.com:993, SSL, folders INBOX, Junk
    smtp           any server: set imap_host / imap_port yourself
The password is taken the same way as for sending (environment variable or macOS Keychain).
"""
import datetime
import email
import imaplib
import os
import ssl

from mail.send import MailError, _password

PRESETS = {
    "proton_bridge": {"host": "127.0.0.1", "port": 1143, "ssl": False, "self_signed": True,
                      "folders": ['"All Mail"', '"Spam"']},
    "gmail": {"host": "imap.gmail.com", "port": 993, "ssl": True, "self_signed": False,
              "folders": ["INBOX", '"[Gmail]/Spam"']},
    "outlook": {"host": "outlook.office365.com", "port": 993, "ssl": True, "self_signed": False,
                "folders": ["INBOX", "Junk"]},
    "smtp": {"host": "", "port": 993, "ssl": True, "self_signed": False, "folders": ["INBOX"]},
}


def from_imap(mail_cfg, days=2, marker="FLOKTRON#"):
    """Yield raw messages (bytes) whose subject contains the marker, from the last `days` days."""
    provider = mail_cfg.get("provider", "smtp")
    p = PRESETS.get(provider)
    if not p:
        raise MailError(f"Unknown mail.provider '{provider}'")
    host = mail_cfg.get("imap_host") or p["host"]
    port = int(mail_cfg.get("imap_port") or p["port"])
    folders = mail_cfg.get("imap_folders") or p["folders"]
    user = mail_cfg.get("user") or ""
    ctx = ssl.create_default_context()
    if p["self_signed"]:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        if p["ssl"]:
            M = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        else:
            M = imaplib.IMAP4(host, port)
            M.starttls(ssl_context=ctx)
        M.login(user, _password(mail_cfg))
    except Exception as e:
        raise MailError(f"Cannot open mailbox {host}:{port} — {e}") from e
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
    ctx = ssl.create_default_context()
    if p["self_signed"]:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        if p["ssl"]:
            M = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        else:
            M = imaplib.IMAP4(host, port)
            M.starttls(ssl_context=ctx)
        M.login(mail_cfg.get("user") or "", _password(mail_cfg))
    except Exception as e:
        raise MailError(f"Cannot open mailbox {host}:{port} — {e}") from e
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
