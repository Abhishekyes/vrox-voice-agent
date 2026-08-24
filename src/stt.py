"""
Ears: turn microphone audio into text, for free, fully offline.

Concept (simple to explain in an interview):
  1. Record a few seconds of raw audio from the mic with `sounddevice`.
  2. Feed that audio into a local Whisper model (via `faster-whisper`,
     a fast CTranslate2 re-implementation of OpenAI's open-source Whisper).
  3. Whisper is multilingual out of the box, so it transcribes mixed
     Hindi/English speech reasonably well without any extra work from us.

No audio ever leaves the machine — there is no API call, so this part of
the pipeline is permanently free.
"""

import logging

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from src.config import settings

log = logging.getLogger("vrox.stt")

SAMPLE_RATE = 16000  # Whisper expects 16kHz mono audio


class SpeechToText:
    def __init__(self, model_size: str | None = None):
        self.model_size = model_size or settings.whisper_model
        log.info("Loading Whisper model '%s' (first run downloads it once)...", self.model_size)
        # compute_type="int8" keeps this fast and light enough for a normal laptop CPU.
        self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

    def record(self, seconds: float = 5.0) -> np.ndarray:
        """Record `seconds` of mono audio from the default microphone."""
        log.info("Listening for %.1fs...", seconds)
        audio = sd.rec(
            int(seconds * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        return audio.flatten()

    def transcribe(self, audio: np.ndarray) -> str:
        """Run Whisper on an in-memory audio array and return the recognized text."""
        segments, _info = self._model.transcribe(
            audio,
            language=None,  # let Whisper auto-detect Hindi vs English per utterance
            vad_filter=True,  # skip silence, trims latency
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        log.info("Heard: %r", text)
        return text

    def listen_once(self, seconds: float = 5.0) -> str:
        """Convenience wrapper: record then transcribe in one call."""
        audio = self.record(seconds)
        return self.transcribe(audio)

    def listen_for_utterance(
        self,
        max_duration: float = 12.0,
        silence_duration: float = 0.9,
        silence_rms: float = 0.012,
    ) -> np.ndarray:
        """
        Hands-free listening: no button, no Enter key. This streams the mic
        continuously in small blocks, waits quietly until it hears volume
        rise above a "someone's talking" threshold, keeps recording while
        that continues, and stops automatically once there's been silence
        for `silence_duration` seconds (or `max_duration` is reached as a
        safety cap). This is what makes the CLI feel like "just start
        talking" instead of "press a button every turn."

        This is a simple energy-based Voice Activity Detector (VAD) — no
        ML model needed, just RMS volume thresholding on short blocks. It's
        deliberately basic (a good, honest thing to say in an interview):
        good enough for a normal quiet room, not tuned for noisy places.
        """
        block_duration = 0.05  # 50ms blocks
        block_size = int(SAMPLE_RATE * block_duration)
        silence_blocks_needed = max(1, int(silence_duration / block_duration))
        max_blocks = int(max_duration / block_duration)

        recorded: list[np.ndarray] = []
        silence_run = 0
        started = False
        blocks_recorded = 0

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=block_size) as stream:
            while True:
                block, _overflowed = stream.read(block_size)
                volume = float(np.sqrt(np.mean(np.square(block))))

                if not started:
                    if volume > silence_rms:
                        started = True
                        recorded.append(block.copy())
                        blocks_recorded += 1
                    continue

                recorded.append(block.copy())
                blocks_recorded += 1
                silence_run = silence_run + 1 if volume < silence_rms else 0

                if silence_run >= silence_blocks_needed or blocks_recorded >= max_blocks:
                    break

        if not recorded:
            return np.array([], dtype="float32")
        return np.concatenate(recorded).flatten()

    def transcribe_file(self, path: str) -> str:
        """
        Transcribe an audio file from disk (used by the web server, which
        receives a recorded clip from the browser's MediaRecorder API —
        e.g. webm/opus — instead of a raw mic stream).
        """
        segments, _info = self._model.transcribe(path, language=None, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        log.info("Heard (file): %r", text)
        return text
