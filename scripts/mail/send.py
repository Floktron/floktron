# -*- coding: utf-8 -*-
"""FLOKTRON · mail/send.py — one way to send mail for every provider.

Providers (config.yaml → mail.provider):
    proton_bridge  Proton Mail Bridge on this computer (paid Proton plan), 127.0.0.1:1025
    gmail          smtp.gmail.com:587 — needs an app password (Google account → Security)
    outlook        smtp.office365.com:587 — Outlook.com / Microsoft 365
    smtp           any other server: set smtp_host and smtp_port yourself

The password is NEVER stored in config.yaml. It is read from:
    1) the environment variable named in mail.password_env (default FLOKTRON_MAIL_PASSWORD), or
    2) macOS Keychain, service name in mail.keychain_service (macOS only).
"""
import os
import smtplib
import ssl
import subprocess
import sys

PRESETS = {
    "proton_bridge": {"host": "127.0.0.1", "port": 1025, "self_signed": True},
    "gmail": {"host": "smtp.gmail.com", "port": 587, "self_signed": False},
    "outlook": {"host": "smtp.office365.com", "port": 587, "self_signed": False},
    "smtp": {"host": "", "port": 587, "self_signed": False},
}


class MailError(Exception):
    pass


def _password(mail_cfg):
    env = mail_cfg.get("password_env") or "FLOKTRON_MAIL_PASSWORD"
    if os.environ.get(env):
        return os.environ[env]
    service = mail_cfg.get("keychain_service")
    if service and sys.platform == "darwin":
        r = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                           capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout.strip()
    raise MailError(f"No mail password: set environment variable {env}"
                    + (f" or Keychain item '{service}'" if service else ""))


class Sender:
    """Open once, send many messages, close. Use as: with Sender(cfg) as s: s.send(msg)"""

    def __init__(self, mail_cfg):
        provider = mail_cfg.get("provider", "smtp")
        if provider not in PRESETS:
            raise MailError(f"Unknown mail.provider '{provider}'. Use one of: {', '.join(PRESETS)}")
        p = PRESETS[provider]
        self.host = mail_cfg.get("smtp_host") or p["host"]
        self.port = int(mail_cfg.get("smtp_port") or p["port"])
        self.self_signed = p["self_signed"]
        self.user = mail_cfg.get("user") or ""
        self.fallback_from = mail_cfg.get("fallback_from") or self.user
        if not self.host or not self.user:
            raise MailError("mail.smtp_host and mail.user must be set in config.yaml")
        self._pwd = _password(mail_cfg)
        self._s = None

    def __enter__(self):
        ctx = ssl.create_default_context()
        if self.self_signed:  # Proton Bridge uses a local self-signed certificate
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        try:
            self._s = smtplib.SMTP(self.host, self.port, timeout=60)
            self._s.starttls(context=ctx)
            self._s.login(self.user, self._pwd)
        except Exception as e:
            raise MailError(f"Cannot connect to {self.host}:{self.port} — {e}") from e
        return self

    def send(self, msg):
        try:
            self._s.send_message(msg)
        except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
            # some servers refuse a From address that is only an alias — retry from the login address
            if msg["From"] == self.fallback_from:
                raise
            del msg["From"]
            msg["From"] = self.fallback_from
            self._s.send_message(msg)

    def __exit__(self, *exc):
        try:
            self._s.quit()
        except Exception:
            pass
