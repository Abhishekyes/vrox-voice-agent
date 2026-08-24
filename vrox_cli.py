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

There's also a text-only mode for machines with no working microphone
(a bare test VM, a laptop you're just trying the personality/replies on,
etc.) — it skips loading Whisper and the mic entirely, so startup is
faster too. You type instead of speak; Vrox still replies with voice
(via whatever VROX_TTS_ENGINE is set to) and text:

    python vrox_cli.py --text

Press Ctrl+C to quit either mode.
"""

import argparse
import logging
import sys

from src.pipeline import VroxPipeline
from src.tts import TextToSpeech

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(name)s: %(message)s")
log = logging.getLogger("vrox.cli")

STOP_PHRASES = ("vrox band karo", "stop listening", "band ho jao", "bye vrox", "exit", "quit")


def run_text_mode(pipeline: VroxPipeline, tts: TextToSpeech) -> None:
    """No mic, no Whisper — you type, Vrox still replies with voice + text."""
    print("\nVrox is ready (text mode — no microphone used).")
    print("Type a message and press Enter. Type 'exit' or Ctrl+C to quit.\n")

    while True:
        try:
            heard = input("You: ").strip()
        except EOFError:
            break
        if not heard:
            continue

        if heard.lower() in STOP_PHRASES:
            print("Vrox: Theek hai, bye! 👋")
            tts.speak("Theek hai, bye!")
            break

        reply = pipeline.handle_text(heard)
        print(f"Vrox: {reply}")
        tts.speak(reply)


def run_voice_mode(pipeline: VroxPipeline, tts: TextToSpeech) -> None:
    from src.stt import MicrophoneError, SpeechToText

    stt = SpeechToText()
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
    except MicrophoneError as e:
        print(f"\n[Vrox] {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Talk to Vrox — by voice (default) or by typing.")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Text-only mode: no microphone/Whisper needed, type instead of speak.",
    )
    args = parser.parse_args()

    print("Vrox is starting up... (loading models, this can take a moment the first time)")
    tts = TextToSpeech()
    pipeline = VroxPipeline()

    try:
        if args.text:
            run_text_mode(pipeline, tts)
        else:
            run_voice_mode(pipeline, tts)
    except KeyboardInterrupt:
        print("\nBye bye! 👋")
        sys.exit(0)


if __name__ == "__main__":
    main()
