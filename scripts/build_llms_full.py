# -*- coding: utf-8 -*-
"""Build llms-full.txt: everything a chat-only AI assistant needs, in ONE file.
For assistants that cannot open GitHub pages: give them the raw link to llms-full.txt, or paste its text.
Run after changing any of the source files:  python3 scripts/build_llms_full.py"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = ["AGENTS.md", "README.md", "SECURITY.md", "docs/TRANSPARENCY.md", "prompts/00_setup_wizard.md",
           "docs/GMAIL_TEST.md", "docs/TELEGRAM.md", "docs/CALENDAR.md", "docs/MEETINGS.md", "docs/SUPPLY_CHAIN.md", "docs/WEBSITE.md", "docs/INVOICES.md", "docs/SNAPSHOT.md", "docs/DOCUMENTS.md", "docs/FOLLOWUPS.md", "docs/MAIL_WATCH.md", "docs/TASKS_TIDY.md", "docs/GATEWAYS.md", "docs/PROSPECTS.md", "docs/INDUSTRY_PACKS.md", "docs/VOICE.md", "docs/WORKTIME.md", "docs/DASHBOARD.md", "docs/BREATH.md", "docs/LIBRARY.md", "docs/MOVE.md", "docs/UPDATES.md", "prompts/58_update.md", "agents/README.md", "docs/INSTALL.md", "docs/SECURITY_CHECKUP.md", "docs/UNINSTALL.md", "docs/FEEDBACK.md", "LICENSING.md"]
HEAD = """# FLOKTRON — full text for AI assistants (one file)

You are an AI assistant. A person wants to test or set up FLOKTRON. This single file contains everything you need:
the rules (AGENTS.md first), what FLOKTRON is, safety, the setup wizard, the Gmail test, install and removal.
Follow AGENTS.md. FIRST offer the person the two ways (AGENTS.md): A — an assistant that works on their
computer does everything; B — step by step in this chat. If you cannot run commands, you are Way B: say so,
mention Way A, then guide the person step by step.
Code files are in the repository https://github.com/floktron/floktron — when the person needs them,
tell them to press Code -> Download ZIP there, or (mode A) clone the repository.
Support: support@floktron.com (subject "FLOKTRON") or GitHub Issues.
"""


def version():
    import re
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        m = re.search(r"Version (\d+\.\d+\.\d+)", f.read())
    return m.group(1) if m else "?"


def build():
    parts = [HEAD + f"Version of this text: {version()}. If a search result, a cached page or the person mentions a newer version,\n"
             "download this file again: https://raw.githubusercontent.com/floktron/floktron/main/llms-full.txt\n"]
    for rel in SOURCES:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            parts.append(f"\n\n===== FILE: {rel} =====\n\n" + f.read().strip() + "\n")
    return "".join(parts)


START_HEAD = """# Start FLOKTRON with any AI assistant

1. Press the **copy** icon in the top-right corner of the grey box below.
2. Open your AI assistant (ChatGPT, Claude, Gemini, Copilot, Leo, Perplexity…) — on the computer or the phone.
3. Paste and send. The assistant explains the two ways to set FLOKTRON up and guides you.

"""


def build_shipped():
    """SHA-256 of every shipped file in prompts/ and agents/ — scripts/move.py packs only the company's own changes."""
    import hashlib
    import json
    out = {}
    for top in ("prompts", "agents"):
        for d, dirs, files in os.walk(os.path.join(ROOT, top)):
            dirs[:] = sorted(x for x in dirs if x != "__pycache__")
            for f in sorted(files):
                p = os.path.join(d, f)
                with open(p, "rb") as fh:  # line ends as in the repository: a Windows checkout (CRLF) is not "changed"
                    out[os.path.relpath(p, ROOT).replace(os.sep, "/")] = hashlib.sha256(
                        fh.read().replace(b"\r\n", b"\n")).hexdigest()
    return json.dumps(dict(sorted(out.items())), indent=1) + "\n"


def build_start():
    return START_HEAD + "~~~~text\n" + build() + "~~~~\n"


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    with open(os.path.join(ROOT, "llms-full.txt"), "w", encoding="utf-8") as f:
        f.write(build())
    with open(os.path.join(ROOT, "START.md"), "w", encoding="utf-8") as f:
        f.write(build_start())
    with open(os.path.join(ROOT, "templates", "shipped_prompts.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(build_shipped())
    print("llms-full.txt, START.md and templates/shipped_prompts.json written")
