# -*- coding: utf-8 -*-
"""FLOKTRON · secret_store.py — one place to keep a secret (the Telegram bot token first) in the system store.

Where a secret is read from, in this order:
    1. an environment variable (telegram.token_env, default FLOKTRON_TG_TOKEN) — servers, tests, a quick try;
    2. macOS Keychain (`security`, the tool every Mac has);
    3. the `keyring` package, if installed — Windows Credential Manager, Linux Secret Service (GNOME Keyring / KWallet),
       macOS Keychain;
    4. Linux `secret-tool` (libsecret), if installed.
Never from a file. FLOKTRON writes no secret to config.yaml, logs, backups or git.

    get(service, account="floktron", env=None)   → the secret or ""
    put(service, secret, account="floktron")     → "" when saved, else what went wrong (never the secret itself)
    where(service, account="floktron")           → name of the store that holds it ("" = none)
    redact(text, *secrets)                        → the text with Telegram tokens and the given secrets hidden

Command line (the value is typed hidden, never shown, never stored in shell history):
    python3 scripts/secret_store.py set FLOKTRON_TG_BOT
    python3 scripts/secret_store.py where FLOKTRON_TG_BOT
"""
import getpass
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists, never a shell
import sys

TG_TOKEN_RX = re.compile(r"(?<!\d)\d{6,12}:[A-Za-z0-9_-]{30,}")   # what @BotFather hands out: <bot id>:<35 characters>
DEFAULT_ACCOUNT = "floktron"


def _run(args, stdin=None):
    try:
        return subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=20)  # nosec B603
    except (OSError, subprocess.SubprocessError):
        return None


def _keyring():
    try:
        import keyring  # optional package: pip install keyring
        return keyring
    except Exception:  # noqa: BLE001 — not installed or no backend
        return None


def get(service, account=DEFAULT_ACCOUNT, env=None):
    """The secret from the first store that has it, else ''."""
    if env and os.environ.get(env, "").strip():
        return os.environ[env].strip()
    if not service:
        return ""
    if sys.platform == "darwin" and shutil.which("security"):
        r = _run(["security", "find-generic-password", "-s", service, "-w"])
        if r and r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    kr = _keyring()
    if kr:
        try:
            v = kr.get_password(service, account)
            if v:
                return v.strip()
        except Exception:  # noqa: BLE001 — a locked or missing backend is not an error here
            pass
    if sys.platform.startswith("linux") and shutil.which("secret-tool"):
        r = _run(["secret-tool", "lookup", "service", service, "account", account])
        if r and r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return ""


def where(service, account=DEFAULT_ACCOUNT, env=None):
    """Which store answers for this secret — for --check and the docs, never the value."""
    if env and os.environ.get(env, "").strip():
        return f"environment variable {env}"
    if sys.platform == "darwin" and shutil.which("security"):
        r = _run(["security", "find-generic-password", "-s", service])
        if r and r.returncode == 0:
            return f"macOS Keychain ({service})"
    kr = _keyring()
    if kr:
        try:
            if kr.get_password(service, account):
                return f"system keyring ({service})"
        except Exception:  # noqa: BLE001
            pass
    if sys.platform.startswith("linux") and shutil.which("secret-tool"):
        r = _run(["secret-tool", "lookup", "service", service, "account", account])
        if r and r.returncode == 0 and r.stdout.strip():
            return f"Secret Service ({service})"
    return ""


def put(service, secret, account=DEFAULT_ACCOUNT):
    """Save (or replace) the secret in the system store. '' = saved."""
    secret = (secret or "").strip()
    if not service or not secret:
        return "nothing to save"
    if sys.platform == "darwin" and shutil.which("security"):
        # -U replaces an old item. `security -i` reads the command from stdin, so the value never shows up
        # in the process list, a file or the shell history.
        q = lambda s: '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'  # noqa: E731
        r = _run(["security", "-i"], stdin=f"add-generic-password -U -s {q(service)} -a {q(account)} -w {q(secret)}\n")
        if r and r.returncode == 0 and get(service, account) == secret:
            return ""
    kr = _keyring()
    if kr:
        try:
            kr.set_password(service, account, secret)
            return ""
        except Exception as e:  # noqa: BLE001
            err = f"keyring: {type(e).__name__}"
    else:
        err = "no system store found"
    if sys.platform.startswith("linux") and shutil.which("secret-tool"):
        r = _run(["secret-tool", "store", f"--label={service}", "service", service, "account", account], stdin=secret)
        if r and r.returncode == 0:
            return ""
        err = "secret-tool did not save it"
    return (err + " — install the package `keyring` (pip install keyring) or use an environment variable")


def redact(text, *secrets):
    """Hide Telegram tokens (any) and the given secrets in a text that goes to a log or a screen."""
    s = TG_TOKEN_RX.sub(lambda m: m.group(0).split(":")[0] + ":<hidden>", str(text))
    for x in secrets:
        if x and len(str(x)) >= 8:
            s = s.replace(str(x), "<hidden>")
    return s


class RedactingStream:
    """sys.stdout / sys.stderr wrapper: nothing that looks like a bot token reaches the console or the log file."""

    def __init__(self, stream, *secrets):
        self._s, self._secrets = stream, [x for x in secrets if x]

    def write(self, data):
        return self._s.write(redact(data, *self._secrets))

    def __getattr__(self, name):
        return getattr(self._s, name)


def ask_hidden(prompt="Paste the secret and press Enter (nothing is shown): "):
    v1 = getpass.getpass(prompt).strip()
    v2 = getpass.getpass("Once more: ").strip()
    if v1 != v2:
        raise SystemExit("The two entries differ — nothing saved.")
    return v1


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) >= 2 and a[0] == "set":
        err = put(a[1], ask_hidden(), a[2] if len(a) > 2 else DEFAULT_ACCOUNT)
        print(f"✅ Saved: {where(a[1]) or a[1]}" if not err else f"⚠️ {err}")
        return 0 if not err else 1
    if len(a) >= 2 and a[0] == "where":
        w = where(a[1], a[2] if len(a) > 2 else DEFAULT_ACCOUNT)
        print(w or "not found")
        return 0 if w else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
