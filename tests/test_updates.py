# -*- coding: utf-8 -*-
"""New-version check — offline, TEST · FICTIONAL releases (tests/fixtures/updates/releases.json), Demo SIA."""
import json
import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bot"))

import update_check as uc  # noqa: E402

REL = os.path.join(ROOT, "tests", "fixtures", "updates", "releases.json")


def cfg(tmp_path, **over):
    c = {"company": {"name": "Demo SIA", "language": "en"},
         "mail": {"manager_address": ""},       # no mail in tests: the bot notice is the delivered channel
         "telegram": {"enabled": True}}
    c.update(over)
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(c), encoding="utf-8")
    return str(p)


def run(tmp_path, *extra, current="0.27.2", c=None):
    return uc.main(["--config", c or cfg(tmp_path), "--data", str(tmp_path / "data"), "--releases", REL,
                    "--current", current, *extra])


def state(tmp_path, name="update_state.json"):
    p = tmp_path / "data" / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def test_local_version_is_changelog_head():
    assert uc.vtuple(uc.local_version()) is not None


def test_newer_releases_sorted_no_drafts():
    news = uc.newer_releases(json.load(open(REL, encoding="utf-8")), "0.27.2")
    assert [n["version"] for n in news] == ["0.29.0", "0.28.0"]      # draft 0.30.0 and older 0.27.2 left out


def test_points_short_and_plain():
    n = uc.newer_releases(json.load(open(REL, encoding="utf-8")), "0.28.0")[0]
    assert len(n["points"]) == uc.MAX_POINTS
    assert "**" not in n["points"][0] and "https://example.com" not in n["points"][1]


def test_notice_once_per_version(tmp_path):
    run(tmp_path)
    n = state(tmp_path, "update_notice.json")
    assert n["version"] == "0.29.0" and not n["sent"]
    assert "0.27.2" in n["text"] and "update FLOKTRON" in n["text"]
    assert state(tmp_path)["notified"] == "0.29.0"
    (tmp_path / "data" / "update_notice.json").unlink()
    run(tmp_path, "--force")                                          # same version again → no second message
    assert state(tmp_path, "update_notice.json") is None


def test_nothing_when_newest(tmp_path):
    run(tmp_path, current="0.29.0")
    assert state(tmp_path, "update_notice.json") is None
    assert state(tmp_path)["latest"] == "0.29.0"


def test_switched_off(tmp_path):
    run(tmp_path, c=cfg(tmp_path, updates={"check": False}))
    assert state(tmp_path) is None


def test_not_delivered_is_retried(tmp_path):
    run(tmp_path, c=cfg(tmp_path, telegram={"enabled": False}))      # no bot, no mail → nobody was told
    assert "notified" not in state(tmp_path)


def test_offline_never_fails(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")
    monkeypatch.setattr(uc, "fetch_releases", boom)
    assert uc.main(["--config", cfg(tmp_path), "--data", str(tmp_path / "data"), "--force"]) == 0


@pytest.mark.parametrize("lang", sorted(uc.T))
def test_every_language_has_all_texts(lang):
    assert set(uc.T[lang]) == set(uc.T["en"])
    s, text, body = uc.build([dict(version="9.9.9", title="TEST · FICTIONAL", points=["<b>x</b>"])], "1.0.0", lang)
    assert "9.9.9" in s and "<b>x</b>" not in body                   # release text is escaped in the mail


def test_no_support_or_partner_links():
    """Only release news: the message never carries donation, sponsor or partner links."""
    for lang in uc.T:
        _, text, body = uc.build([dict(version="9.9.9", title="t", points=[])], "1.0.0", lang)
        for bad in ("stripe", "donate", "sponsor", "support/", "paypal"):
            assert bad not in (text + body).lower()


def test_bot_passes_notice_once_and_version(tmp_path):
    import telegram_bot as tb

    class Api:
        sent = []

        def call(self, method, **p):
            self.sent.append(p)
            return {"message_id": 1}

    flow = yaml.safe_load(open(os.path.join(ROOT, "config", "bot_flow.example.yaml"), encoding="utf-8"))
    api = Api()
    b = tb.Bot(api, flow, {"manager_chat_ids": [999]}, tb.Store(data_dir=str(tmp_path)))
    (tmp_path / "update_notice.json").write_text(json.dumps(dict(version="0.29.0", text="🆕 TEST · FICTIONAL", sent=False)))
    b.update_due()
    b.update_due()
    assert [p["text"] for p in api.sent].count("🆕 TEST · FICTIONAL") == 1
    b.handle({"update_id": 1, "message": {"chat": {"id": 999, "type": "private"}, "from": {}, "text": "/version"}})
    assert api.sent[-1]["text"].startswith("FLOKTRON ")


def test_support_releases_and_links_left_out():
    rel = [{"tag_name": "v9.0.0", "name": "FLOKTRON 9.0.0 — support the project", "body": "- donate here https://x.y"},
           {"tag_name": "v8.0.0", "name": "FLOKTRON 8.0.0 — TEST · FICTIONAL fix", "body": "- Fixed: see https://x.y now\n- Stripe button"}]
    news = uc.newer_releases(rel, "1.0.0")
    s, text, body = uc.build(news, "1.0.0", "en")
    assert "9.0.0" in s                                   # the newest version is still told
    assert "support the project" not in text and "Stripe" not in text and "x.y" not in text
    assert "TEST · FICTIONAL fix" in text
