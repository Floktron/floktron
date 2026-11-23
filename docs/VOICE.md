# Voice — reports from the field, a summary for the road

Two optional features of the Telegram bot (`scripts/bot/telegram_bot.py` + `scripts/voice.py`):

1. **Voice reports.** A team member records a voice message to your bot — on a site, in a van, with dirty hands.
   The bot turns it into text on **your** computer, saves it to `data/voice_reports.xlsx` (sheet *Voice*),
   answers the person with what it understood, and sends the text to the manager.
2. **Audio summary.** Your morning AI run writes a short text `pulse_<YYYY-MM-DD>.txt`; the bot reads it aloud and
   sends the audio to the manager in Telegram — listen while driving. `/pulse` sends it again.

## Your voice stays with you
| Step | Default (local, free) | Optional (cloud, your key) |
|---|---|---|
| Speech → text | `faster-whisper` model on your computer (downloads once, "small" ≈ 460 MB) | ElevenLabs Scribe |
| Text → speech | macOS `say` (system voices) · Linux `espeak-ng` | ElevenLabs |
The model is downloaded **once** from huggingface.co (the `faster-whisper` package does it on the first voice message)
and stays on your computer; after that speech → text works without the internet. Only the model comes in — no voice
or text goes out. Want no download at all from FLOKTRON? Copy the model folder yourself and put its path in `stt_model`.
Nothing goes to the cloud unless you set `stt_engine` / `tts_engine` to `elevenlabs` yourself
(key: environment `ELEVENLABS_API_KEY` or macOS Keychain item `FLOKTRON_ELEVENLABS`). See [TRANSPARENCY](TRANSPARENCY.md).

## Switch it on (10 minutes)
1. `pip install faster-whisper` (Mac: `python3 -m pip install --user faster-whisper`).
2. `python3 scripts/voice.py check --lang en` — shows which engines work. On a Mac without a voice for your language:
   System Settings → Accessibility → Spoken Content → System voice → Manage voices.
3. Add to `config/config.yaml` under `telegram:`:
```yaml
  voice:
    enabled: true
    users: {}                 # chat id of a team member: "L5 Logistics" — they write /id to the bot, you add the line
    accept_unknown: false     # strangers get "please write as text"
    max_seconds: 300
    stt_engine: auto          # auto = local; or elevenlabs
    stt_model: small          # tiny | base | small | medium — bigger = more exact, slower; or a folder path
    stt_lang:                 # empty = detect the language of each message
    pulse_dir: "../data/audio"  # where the morning run writes pulse_<date>.txt
    tts_engine: auto          # auto = system voice; or elevenlabs
    tts_lang: en
    pulse_caption: "Morning summary"
    texts: {}                 # your own replies: saved / later / not_team / off ({text} = the transcript)
```
4. Restart the bot. Send it a voice message — it answers with the text. Write `/pulse` to hear today's summary.

## How the morning summary text should be written (for your AI run)
For the ear, not the eye: 180–260 words (≈ 1.5–2 minutes), short sentences, no links, emoji, tables or codes
("L5" → "ray five, logistics"). Order: greeting with the date → is everything working → today → yesterday →
mail and voice reports → what needs a decision → one sentence "the main thing today". No personal data, no prices,
no text of other people's messages.

## Good to know
- Voice messages up to `max_seconds` (default 5 min). The original audio is kept in `data/voice/`.
- If the text cannot be made (engine missing), the file is kept and the row says *not transcribed* — nothing is lost.
- Accuracy is best with the `small` model or bigger; on Apple silicon `faster-whisper` runs on the CPU, a 30-second message takes a few seconds.
- Tests: `tests/test_voice.py` (no network, fake engines).
