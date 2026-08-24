#!/usr/bin/env python3
"""
Standalone microphone diagnostic for Vrox.

If start_vrox.bat / vrox_cli.py can't open your microphone, run this
directly to see exactly what's available on your machine and which
configuration (if any) actually works:

    python check_mic.py

This doesn't need Ollama or any of Vrox's other pieces — it only touches
`sounddevice`, so it's safe to run even if the rest of setup isn't done
yet.
"""

import sys

import sounddevice as sd


def main() -> None:
    print("=" * 60)
    print("Vrox microphone diagnostic")
    print("=" * 60)

    print("\n--- Host APIs on this machine ---")
    for i, api in enumerate(sd.query_hostapis()):
        print(f"  [{i}] {api['name']}  (default input device index: {api['default_input_device']})")

    print("\n--- All audio devices ---")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        kind = []
        if dev["max_input_channels"] > 0:
            kind.append("INPUT")
        if dev["max_output_channels"] > 0:
            kind.append("output")
        print(f"  [{i}] {dev['name']}  ({'/'.join(kind) or 'n/a'})  "
              f"default rate: {int(dev['default_samplerate'])}Hz")

    try:
        default_in = sd.query_devices(kind="input")
        print(f"\n--- Default input device ---\n  {default_in['name']}  "
              f"(native rate: {int(default_in['default_samplerate'])}Hz)")
    except Exception as e:
        print(f"\n[!] Could not determine a default input device: {e}")
        print("    This usually means Windows has no microphone set as default.")
        print("    Check: Settings -> System -> Sound -> Input")
        sys.exit(1)

    print("\n--- Trying to actually open the microphone ---")
    print("(each line is one attempt; you don't need to do anything, this is silent)\n")

    native_rate = int(default_in["default_samplerate"])
    rates_to_try = []
    for r in (native_rate, 44100, 48000, 16000):
        if r not in rates_to_try:
            rates_to_try.append(r)

    any_success = False
    for rate in rates_to_try:
        for dtype in ("float32", "int16"):
            label = f"  {rate}Hz / {dtype}: "
            try:
                with sd.InputStream(samplerate=rate, channels=1, dtype=dtype, blocksize=int(rate * 0.05)):
                    pass
                print(label + "OK - this configuration works")
                any_success = True
            except Exception as e:
                print(label + f"FAILED - {e}")

    print()
    if any_success:
        print("At least one configuration worked above. If Vrox still fails, "
              "copy this whole output and share it — that pinpoints exactly "
              "which combination to force.")
    else:
        print("Every configuration failed. This points to something outside "
              "the app entirely — likely candidates:")
        print("  - Windows microphone privacy toggles (Settings -> Privacy & "
              "security -> Microphone)")
        print("  - Another app currently holding the microphone exclusively")
        print("  - No physical/default microphone actually configured in Windows")
    print("=" * 60)


if __name__ == "__main__":
    main()
