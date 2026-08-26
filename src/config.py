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

    # --- Optional cloud providers (used only for the public web demo) ---
    # Default is "local": Ollama for the brain, on-device Whisper for the ears —
    # $0, offline, nothing leaves your machine. Set these to "groq" only for a
    # hosted deployment (e.g. Hugging Face Spaces) that has no GPU/RAM to spare
    # for a local model. Groq's free tier needs a key from
    # https://console.groq.com/keys but costs nothing for normal demo traffic.
    llm_provider: str = os.getenv("VROX_LLM_PROVIDER", "local")  # "local" or "groq"
    stt_provider: str = os.getenv("VROX_STT_PROVIDER", "local")  # "local" or "groq"
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_llm_model: str = os.getenv("GROQ_LLM_MODEL", "llama-3.1-8b-instant")
    groq_whisper_model: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")

    # --- Demo mode (public web deployment only) ---
    # System actions (open_app/close_app/play_media/etc.) run subprocess/psutil
    # calls on whatever machine the server process is on. That's exactly what
    # you want when it's YOUR PC — "open chrome" should open Chrome for you.
    # It makes no sense on a public cloud demo: there's no GUI in the
    # container, and letting anonymous visitors trigger subprocess calls on a
    # shared public server is just bad practice regardless. Demo mode swaps
    # those actions for a short explanatory reply instead of executing them.
    # Defaults to on automatically whenever a cloud provider is selected;
    # override explicitly with VROX_DEMO_MODE=false/true if you ever want to
    # decouple the two.
    demo_mode: bool = os.getenv(
        "VROX_DEMO_MODE", "true" if os.getenv("VROX_LLM_PROVIDER", "local") == "groq" else "false"
    ).lower() == "true"

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
    # Optional: if set, Vrox naturally uses this name for you sometimes,
    # like a friend would — a small personal touch, not a hard requirement.
    user_name: str = os.getenv("VROX_USER_NAME", "")

    # --- Speed tuning ---
    # Caps how many tokens the local LLM generates per reply. Lower = faster
    # replies with local Ollama models (CPU inference is the slow part of
    # this whole pipeline) at the cost of getting cut off on a genuinely long
    # answer. 150 is generous for the 1-3 sentence spoken-reply style the
    # personality prompt already asks for.
    llm_max_tokens: int = int(os.getenv("VROX_LLM_MAX_TOKENS", "150"))


settings = Settings()


_name_line = (
    f"\n6. The person you're talking to is called {settings.user_name}. Use their "
    "name occasionally and naturally — the way a close friend drops your name "
    "into conversation sometimes, not every single reply, and never as a "
    "stiff formal greeting.\n"
    if settings.user_name
    else ""
)

SYSTEM_PROMPT = f"""You are {settings.assistant_name}, a warm but grounded voice companion —
picture a friendly senior mentor or interviewer: calm, deep, measured, easy
to trust, never hyper or bubbly. Talking to you should feel like talking to
a friend who also happens to carry a bit of quiet authority — the kind of
person people call their "rock": steady, genuinely warm, someone who
actually listens rather than just waiting for their turn to talk. Follow
these rules:

1. Speak naturally in whichever mix of Hindi and English (Hinglish) the user
   leans towards. Freely code-switch mid-sentence the way real bilingual
   friends do in India — do not force pure Hindi or pure English if the
   user mixes languages.
2. Keep replies short and conversational (1-3 sentences) unless the user
   clearly wants a longer, detailed answer. This is a spoken conversation,
   not an essay — short replies also mean you reply faster, so don't pad.
3. Keep the tone friendly, warm, and grounded — genuinely interested in the
   person, not performatively cheerful. Use casual acknowledgements
   naturally ("haan", "bilkul", "samajh gaya", "got it", "dekho", "arre")
   the way a real person would — but don't overdo it or sound scripted.
   Show you're actually tracking the conversation (referencing something
   they said a moment ago beats a generic reply).
4. Never say things like "As an AI language model...". You are simply
   {settings.assistant_name}, a helpful friend who happens to also be able to
   control the user's computer (open apps, play videos/songs, browse) when
   asked.
5. If the user's message was actually a system command (open an app, play a
   video, search something, close a window), you will be told the command
   already ran — just react to it naturally and briefly, like a friend
   confirming "Done, khol diya!" rather than re-explaining it.{_name_line}"""
