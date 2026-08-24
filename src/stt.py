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
from math import gcd

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from scipy.signal import resample_poly

from src.config import settings

log = logging.getLogger("vrox.stt")

SAMPLE_RATE = 16000  # Whisper expects 16kHz mono audio


class MicrophoneError(RuntimeError):
    """
    Raised when the microphone can't be opened at all, after trying every
    fallback configuration this module knows about. On Windows this is
    usually either a privacy setting or an unusual audio driver — see the
    message this carries, and try `python check_mic.py` for details.
    """


def _native_input_rate() -> int:
    """Ask the OS what sample rate the default microphone reports as native."""
    try:
        info = sd.query_devices(kind="input")
        rate = int(info["default_samplerate"])
        return rate if rate > 0 else 44100
    except Exception:
        return 44100


def _to_whisper_rate(audio: np.ndarray, native_rate: int) -> np.ndarray:
    """Resample recorded audio from whatever rate it was captured at to Whisper's 16kHz."""
    if native_rate == SAMPLE_RATE or audio.size == 0:
        return audio
    divisor = gcd(native_rate, SAMPLE_RATE)
    up, down = SAMPLE_RATE // divisor, native_rate // divisor
    return resample_poly(audio, up, down).astype("float32")


def _candidate_configs() -> list[tuple[int, str]]:
    """
    A short list of (samplerate, dtype) combinations to try, in order,
    when opening the microphone.

    Why a list instead of one guess: Windows' older MME audio host API is
    notoriously picky, and different laptops reject different
    combinations of sample rate and sample format with the same opaque
    "invalid parameter" error. Rather than getting that error once and
    giving up, we try several combinations that are known to work across
    different machines — the mic's own reported native rate first (most
    likely to succeed), then the two most common physical mic rates, then
    Whisper's own 16kHz, each first as float32 and then as int16 (some
    MME drivers only accept 16-bit integer samples, not floating point).
    """
    native = _native_input_rate()
    rates: list[int] = []
    for rate in (native, 44100, 48000, 16000):
        if rate not in rates:
            rates.append(rate)

    configs = [(rate, "float32") for rate in rates]
    configs += [(rate, "int16") for rate in rates]
    return configs


_MIC_HELP = (
    "Could not open your microphone after trying several configurations.\n"
    "Most likely causes:\n"
    "  1. Windows Settings -> Privacy & security -> Microphone:\n"
    "     make sure 'Microphone access' AND 'Let desktop apps access your\n"
    "     microphone' are both ON.\n"
    "  2. Another app (Zoom/Teams/Discord/a browser call) has the mic locked.\n"
    "  3. No microphone is actually set as your default recording device.\n"
    "For exact details on what's failing, run:  python check_mic.py\n"
    "Then run start_vrox.bat again."
)


def _read_normalized_block(stream: sd.InputStream, block_size: int, dtype: str) -> np.ndarray:
    """Read one block and return it as float32 in [-1, 1], regardless of dtype used to open the stream."""
    block, _overflowed = stream.read(block_size)
    if dtype == "int16":
        return (block.astype("float32") / 32768.0).flatten()
    return block.astype("float32").flatten()


class SpeechToText:
    def __init__(self, model_size: str | None = None):
        self.model_size = model_size or settings.whisper_model
        log.info("Loading Whisper model '%s' (first run downloads it once)...", self.model_size)
        # compute_type="int8" keeps this fast and light enough for a normal laptop CPU.
        self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

    def record(self, seconds: float = 5.0) -> np.ndarray:
        """Record `seconds` of mono audio from the default microphone."""
        last_err: Exception | None = None
        for rate, dtype in _candidate_configs():
            try:
                log.info("Trying to record at %dHz (%s)...", rate, dtype)
                audio = sd.rec(int(seconds * rate), samplerate=rate, channels=1, dtype=dtype)
                sd.wait()
                audio = audio.flatten()
                if dtype == "int16":
                    audio = audio.astype("float32") / 32768.0
                return _to_whisper_rate(audio, rate)
            except sd.PortAudioError as e:
                last_err = e
                continue
        raise MicrophoneError(_MIC_HELP) from last_err

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

        Tries several (samplerate, dtype) configurations in turn (see
        `_candidate_configs`) before giving up, since some Windows audio
        drivers reject specific combinations with an opaque error. Raises
        MicrophoneError only if every configuration fails.
        """
        last_err: Exception | None = None
        for rate, dtype in _candidate_configs():
            try:
                return self._listen_with_config(rate, dtype, max_duration, silence_duration, silence_rms)
            except sd.PortAudioError as e:
                last_err = e
                continue
        raise MicrophoneError(_MIC_HELP) from last_err

    def _listen_with_config(
        self,
        rate: int,
        dtype: str,
        max_duration: float,
        silence_duration: float,
        silence_rms: float,
    ) -> np.ndarray:
        block_duration = 0.05  # 50ms blocks
        block_size = int(rate * block_duration)
        silence_blocks_needed = max(1, int(silence_duration / block_duration))
        max_blocks = int(max_duration / block_duration)

        recorded: list[np.ndarray] = []
        silence_run = 0
        started = False
        blocks_recorded = 0

        with sd.InputStream(samplerate=rate, channels=1, dtype=dtype, blocksize=block_size) as stream:
            while True:
                block = _read_normalized_block(stream, block_size, dtype)
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
        audio = np.concatenate(recorded).flatten()
        return _to_whisper_rate(audio, rate)

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
