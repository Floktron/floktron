# -*- coding: utf-8 -*-
"""FLOKTRON · voice.py — speech to text (voice reports from the field) and text to speech (audio summary for the road).

Local first: by default nothing leaves your computer.
  Speech → text:  faster-whisper (pip install faster-whisper; the model downloads once, "small" ≈ 460 MB)
                  or openai-whisper; or ElevenLabs Scribe (cloud, your API key) if you choose it.
  Text → speech:  macOS `say` (built in), espeak-ng (Linux), or ElevenLabs (cloud, your API key).
Audio files are converted with macOS `afconvert` or `ffmpeg`, whichever exists.

CLI:
    python3 voice.py check                         # which engines work on this computer
    python3 voice.py stt <audio> [--lang ru]       # print the transcript
    python3 voice.py tts <text.txt> <out.m4a> [--lang ru]
API keys (only for ElevenLabs): environment ELEVENLABS_API_KEY or macOS Keychain item "FLOKTRON_ELEVENLABS".
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid

SAY_VOICES = {"ru": ["Milena", "Yuri"], "en": ["Samantha", "Daniel"], "de": ["Anna"], "lv": [], "lt": [], "et": []}
EL_VOICE = "21m00Tcm4TlvDq8ikWAM"       # default ElevenLabs voice; override with voice.tts_voice
_MODEL = {}


class VoiceError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def clean_for_speech(text):
    """Text that reads well aloud: no links, emoji, markdown marks or table bars."""
    t = re.sub(r"https?://\S+", "", str(text or ""))
    t = re.sub(r"[*_#`>|]+", " ", t)
    t = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️‍]", "", t)
    t = t.replace("·", ",").replace("→", "—")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _key():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"].strip()
    if sys.platform == "darwin":
        r = subprocess.run(["security", "find-generic-password", "-s", "FLOKTRON_ELEVENLABS", "-w"], capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout.strip()
    raise VoiceError("no ElevenLabs key (ELEVENLABS_API_KEY or Keychain FLOKTRON_ELEVENLABS)")


def _multipart(fields, files):
    b = uuid.uuid4().hex
    out = b""
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, (name, data, ctype) in files.items():
        out += (f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\n'
                f"Content-Type: {ctype}\r\n\r\n").encode() + data + b"\r\n"
    return out + f"--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"


def _convert(src, out):
    """Any audio → .m4a (AAC) or .mp3 by the out extension."""
    if os.path.splitext(out)[1].lower() == os.path.splitext(src)[1].lower():
        shutil.copyfile(src, out)
        return out
    if shutil.which("afconvert") and out.lower().endswith(".m4a"):
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", src, out], check=True, capture_output=True)
    elif shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, out], check=True)
    else:
        raise VoiceError("no audio converter (afconvert on Mac, or install ffmpeg)")
    return out


# ---------------------------------------------------------------- speech → text
def engines_stt():
    import importlib.util
    found = [name for mod, name in (("faster_whisper", "faster-whisper"), ("whisper", "openai-whisper"))
             if importlib.util.find_spec(mod)]
    try:
        _key()
        found.append("elevenlabs")
    except VoiceError:
        pass
    return found


def stt(path, lang=None, engine="auto", model="small"):
    """Return the transcript of an audio file (ogg/m4a/mp3/wav). lang=None → detect."""
    order = engines_stt() if engine == "auto" else [engine]
    if engine == "auto":
        order = [e for e in order if e != "elevenlabs"]      # cloud only when chosen explicitly
    if not order:
        raise VoiceError("no speech-to-text engine: pip install faster-whisper (local) or set voice.stt_engine: elevenlabs")
    e = order[0]
    if e == "faster-whisper":
        from faster_whisper import WhisperModel
        m = _MODEL.get(("fw", model)) or _MODEL.setdefault(("fw", model), WhisperModel(model, device="cpu", compute_type="int8"))
        segs, _info = m.transcribe(path, language=lang, beam_size=3, vad_filter=True)
        return " ".join(s.text.strip() for s in segs).strip()
    if e == "openai-whisper":
        import whisper
        m = _MODEL.get(("ow", model)) or _MODEL.setdefault(("ow", model), whisper.load_model(model))
        return m.transcribe(path, language=lang)["text"].strip()
    if e == "elevenlabs":
        with open(path, "rb") as f:
            body, ctype = _multipart({"model_id": "scribe_v1", **({"language_code": lang} if lang else {})},
                                     {"file": (os.path.basename(path), f.read(), "application/octet-stream")})
        req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body,
                                     headers={"xi-api-key": _key(), "Content-Type": ctype})
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode()).get("text", "").strip()
    raise VoiceError(f"unknown speech-to-text engine: {e}")


# ---------------------------------------------------------------- text → speech
def say_voice(lang):
    if not shutil.which("say"):
        return None
    have = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    names = {l.split()[0] for l in have.splitlines() if l.strip()}
    for v in SAY_VOICES.get(lang, []):
        if v in names:
            return v
    loc = {"ru": "ru_RU", "en": "en_", "de": "de_DE", "lv": "lv_LV", "lt": "lt_LT", "et": "et_EE"}.get(lang, lang)
    for l in have.splitlines():
        if loc in l:
            return l.split()[0]
    return None


def engines_tts(lang="ru"):
    found = []
    if say_voice(lang):
        found.append("say")
    if shutil.which("espeak-ng"):
        found.append("espeak-ng")
    try:
        _key()
        found.append("elevenlabs")
    except VoiceError:
        pass
    return found


def tts(text, out, lang="ru", engine="auto", voice=None):
    """Speak `text` into the audio file `out` (.m4a or .mp3). Returns the path."""
    text = clean_for_speech(text)
    if not text:
        raise VoiceError("nothing to say")
    order = engines_tts(lang) if engine == "auto" else [engine]
    if engine == "auto":
        order = [e for e in order if e != "elevenlabs"]
    if not order:
        raise VoiceError(f"no text-to-speech engine for '{lang}': on Mac add a voice in System Settings → "
                         "Accessibility → Spoken Content; on Linux install espeak-ng; or set voice.tts_engine: elevenlabs")
    e = order[0]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write(text)
        if e == "say":
            raw = os.path.join(td, "speech.aiff")
            subprocess.run(["say", "-v", voice or say_voice(lang), "-r", "185", "-o", raw, "-f", src], check=True)
        elif e == "espeak-ng":
            raw = os.path.join(td, "speech.wav")
            subprocess.run(["espeak-ng", "-v", lang, "-s", "160", "-w", raw, "-f", src], check=True)
        elif e == "elevenlabs":
            raw = os.path.join(td, "speech.mp3")
            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice or EL_VOICE}?output_format=mp3_44100_128",
                data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode(),
                headers={"xi-api-key": _key(), "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r, open(raw, "wb") as f:
                f.write(r.read())
        else:
            raise VoiceError(f"unknown text-to-speech engine: {e}")
        return _convert(raw, out)


def check(lang="ru"):
    s, t = engines_stt(), engines_tts(lang)
    print("speech → text:", ", ".join(s) or "none — pip install faster-whisper")
    print(f"text → speech ({lang}):", ", ".join(t) or "none")
    if "say" in t:
        print("  macOS voice:", say_voice(lang))
    print("audio converter:", "afconvert" if shutil.which("afconvert") else "ffmpeg" if shutil.which("ffmpeg") else "none")
    return bool(s) and bool(t)


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    lang = a[a.index("--lang") + 1] if "--lang" in a else None
    a = [x for i, x in enumerate(a) if x != "--lang" and (i == 0 or a[i - 1] != "--lang")]
    if not a or a[0] == "check":
        return 0 if check(lang or "ru") else 1
    if a[0] == "stt" and len(a) > 1:
        print(stt(a[1], lang))
        return 0
    if a[0] == "tts" and len(a) > 2:
        with open(a[1], encoding="utf-8") as f:
            print(tts(f.read(), a[2], lang or "ru"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    import utf8_console  # noqa: F401 — UTF-8 output on any console (Windows code pages)
    sys.exit(main())
