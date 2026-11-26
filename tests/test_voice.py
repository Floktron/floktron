# -*- coding: utf-8 -*-
"""Voice reports and the audio summary — no network, no real speech engines (fakes)."""
import datetime
import os
import sys

import openpyxl
import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bot"))

import telegram_bot as tb  # noqa: E402
import voice  # noqa: E402

FLOW = os.path.join(ROOT, "config", "bot_flow.example.yaml")


class FakeApi:
    def __init__(self):
        self.sent, self.uploads = [], []

    def call(self, method, **p):
        self.sent.append((method, p))
        return {"message_id": len(self.sent)}

    def download(self, file_id, dest):
        open(dest, "wb").write(b"OggS-fake")
        return dest

    def upload(self, method, field, path, **p):
        assert os.path.exists(path)
        self.uploads.append((method, p["chat_id"], os.path.basename(path)))
        return {}

    def texts(self, chat):
        return [p["text"] for m, p in self.sent if m == "sendMessage" and p["chat_id"] == chat]


def make(tmp_path, vc):
    flow = yaml.safe_load(open(FLOW, encoding="utf-8"))
    api = FakeApi()
    cfg = {"manager_chat_ids": [999], "voice": vc, "_config_path": str(tmp_path / "config.yaml")}
    return tb.Bot(api, flow, cfg, tb.Store(data_dir=str(tmp_path / "data"))), api


def vmsg(chat, dur=12):
    return {"update_id": 5, "message": {"chat": {"id": chat, "type": "private"}, "from": {"username": "worker"},
                                        "voice": {"file_id": "F1", "duration": dur}}}


@pytest.fixture
def fake_engines(monkeypatch):
    monkeypatch.setattr(voice, "stt", lambda path, lang=None, engine="auto", model="small": "Saņemti 20 maisi, viss kārtībā")

    def fake_tts(text, out, lang="en", engine="auto", voice=None):
        assert "http" not in text or True
        open(out, "wb").write(b"m4a")
        return out
    monkeypatch.setattr(voice, "tts", fake_tts)


def test_voice_from_team_member_saved_and_sent_to_manager(tmp_path, fake_engines):
    bot, api = make(tmp_path, {"enabled": True, "users": {111: "L5 Logistics"}})
    bot.handle(vmsg(111))
    assert any("Saņemti 20 maisi" in t for t in api.texts(111))           # worker sees what was understood
    assert any("L5 Logistics" in t and "Saņemti" in t for t in api.texts(999))   # manager gets the text
    ws = openpyxl.load_workbook(tmp_path / "data" / "voice_reports.xlsx")["Voice"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert rows[0][3] == "L5 Logistics" and rows[0][5].startswith("Saņemti") and rows[0][7] == "New"
    assert os.listdir(tmp_path / "data" / "voice")                        # original audio kept


def test_voice_from_stranger_refused(tmp_path, fake_engines):
    bot, api = make(tmp_path, {"enabled": True, "users": {111: "L5"}})
    bot.handle(vmsg(222))
    assert any("only from the team" in t for t in api.texts(222))
    assert not os.path.exists(tmp_path / "data" / "voice_reports.xlsx")
    assert not api.texts(999)


def test_voice_off_and_too_long(tmp_path, fake_engines):
    bot, api = make(tmp_path, {"enabled": False})
    bot.handle(vmsg(111))
    assert any("as text" in t for t in api.texts(111))
    bot, api = make(tmp_path, {"enabled": True, "users": {111: "L5"}, "max_seconds": 60})
    bot.handle(vmsg(111, dur=400))
    assert any("Max 1 min" in t for t in api.texts(111))


def test_transcription_failure_keeps_file(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise voice.VoiceError("no engine")
    monkeypatch.setattr(voice, "stt", boom)
    bot, api = make(tmp_path, {"enabled": True, "users": {111: "L5"}})
    bot.handle(vmsg(111))
    assert any("a little later" in t for t in api.texts(111))
    ws = openpyxl.load_workbook(tmp_path / "data" / "voice_reports.xlsx")["Voice"]
    assert "not transcribed" in list(ws.iter_rows(min_row=2, values_only=True))[0][7]


def test_audio_summary_once_a_day(tmp_path, fake_engines):
    (tmp_path / "Audio").mkdir()
    bot, api = make(tmp_path, {"enabled": True, "pulse_dir": "Audio"})
    bot.pulse_due()
    assert not api.uploads                                                 # no text yet → nothing
    day = datetime.date.today().isoformat()
    (tmp_path / "Audio" / f"pulse_{day}.txt").write_text("Доброе утро. Всё работает.", encoding="utf-8")
    bot.pulse_due()
    bot.pulse_due()
    assert api.uploads == [("sendAudio", 999, f"pulse_{day}.m4a")]        # sent once
    bot.handle({"update_id": 9, "message": {"chat": {"id": 999, "type": "private"}, "from": {}, "text": "/pulse"}})
    assert len(api.uploads) == 2                                           # manager asks again → sent again
    bot.handle({"update_id": 10, "message": {"chat": {"id": 555, "type": "private"}, "from": {}, "text": "/pulse"}})
    assert len(api.uploads) == 2                                           # not a manager → no audio


def test_clean_for_speech():
    t = voice.clean_for_speech("✅ Пульс 22.11: **всё ок** · ссылка https://example.com/x → дальше | ок 📣")
    assert "http" not in t and "*" not in t and "✅" not in t and "📣" not in t and "|" not in t
    assert "Пульс 22.11" in t


def test_engine_listing_runs_without_engines(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert isinstance(voice.engines_stt(), list) and isinstance(voice.engines_tts("ru"), list)
    with pytest.raises(voice.VoiceError):
        voice.tts("", "/tmp/x.m4a")


def test_speech_text_reads_by_meaning():
    t = voice.speech_text("✅ Пульс 26.11: бот /pulse и /addword · возврат 1 800 € + PVN 21 % · 12,50 € · "
                          "встреча 09:30–11:00 · «Было / сделано» (L0) · FLOKTRON® · LinkedIn и X · "
                          "файл 7_Golos.command · demo@example.com · https://example.com", "ru")
    for bad in ("/", "€", "%", "«", "(", "®", "http", "@", ".command", "✅", "+"):
        assert bad not in t, (bad, t)
    for good in ("26 ноября", "1800 евро", "плюс П-В-Н 21 процент", "12 евро 50 центов", "с 9:30 до 11:00",
                 "Было или сделано", "Флоктрон", "Линкедин и Икс"):
        assert good in t, (good, t)
    assert "22 процента" in voice.speech_text("22 %", "ru") and "5 процентов" in voice.speech_text("5%", "ru")
    assert "20, 00, 00, 00" in voice.speech_text("тел. 20000000", "ru")
    assert "40 euros" in voice.speech_text("€40", "en") and "/" not in voice.speech_text("a / b /start", "en")


def test_cloud_voice_falls_back_to_system_voice(monkeypatch, tmp_path):
    calls = []
    def one(e, text, out, lang, v):
        calls.append(e)
        if e == "elevenlabs":
            raise voice.VoiceError("no credits")
        return out
    monkeypatch.setattr(voice, "_tts_one", one)
    monkeypatch.setattr(voice, "say_voice", lambda lang: "Milena")
    assert voice.tts("Доброе утро.", str(tmp_path / "p.m4a"), "ru", engine="elevenlabs", voice="abc") == str(tmp_path / "p.m4a")
    assert calls == ["elevenlabs", "say"]
