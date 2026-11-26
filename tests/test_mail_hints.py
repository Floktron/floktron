# -*- coding: utf-8 -*-
"""A refused mailbox gets one plain sentence: Outlook is not supported yet, Proton needs a paid plan with Bridge."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from mail import read as mread  # noqa: E402
from mail.send import MailError, Sender, hint, with_hint  # noqa: E402


def test_hint_names_the_way_out():
    assert "Gmail" in hint({"provider": "outlook"}) and "not" in hint({"provider": "outlook"})
    assert "paid Proton plan" in hint({"provider": "proton_bridge"})
    assert hint({"provider": "smtp"}) == "" and hint(None) == ""
    assert with_hint("x", {"provider": "smtp"}) == "x"


def test_refused_outlook_says_why(monkeypatch):
    monkeypatch.setenv("FLOKTRON_MAIL_PASSWORD", "test-only")
    cfg = {"provider": "outlook", "user": "test@example.com", "imap_host": "127.0.0.1", "imap_port": 9,
           "smtp_host": "127.0.0.1", "smtp_port": 9}
    with pytest.raises(MailError) as e:
        list(mread.from_imap(cfg))
    assert "FLOKTRON cannot sign in to Outlook yet" in str(e.value)
    with pytest.raises(MailError) as e:
        with Sender(cfg):
            pass
    assert "FLOKTRON cannot sign in to Outlook yet" in str(e.value)
