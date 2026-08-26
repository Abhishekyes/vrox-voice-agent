# Only used for the optional public demo deployment (e.g. Hugging Face
# Spaces or Render) — see docs/DEPLOY.md. Running Vrox yourself normally
# means `start_vrox.bat` / `start_vrox.sh` on your own machine; you never
# need Docker for that.
#
# This image runs the FastAPI LAN/web server (src/server.py) in "cloud"
# mode: VROX_LLM_PROVIDER=groq and VROX_STT_PROVIDER=groq below make it use
# Groq's free hosted API instead of a local Ollama model / local Whisper —
# a free box has no GPU and not much RAM to spare for either. TTS stays
# edge-tts (already free, no key needed). Nothing about running Vrox
# locally changes; those env vars only apply inside this container.

FROM python:3.11-slim

# ffmpeg: decodes the audio clips the browser records (webm/opus).
# libportaudio2: only actually needed if VROX_STT_PROVIDER=local is set on
# top of this image; included so importing src.stt never hard-crashes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV VROX_LLM_PROVIDER=groq \
    VROX_STT_PROVIDER=groq \
    VROX_DEMO_MODE=true \
    PYTHONUNBUFFERED=1

# Hugging Face Spaces expects the app on port 7860; Render/Railway/etc. set
# their own $PORT — this falls back to 7860 when $PORT isn't set.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-7860}"]
