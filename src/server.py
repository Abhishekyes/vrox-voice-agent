"""
LAN web server: talk to Vrox from your phone or any other device on the
same WiFi network as your PC.

Concept (simple client-server architecture):
    Browser (any device, same WiFi)
        -> records mic audio (MediaRecorder API)
        -> POST /api/talk  (audio blob)
    FastAPI server (runs on your PC, where Ollama/Whisper/system-control live)
        -> transcribes audio (Whisper)
        -> routes intent + executes system actions ON THE HOST PC
           (opening apps only ever happens on the machine running this
           server — that's intentional: the phone is a remote control,
           the PC is what actually gets controlled)
        -> gets an LLM reply
        -> synthesizes speech
        -> returns { transcript, reply, audio_base64 } as JSON
    Browser
        -> plays the returned audio, shows the transcript/reply as text

Run with:
    uvicorn src.server:app --host 0.0.0.0 --port 8000
Then, from any device on the same WiFi:
    http://<this-pc's-LAN-IP>:8000
"""

import base64
import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.pipeline import VroxPipeline
from src.tts import TextToSpeech

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
log = logging.getLogger("vrox.server")

app = FastAPI(title="Vrox Voice Assistant")

# CORS wide open on purpose: this is meant to be reached from other devices
# (phone, tablet) on your own home WiFi, not exposed to the public internet.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_web_dir = Path(__file__).resolve().parent.parent / "web"

# Components are created once at startup and reused across requests — the
# Whisper/LLM model load is the slow part, so we pay that cost exactly once.
# Typed loosely on purpose: this holds either the local implementation or the
# Groq-backed one, chosen by VROX_STT_PROVIDER / VROX_LLM_PROVIDER (see
# src/config.py). Only the provider actually selected gets imported, so a
# cloud deployment (VROX_STT_PROVIDER=groq) never pulls in faster-whisper /
# sounddevice, and a local run never needs a Groq key.
_stt = None
_tts: TextToSpeech | None = None
_pipeline: VroxPipeline | None = None


@app.on_event("startup")
def _load_models() -> None:
    global _stt, _tts, _pipeline
    log.info("Loading Vrox's brain, ears, and voice (stt=%s, llm=%s)...", settings.stt_provider, settings.llm_provider)

    if settings.stt_provider == "groq":
        from src.stt_cloud import GroqSpeechToText

        _stt = GroqSpeechToText()
    else:
        from src.stt import SpeechToText

        _stt = SpeechToText()

    _tts = TextToSpeech()
    _pipeline = VroxPipeline()
    log.info("Vrox is ready and listening on the network.")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_web_dir / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/talk")
async def talk(audio: UploadFile = File(...)) -> JSONResponse:
    """
    Accepts a recorded audio clip (webm/opus from the browser), transcribes
    it, runs it through the pipeline, and returns the transcript + reply
    text + a base64-encoded mp3 of the spoken reply.
    """
    assert _stt and _tts and _pipeline, "server not fully started yet"

    suffix = Path(audio.filename or "clip.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        clip_path = tmp.name

    try:
        transcript = _stt.transcribe_file(clip_path)
    finally:
        Path(clip_path).unlink(missing_ok=True)

    if not transcript:
        return JSONResponse({"transcript": "", "reply": "Kuch suna nahi, dobara try karo?", "audio_base64": ""})

    reply = _pipeline.handle_text(transcript)

    audio_b64 = ""
    audio_path = _tts.synthesize_to_file(reply)
    if audio_path:
        audio_b64 = base64.b64encode(Path(audio_path).read_bytes()).decode("ascii")
        Path(audio_path).unlink(missing_ok=True)

    return JSONResponse({"transcript": transcript, "reply": reply, "audio_base64": audio_b64})


@app.post("/api/chat")
async def chat(payload: dict) -> JSONResponse:
    """Text-only variant of /api/talk, handy for testing without a microphone."""
    assert _pipeline and _tts, "server not fully started yet"
    text = (payload.get("text") or "").strip()
    if not text:
        return JSONResponse({"reply": "", "audio_base64": ""})

    reply = _pipeline.handle_text(text)
    audio_b64 = ""
    audio_path = _tts.synthesize_to_file(reply)
    if audio_path:
        audio_b64 = base64.b64encode(Path(audio_path).read_bytes()).decode("ascii")
        Path(audio_path).unlink(missing_ok=True)

    return JSONResponse({"reply": reply, "audio_base64": audio_b64})


# Serve any static assets (css/js) placed alongside index.html.
app.mount("/static", StaticFiles(directory=str(_web_dir)), name="static")
