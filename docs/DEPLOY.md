# Putting a live demo online (free)

Everything above (`docs/SETUP.md`) is about running Vrox **on your own
machine** — fully offline, $0, forever. This doc is for the separate,
optional thing: a public link you can put in a portfolio/resume so anyone
can talk to Vrox from a browser without installing anything.

## Why this needs a different setup

A free cloud box has no GPU and only a small amount of RAM — not enough to
comfortably run Ollama + a 7B model, or even load `faster-whisper` quickly.
So the hosted demo swaps two components for free hosted APIs instead of
local models:

| Component | Local (your PC) | Hosted demo |
|---|---|---|
| LLM | Ollama, `qwen2.5:7b-instruct` | [Groq](https://console.groq.com) free API, `llama-3.1-8b-instant` |
| STT | local `faster-whisper` | Groq free API, `whisper-large-v3-turbo` |
| TTS | `edge-tts` (free) | same — `edge-tts` (free), unchanged |

Groq's free tier needs an API key but no credit card, and is fast enough
that the demo still feels close to real-time. This is controlled entirely
by two environment variables (`VROX_LLM_PROVIDER`, `VROX_STT_PROVIDER`) —
the code, personality, and everything else is identical to the local
version. See `src/brain_cloud.py` / `src/stt_cloud.py` if you want to read
exactly what changes.

## 1. Get a free Groq API key

1. Go to <https://console.groq.com/keys> and sign up (no card required).
2. Create an API key, copy it.

## 2. Deploy — Hugging Face Spaces (recommended, free, no card)

1. Go to <https://huggingface.co/new-space>.
2. Pick a name (e.g. `vrox-voice-agent`), set **SDK** to **Docker**,
   **visibility** to Public, hardware **CPU basic — free**.
3. Once the Space is created, open its **Settings -> Variables and
   secrets** and add a new **secret**: `GROQ_API_KEY` = the key from step 1.
4. Push this repo's code into the Space. Two ways:
   - Easiest: on the Space page, use **Files -> Add file -> Upload files**
     and drag in the whole project folder.
   - Or with git (the Space is itself a git repo):
     ```bash
     git clone https://huggingface.co/spaces/<your-username>/vrox-voice-agent hf-space
     cp -r vrox-voice-agent/* hf-space/
     cd hf-space
     git add .
     git commit -m "Deploy Vrox"
     git push
     ```
     (You'll be prompted for your Hugging Face username and an access
     token as the password — generate one under your HF account settings.
     That's between you and Hugging Face; nothing to share with anyone
     else.)
5. The Space auto-builds the `Dockerfile` at the repo root. First build
   takes a couple of minutes. When it's done you'll have a public URL like
   `https://<your-username>-vrox-voice-agent.hf.space`.
6. Open it, allow microphone access when the browser asks, and talk.

## 3. Alternative — Render.com free web service

Also free, no card for the free tier, if you'd rather not use Hugging Face:

1. Push this repo to GitHub (already done if you're reading this from the
   repo).
2. On <https://render.com>, **New -> Web Service**, connect the GitHub
   repo, environment **Docker** (it will pick up the `Dockerfile`
   automatically).
3. Add the environment variable `GROQ_API_KEY` under the service's
   **Environment** tab.
4. Deploy. Render assigns a public `onrender.com` URL.

Note: Render's free tier spins the service down after periods of
inactivity, so the first request after a while takes ~30-60s to wake back
up — normal, not a bug.

## Cost check

Both Hugging Face Spaces (CPU basic) and Render's free web service tier are
$0. Groq's free tier is also $0 for the request volume a portfolio demo
gets (a handful to a few hundred conversations a day). If you ever did
exceed a free quota somewhere, the very worst case is the demo stops
responding until the quota resets — no surprise charges, since none of
these require a card on the free tier.

## Keeping the "fully local and free" story intact

Nothing above changes how Vrox behaves when *you* run it locally via
`start_vrox.bat` / `start_vrox.sh` — those still default to Ollama and
local Whisper, no API key needed, no data leaving your machine. The cloud
providers only activate when `VROX_LLM_PROVIDER` / `VROX_STT_PROVIDER` are
explicitly set to `groq`, which only happens inside the Docker image above.
