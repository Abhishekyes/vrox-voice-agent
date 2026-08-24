"""
Voice: turn text replies into natural-sounding speech, for free.

Two engines are supported behind one simple interface — a classic
"strategy pattern", easy to explain in an interview:

  * "edge"    -> Microsoft Edge's free neural TTS (via the `edge-tts`
                 package). No API key, no cost, sounds close to a real
                 human, and has good Hindi + Indian-English voices.
                 Needs internet (it calls Microsoft's free public endpoint).

  * "offline" -> `pyttsx3`, which drives your OS's built-in TTS engine
                 (SAPI5 on Windows, NSSpeech on macOS, espeak on Linux).
                 Fully offline, zero network dependency, more robotic.

An optional ElevenLabs backend is included but OFF by default — see
docs/SETUP.md if you deliberately want to spend ElevenLabs free-tier
credits for an even more natural voice.
"""

import asyncio
import logging
import tempfile
from pathlib import Path

from src.config import settings

log = logging.getLogger("vrox.tts")


class TextToSpeech:
    def __init__(self, engine: str | None = None):
        self.engine = engine or settings.tts_engine

    def speak(self, text: str) -> None:
        """Synthesize `text` and play it out loud immediately (used by the CLI)."""
        if not text.strip():
            return

        if self.engine == "edge":
            try:
                self._speak_edge(text)
                return
            except Exception:
                log.warning("edge-tts failed (likely no internet) — falling back to offline TTS.")

        if self.engine == "elevenlabs" and settings.elevenlabs_api_key:
            try:
                self._speak_elevenlabs(text)
                return
            except Exception:
                log.warning("ElevenLabs TTS failed — falling back to offline TTS.")

        self._speak_offline(text)

    def synthesize_to_file(self, text: str) -> str | None:
        """
        Generate speech audio for `text` and return the path to an mp3 file
        (used by the web server, which streams the bytes to the browser
        instead of playing audio on the host machine). Returns None if only
        the offline (device-driven) engine is available, since pyttsx3 can't
        export to a file the same simple way.
        """
        if not text.strip():
            return None

        if self.engine == "edge" or self.engine == "elevenlabs":
            import asyncio
            import tempfile

            if self.engine == "elevenlabs" and settings.elevenlabs_api_key:
                try:
                    return self._synthesize_elevenlabs_to_file(text)
                except Exception:
                    log.warning("ElevenLabs synth failed — falling back to edge-tts.")

            try:
                import edge_tts

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    out_path = tmp.name

                async def _gen():
                    communicate = edge_tts.Communicate(text, settings.tts_voice)
                    await communicate.save(out_path)

                asyncio.run(_gen())
                return out_path
            except Exception:
                log.warning("edge-tts file synth failed — no audio file available.")
                return None

        return None

    def _synthesize_elevenlabs_to_file(self, text: str) -> str:
        import tempfile

        import requests

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
        headers = {"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(resp.content)
            return tmp.name

    # ---- Engines ----

    def _speak_edge(self, text: str) -> None:
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            out_path = tmp.name

        async def _gen():
            communicate = edge_tts.Communicate(text, settings.tts_voice)
            await communicate.save(out_path)

        asyncio.run(_gen())
        self._play(out_path)

    def _speak_offline(self, text: str) -> None:
        import pyttsx3

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

    def _speak_elevenlabs(self, text: str) -> None:
        """Optional premium path. Only runs if ELEVENLABS_API_KEY is set."""
        import requests

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
        headers = {
            "xi-api-key": settings.elevenlabs_api_key,
            "Content-Type": "application/json",
        }
        # eleven_turbo_v2_5 is ElevenLabs' cheapest/fastest multilingual model —
        # it also handles Hindi, keeping credit usage minimal if you opt in.
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(resp.content)
            out_path = tmp.name
        self._play(out_path)

    @staticmethod
    def _play(path: str) -> None:
        import pygame

        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        Path(path).unlink(missing_ok=True)
