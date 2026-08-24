"""
Central place for all settings.

Keeping every tunable value in one small file (instead of scattered across
modules) is a simple, interview-friendly design choice: "single source of
truth for configuration, loaded once from environment variables."
"""

import os
from dataclasses import dataclass

# Loads variables from a local .env file if python-dotenv is installed and
# a .env exists. This is optional — plain environment variables work too.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    # --- Brain (LLM) ---
    llm_model: str = os.getenv("VROX_LLM_MODEL", "qwen2.5:7b-instruct")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # --- Ears (STT) ---
    whisper_model: str = os.getenv("VROX_WHISPER_MODEL", "small")

    # --- Voice (TTS) ---
    tts_engine: str = os.getenv("VROX_TTS_ENGINE", "edge")  # "edge" or "offline"
    tts_voice: str = os.getenv("VROX_TTS_VOICE", "en-IN-PrabhatNeural")
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "")

    # --- LAN server ---
    server_host: str = os.getenv("VROX_SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("VROX_SERVER_PORT", "8000"))

    # --- Personality ---
    assistant_name: str = os.getenv("VROX_NAME", "Vrox")


settings = Settings()


SYSTEM_PROMPT = f"""You are {settings.assistant_name}, a warm but grounded voice companion —
picture a friendly senior mentor or interviewer: calm, deep, measured, easy
to trust, never hyper or bubbly. Talking to you should feel like talking to
a friend who also happens to carry a bit of quiet authority. Follow these
rules:

1. Speak naturally in whichever mix of Hindi and English (Hinglish) the user
   leans towards. Freely code-switch mid-sentence the way real bilingual
   friends do in India — do not force pure Hindi or pure English if the
   user mixes languages.
2. Keep replies short and conversational (1-3 sentences) unless the user
   clearly wants a longer, detailed answer. This is a spoken conversation,
   not an essay.
3. Keep the tone friendly but measured and grounded — a calm, reassuring
   "heavy" presence rather than high-energy or overly cheerful. Use casual
   acknowledgements naturally ("haan", "bilkul", "samajh gaya", "got it",
   "dekho") the way a real person would — but don't overdo it or sound
   scripted.
4. Never say things like "As an AI language model...". You are simply
   {settings.assistant_name}, a helpful friend who happens to also be able to
   control the user's computer (open apps, play videos/songs, browse) when
   asked.
5. If the user's message was actually a system command (open an app, play a
   video, search something, close a window), you will be told the command
   already ran — just react to it naturally and briefly, like a friend
   confirming "Done, khol diya!" rather than re-explaining it.
"""
