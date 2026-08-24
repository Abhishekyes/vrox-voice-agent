#!/usr/bin/env python3
"""
The simplest way to talk to Vrox: run this directly on your PC.

This is fully hands-free by default — no button, no pressing Enter. Vrox
listens continuously in the background, automatically detects when you
start and stop talking (simple volume-based voice detection in
src/stt.py's `listen_for_utterance`), transcribes it, thinks, (maybe)
acts, and replies out loud — then goes right back to listening. Just
start talking whenever you're ready.

Usage:
    python vrox_cli.py

Press Ctrl+C to quit.
"""

import logging
import sys

from src.pipeline import VroxPipeline
from src.stt import SpeechToText
from src.tts import TextToSpeech

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(name)s: %(message)s")
log = logging.getLogger("vrox.cli")

STOP_PHRASES = ("vrox band karo", "stop listening", "band ho jao", "bye vrox")


def main() -> None:
    print("Vrox is starting up... (loading models, this can take a moment the first time)")
    stt = SpeechToText()
    tts = TextToSpeech()
    pipeline = VroxPipeline()

    print("\nVrox is ready and listening — just start talking whenever you like.")
    print("(Say 'stop listening', or press Ctrl+C, to quit.)\n")

    try:
        while True:
            audio = stt.listen_for_utterance()
            if audio.size == 0:
                continue

            heard = stt.transcribe(audio)
            if not heard:
                continue

            print(f"You said: {heard}")

            if heard.strip().lower() in STOP_PHRASES:
                print("Vrox: Theek hai, bye! 👋")
                tts.speak("Theek hai, bye!")
                break

            reply = pipeline.handle_text(heard)
            print(f"Vrox: {reply}")
            tts.speak(reply)
    except KeyboardInterrupt:
        print("\nBye bye! 👋")
        sys.exit(0)


if __name__ == "__main__":
    main()
