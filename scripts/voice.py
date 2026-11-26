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


# ---------------------------------------------------------------- text for the ear (0.32)
MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
SAY_AS = {   # how names are SAID (ru); longest first. Unknown Latin words stay as they are.
    "ru": [("FLOKTRON", "Флоктрон"),
           ("LinkedIn", "Линкедин"), ("Instagram", "Инстаграм"), ("Facebook", "Фейсбук"), ("TikTok", "Тикток"),
           ("Telegram", "Телеграм"), ("YouTube", "Ютуб"), ("WhatsApp", "Ватсап"), ("Proton Mail", "Протон"), ("Proton", "Протон"),
           ("iCloud", "Ай-клауд"), ("Gmail", "Джимейл"), ("Google", "Гугл"), ("e-mail", "имейл"), ("email", "имейл"),
           ("Stripe", "Страйп"), ("GitHub", "Гитхаб"), ("Mac", "Мак"), ("iPhone", "Айфон"), ("Excel", "Эксель"),
           ("SIA", "СИА"), ("PVN", "П-В-Н"), ("VAT", "НДС"), ("EUR", "евро"), ("USD", "долларов"), ("PDF", "пэ-дэ-эф"),
           ("AI", "ИИ"), ("OK", "окей"), ("ok", "окей")],
}
CMD_SAY = {"ru": {"pulse": "пульс", "addword": "добавить слово", "delword": "убрать слово", "words": "слова", "client": "клиент",
                  "backup": "резервная копия", "version": "версия", "start": "старт", "id": "айди", "help": "помощь", "add": "добавить"},
           "lv": {"pulse": "pulss", "add": "pievienot", "help": "palīdzība"}}
FILE_WORD = {"ru": "файл", "lv": "fails", "en": "file"}
WORDS = {"ru": {"eur": ("евро", "евро", "евро"), "usd": ("доллар", "доллара", "долларов"), "pct": ("процент", "процента", "процентов"),
                "cent": ("цент", "цента", "центов"), "plus": "плюс", "no": "номер", "and": "и", "from": "с", "to": "до", "or": "или",
                "x": "Икс", "deg": ("градус", "градуса", "градусов")},
         "lv": {"eur": ("eiro",) * 3, "usd": ("dolārs", "dolāri", "dolāru"), "pct": ("procents", "procenti", "procentu"),
                "cent": ("cents", "centi", "centu"), "plus": "plus", "no": "numurs", "and": "un", "from": "no", "to": "līdz", "or": "vai",
                "x": "X", "deg": ("grāds", "grādi", "grādu")},
         "en": {"eur": ("euro", "euros", "euros"), "usd": ("dollar", "dollars", "dollars"), "pct": ("percent",) * 3,
                "cent": ("cent", "cents", "cents"), "plus": "plus", "no": "number", "and": "and", "from": "from", "to": "to", "or": "or",
                "x": "X", "deg": ("degree", "degrees", "degrees")}}


