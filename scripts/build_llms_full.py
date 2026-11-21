# -*- coding: utf-8 -*-
"""Build llms-full.txt: everything a chat-only AI assistant needs, in ONE file.
For assistants that cannot open GitHub pages: give them the raw link to llms-full.txt, or paste its text.
Run after changing any of the source files:  python3 scripts/build_llms_full.py"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = ["AGENTS.md", "README.md", "SECURITY.md", "docs/TRANSPARENCY.md", "prompts/00_setup_wizard.md",
           "docs/GMAIL_TEST.md", "docs/TELEGRAM.md", "docs/CALENDAR.md", "docs/SUPPLY_CHAIN.md", "docs/INSTALL.md", "docs/SECURITY_CHECKUP.md", "docs/UNINSTALL.md", "docs/FEEDBACK.md", "LICENSING.md"]
HEAD = """# FLOKTRON — full text for AI assistants (one file)

You are an AI assistant. A person wants to test or set up FLOKTRON. This single file contains everything you need:
the rules (AGENTS.md first), what FLOKTRON is, safety, the setup wizard, the Gmail test, install and removal.
Follow AGENTS.md. FIRST offer the person the two ways (AGENTS.md): A — an assistant that works on their
computer does everything; B — step by step in this chat. If you cannot run commands, you are Way B: say so,
mention Way A, then guide the person step by step.
Code files are in the repository https://github.com/koagu-element/floktron — when the person needs them,
tell them to press Code -> Download ZIP there, or (mode A) clone the repository.
Support: floktron@koagu.com (subject "FLOKTRON") or GitHub Issues.
"""


def version():
    import re
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        m = re.search(r"Version (\d+\.\d+\.\d+)", f.read())
    return m.group(1) if m else "?"


def build():
    parts = [HEAD + f"Version of this text: {version()}. If a search result, a cached page or the person mentions a newer version,\n"
             "download this file again: https://raw.githubusercontent.com/koagu-element/floktron/main/llms-full.txt\n"]
    for rel in SOURCES:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            parts.append(f"\n\n===== FILE: {rel} =====\n\n" + f.read().strip() + "\n")
    return "".join(parts)


START_HEAD = """# Start FLOKTRON with any AI assistant

1. Press the **copy** icon in the top-right corner of the grey box below.
2. Open your AI assistant (ChatGPT, Claude, Gemini, Copilot, Leo, Perplexity…) — on the computer or the phone.
3. Paste and send. The assistant explains the two ways to set FLOKTRON up and guides you.

"""


def build_start():
    return START_HEAD + "~~~~text\n" + build() + "~~~~\n"


if __name__ == "__main__":
    with open(os.path.join(ROOT, "llms-full.txt"), "w", encoding="utf-8") as f:
        f.write(build())
    with open(os.path.join(ROOT, "START.md"), "w", encoding="utf-8") as f:
        f.write(build_start())
    print("llms-full.txt and START.md written")
