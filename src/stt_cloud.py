"""
Optional cloud ears: transcribes an audio file via Groq's free-tier hosted
Whisper API instead of loading `faster-whisper` locally.

Only implements `transcribe_file()` (what the web server uses for a browser-
recorded clip) — not `record()`/`listen_for_utterance()`, which are for the
CLI's direct-mic mode and only make sense against a local mic, so the CLI
always uses `src.stt.SpeechToText` regardless of this setting.

Why this exists: on a free cloud box, loading faster-whisper (even the
"small" model) is slow to start and eats RAM. Groq hosts `whisper-large-v3`
for free and returns a transcript in under a second, which keeps a public
demo deployment fast and light. Running Vrox on your own machine still
defaults to fully local, offline Whisper — nothing about that changes.
"""

import logging

import requests

from src.config import settings

log = logging.getLogger("vrox.stt_cloud")

_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class GroqSpeechToText:
    def __init__(self):
        if not settings.groq_api_key:
            raise RuntimeError(
                "VROX_STT_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com/keys and set it as an env var."
            )

    def transcribe_file(self, path: str) -> str:
        with open(path, "rb") as f:
            resp = requests.post(
                _TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files={"file": f},
                data={"model": settings.groq_whisper_model},
                timeout=30,
            )
        resp.raise_for_status()
        text = resp.json().get("text", "").strip()
        log.info("Heard (groq, file): %r", text)
        return text