def _plural(n, forms):
    """forms = (1, 2-4, 5+) — Russian rule; fine for lv/en too (they only use 1 vs other)."""
    try:
        n = abs(int(n))
    except ValueError:
        return forms[2]
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def speech_text(text, lang="ru"):
    """Plain text for a voice: no symbols, signs or commands — said by meaning.
    1 800 € → 1800 евро; 12,50 € → 12 евро 50 центов; 21 % → 21 процент; 26.11 → 26 ноября; /pulse → (dropped);
    LinkedIn → Линкедин; «кавычки», (скобки), маркеры списков и эмодзи — убраны."""
    lang = (lang or "ru")[:2].lower()
    W = WORDS.get(lang, WORDS["en"])
    t = str(text or "").replace(" ", " ").replace(" ", " ").replace("️", "")
    t = re.sub(r"https?://\S+|www\.\S+", "", t)
    t = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", "", t)                          # e-mail addresses
    cmd = CMD_SAY.get(lang, {})
    t = re.sub(r"(?<![\w/])/([A-Za-z_]+)\b", lambda m: cmd.get(m.group(1).lower(), m.group(1)), t)   # /pulse → пульс
    fw = FILE_WORD.get(lang, "file")
    t = re.sub(r"(?i)\b(" + fw + r"\s+)?[\w«»\"-]+\.(?:command|py|xlsx|json|yaml|md|txt|pdf|m4a|docx|csv)\b", fw, t)  # names of files
    t = re.sub(r"(?<![\d,.])(\+?\d{3}\s)?([26]\d)(\d\d)(\d\d)(\d\d)(?!\d)",
               lambda m: (m.group(1) or "") + ", ".join(m.group(i) for i in range(2, 6)), t)   # LV phone 20000000 → 20, 00, 00, 00
    t = re.sub(r"(?<=\d)[ ](?=\d{3}\b)", "", t)                                 # 1 800 → 1800
    t = re.sub(r"(?<=\d)[ ](?=\d{3}\b)", "", t)                                 # 1 000 000 (second pass)
    num = r"(\d+)(?:[,.](\d{1,2}))?"

    def money(m, cur):
        whole, cents = m.group(1), m.group(2)
        s = f"{whole} {_plural(whole, W[cur])}"
        if cents and int(cents):
            c = cents if len(cents) == 2 else cents + "0"
            s += f" {int(c)} {_plural(int(c), W['cent'])}"
        return s
    t = re.sub(r"€\s*" + num, lambda m: money(m, "eur"), t)
    t = re.sub(num + r"\s*(?:€|EUR\b|eur\b|евро\b)", lambda m: money(m, "eur"), t)
    t = re.sub(r"\$\s*" + num, lambda m: money(m, "usd"), t)
    t = re.sub(num + r"\s*(?:\$|USD\b)", lambda m: money(m, "usd"), t)
    t = re.sub(r"(\d+)(?:[,.]\d+)?\s*%", lambda m: f"{m.group(0).rstrip('% ').replace('.', ',')} {_plural(m.group(1), W['pct'])}", t)
    t = re.sub(r"(\d+)\s*°\s*C?", lambda m: f"{m.group(1)} {_plural(m.group(1), W['deg'])}", t)
    t = t.replace("€", " " + W["eur"][2] + " ").replace("№", W["no"] + " ").replace("&", " " + W["and"] + " ")
    if lang == "ru":
        def date(m):
            d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
            if not (1 <= d <= 31 and 1 <= mo <= 12):
                return m.group(0)
            return f"{d} {MONTHS_RU[mo - 1]}" + (f" {y} года" if y else "")
        t = re.sub(r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\b(?!\.\d)", date, t)
        t = re.sub(r"\bт\.\s?е\.", "то есть", t)
        t = re.sub(r"\bи т\.\s?д\.", "и так далее", t)
        t = re.sub(r"\bи т\.\s?п\.", "и тому подобное", t)
    t = re.sub(r"\b0(\d):(\d\d)\b", r"\1:\2", t)                                 # 07:40 → 7:40
    t = re.sub(r"(?:\b(?:в|во|at|plkst\.?)\s+)?\b(\d{1,2}(?::\d\d)?)\s*[–—-]\s*(\d{1,2}(?::\d\d)?)\b(?!\.\d)",
               lambda m: f"{W['from']} {m.group(1)} {W['to']} {m.group(2)}", t)  # (в) 10–12 → с 10 до 12
    for a, b in SAY_AS.get(lang, []):
        t = re.sub(r"(?<![\w-])" + re.escape(a) + r"(?!\w)", b, t)
    if lang == "ru":
        t = re.sub(r"(?<![\w-])X(?![\w-])", W["x"], t)                       # соцсеть X
    t = re.sub(r"(?<![\w+])\+(?=\s*\w)", W["plus"] + " ", t)
    t = re.sub(r"[®™©]", "", t)
    t = re.sub(r"(?<=\w)\s*/\s*(?=\w)", f" {W['or']} ", t)                     # было / сделано → было или сделано
    t = re.sub(r"[«»\"“”„]", "", t)
    t = re.sub(r"\s*\(\s*", ", ", t).replace(")", ",")
    t = re.sub(r"(?m)^\s*(?:[-–—•*>]+|\d+[.)])\s+", "", t)                     # list markers
    t = clean_for_speech(t)
    t = re.sub(r"[\\/{}\[\]<>=~^_|#*@]", " ", t)                                # any symbol left — silence
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r",\s*,+", ",", t)
    t = re.sub(r"([,.;:!?])(?=[^\s\d,.;:!?])", r"\1 ", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r",\s*\.", ".", t)
    return "\n".join(x.strip(" ,") for x in t.splitlines()).strip()


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
    text = speech_text(text, lang)            # for the ear: no symbols, € → euro, dates in words, names as said
    if not text:
        raise VoiceError("nothing to say")
    order = engines_tts(lang) if engine == "auto" else [engine]
    if engine == "auto":
        order = [e for e in order if e != "elevenlabs"]
    if not order:
        raise VoiceError(f"no text-to-speech engine for '{lang}': on Mac add a voice in System Settings → "
                         "Accessibility → Spoken Content; on Linux install espeak-ng; or set voice.tts_engine: elevenlabs")
    if engine == "elevenlabs" and say_voice(lang):
        order = order + ["say"]                # cloud voice failed (no key, no credits, offline) → system voice, still on time
    last = None
    for e in order:
        try:
            return _tts_one(e, text, out, lang, None if (engine == "elevenlabs" and e != engine) else voice)
        except Exception as ex:  # noqa: BLE001 — try the next engine
            last = ex
    raise VoiceError(f"text to speech failed: {last}")


def _tts_one(e, text, out, lang, voice):
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
