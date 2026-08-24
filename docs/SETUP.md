# Setup guide

## 1. Prerequisites

| Tool | Why | Install |
|---|---|---|
| Python 3.10+ | runs the whole app | [python.org](https://python.org) (check "Add to PATH" on Windows) |
| [Ollama](https://ollama.com) | runs the local LLM, free | download the installer for your OS from ollama.com |
| `ffmpeg` | needed by Whisper to decode audio | Windows: `winget install ffmpeg` · Mac: `brew install ffmpeg` · Linux: `sudo apt install ffmpeg` |
| A microphone | for voice input | built-in laptop mic is fine |

## 2. Pull a local LLM model

With Ollama installed and running:

```bash
ollama pull qwen2.5:7b-instruct
```

This downloads once (a few GB) and then runs 100% offline afterwards.
If your machine is lower-spec, `qwen2.5:3b-instruct` or `llama3.2:3b` are
lighter alternatives — set whichever you use in `.env` as `VROX_LLM_MODEL`.

## 3. Set up the Python project

```bash
git clone <your-repo-url>
cd vrox-voice-agent

python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# open .env and adjust VROX_LLM_MODEL if you pulled a different model
```

## 4. Run it

**Simplest — talk directly on your PC:**
```bash
python vrox_cli.py
```
Press Enter, speak for ~5 seconds, listen to the reply, repeat.

**LAN mode — control your PC from your phone:**
```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000
```
Then find your PC's local IP address:
- Windows: `ipconfig` (look for "IPv4 Address")
- Mac/Linux: `ifconfig` or `ip addr` (look for something like `192.168.x.x`)

On your phone (connected to the **same WiFi**), open a browser and go to:
```
http://<that-ip-address>:8000
```
Hold the button, speak, release — Vrox replies with voice + text, and
executes any system command directly on your PC.

## 5. Run the tests

```bash
pytest tests/ -v
ruff check src/ tests/ vrox_cli.py
```

## Cost breakdown

| Component | Default | Cost |
|---|---|---|
| Speech-to-text | local Whisper (`faster-whisper`) | **$0**, runs offline |
| LLM / conversation | local model via Ollama | **$0**, runs offline |
| Text-to-speech | `edge-tts` (Microsoft's free endpoint) | **$0**, needs internet but no key/quota |
| System control | Python stdlib + `psutil`/`pywhatkit` | **$0** |
| Hosting | your own PC, source on GitHub | **$0** |
| **Total** | | **$0 / ₹0** |

### Optional paid upgrade (off by default)

If you want an even more natural-sounding voice, you can opt into
ElevenLabs:

1. Create a free ElevenLabs account (comes with a free monthly character
   quota).
2. Grab your API key and a voice ID.
3. In `.env`, set:
   ```
   VROX_TTS_ENGINE=elevenlabs
   ELEVENLABS_API_KEY=your-key-here
   ELEVENLABS_VOICE_ID=your-voice-id-here
   ```
4. The code already uses `eleven_turbo_v2_5`, ElevenLabs' cheapest/fastest
   multilingual model, and replies are kept short by the personality
   prompt (1-3 sentences) — both of which minimize how many credits each
   turn burns, in case you want to try it during a demo.

If you don't set an API key, Vrox silently stays on the free `edge-tts`
engine — there's no way to accidentally get billed.

## Troubleshooting

- **"Model not found" from Ollama** — make sure `ollama pull <model>` has
  finished, and that the Ollama app/service is running in the background.
- **No sound / mic not detected (CLI mode)** — check your OS's default
  input/output device; `sounddevice` uses whatever your OS considers
  default. Vrox already tries several sample-rate/format combinations
  automatically before giving up (some Windows audio drivers reject the
  "obvious" one), but if it still can't open the mic, run
  `python check_mic.py` for a detailed report of exactly which
  configuration is failing and why — much faster to debug from than a
  bare error message.
- **Phone can't reach the server** — confirm both devices are on the same
  WiFi network (not a guest network that isolates clients), and that your
  PC's firewall allows inbound connections on port 8000.
- **`play_media` doesn't open anything** — `pywhatkit` opens a browser tab
  and can occasionally be blocked by browser popup rules; the fallback in
  `src/actions.py` opens a YouTube search tab instead so you're never left
  with nothing.
