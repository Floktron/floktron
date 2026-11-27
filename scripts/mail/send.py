# -*- coding: utf-8 -*-
"""FLOKTRON · mail/send.py — one way to send mail for every provider.

Providers (config.yaml → mail.provider):
    proton_bridge  Proton Mail Bridge on this computer, 127.0.0.1:1025 — Bridge comes only with a PAID Proton plan;
                   a free Proton account cannot be used (take Gmail instead)
    gmail          smtp.gmail.com:587 — needs an app password (Google account → Security)
    outlook        smtp.office365.com:587 — Outlook.com / Microsoft 365. NOT WORKING YET: Microsoft no longer accepts
                   a password from outside programs; FLOKTRON does not have the Microsoft sign-in (OAuth) yet
    smtp           any other server: set smtp_host and smtp_port yourself

The password is NEVER stored in config.yaml. It is read from:
    1) the environment variable named in mail.password_env (default FLOKTRON_MAIL_PASSWORD), or
    2) macOS Keychain, service name in mail.keychain_service (macOS only).

Certificates. Every server's certificate is checked, with one narrow exception: Proton Mail Bridge runs on THIS computer
and uses its own self-signed certificate. For Bridge the check is relaxed only when the address is this computer
(127.0.0.1, ::1, localhost) — then the connection never leaves the machine. Better still, export Bridge's certificate
(Bridge → Settings → Advanced → Export TLS certificates) and set mail.tls_cert: "path/to/cert.pem": then exactly that
certificate is accepted and nothing else. A Bridge address on another computer without mail.tls_cert is refused.
"""
import ipaddress
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



HINTS = {
    "outlook": "Outlook / Microsoft 365: Microsoft no longer lets outside programs sign in with a password "
               "(Outlook.com since 16.09.2024, Microsoft 365 earlier). FLOKTRON cannot sign in to Outlook yet — "
               "use a separate Gmail mailbox (free, app password) or a paid Proton plan with Bridge.",
    "proton_bridge": "Proton: is Proton Mail Bridge open on this computer? Bridge comes only with a paid Proton plan "
                     "(for example Mail Plus); a free Proton account cannot be used — take a separate Gmail mailbox instead.",
    "gmail": "Gmail: use an app password (2-Step Verification must be on), not the normal password — docs/GMAIL_TEST.md.",
}


def hint(mail_cfg):
    """One plain sentence for the person when the mailbox refuses the connection."""
    return HINTS.get((mail_cfg or {}).get("provider") or "", "")


def with_hint(message, mail_cfg):
    h = hint(mail_cfg)
    return f"{message}. {h}" if h else message


def read_secret(env, service):
    """A secret (password, private calendar link) from an environment variable or the macOS Keychain — never from files."""
    if env and os.environ.get(env):
        return os.environ[env]
    if service and sys.platform == "darwin":
        r = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                           capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout.strip()
    return ""


def _password(mail_cfg):
    env = mail_cfg.get("password_env") or "FLOKTRON_MAIL_PASSWORD"
    service = mail_cfg.get("keychain_service")
    pwd = read_secret(env, service)
    if pwd:
        return pwd
    raise MailError(f"No mail password: set environment variable {env}"
                    + (f" or Keychain item '{service}'" if service else ""))


LOCAL_NAMES = {"localhost", "localhost.localdomain"}


def is_local(host):
    """True only for this computer: a loopback IP or the name localhost. No DNS lookup — a name never counts."""
    h = str(host or "").strip().strip("[]").lower()
    if h in LOCAL_NAMES:
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def tls_context(host, self_signed, mail_cfg):
    """The TLS context for one mail server connection.
    Normal servers: full certificate and host-name check. Proton Bridge (self_signed): only the exported Bridge
    certificate in mail.tls_cert, or — without it — no check, but only for an address on this computer."""
    ctx = ssl.create_default_context()
    if not self_signed:
        return ctx
    cert = (mail_cfg or {}).get("tls_cert") or ""
    if cert:
        if not os.path.isfile(cert):
            raise MailError(f"mail.tls_cert not found: {cert}")
        ctx = ssl.create_default_context(cafile=cert)   # only this certificate is trusted ...
        ctx.check_hostname = False                       # ... Bridge's certificate is not issued for a host name
        return ctx
    if not is_local(host):
        raise MailError(f"Refused: certificate check can be off only for Proton Bridge on this computer (127.0.0.1), "
                        f"not for {host}. Export Bridge's certificate and set mail.tls_cert, or use the local address.")
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE   # local self-signed Bridge; traffic stays on this computer
    return ctx


class Sender:
    """Open once, send many messages, close. Use as: with Sender(cfg) as s: s.send(msg)"""

    def __init__(self, mail_cfg):
        self._cfg = mail_cfg
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
        ctx = tls_context(self.host, self.self_signed, self._cfg)   # Bridge: local only, or its exported certificate
        try:
            self._s = smtplib.SMTP(self.host, self.port, timeout=60)
            self._s.starttls(context=ctx)
            self._s.login(self.user, self._pwd)
        except Exception as e:
            raise MailError(with_hint(f"Cannot connect to {self.host}:{self.port} — {e}", self._cfg)) from e
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
