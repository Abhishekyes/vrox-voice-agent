"""
Hands: actually perform the system-control actions the intent router decided on.

Design: one small function per action, each cross-platform via a runtime
`platform.system()` check. This keeps the "how do I open Chrome on Windows
vs Mac vs Linux" complexity in exactly one place, so the rest of the app
never has to think about the OS.
"""

import logging
import platform
import subprocess
import webbrowser
from urllib.parse import quote_plus

import psutil

from src.intent_router import Command, Intent

log = logging.getLogger("vrox.actions")

OS_NAME = platform.system()  # "Windows", "Darwin" (macOS), or "Linux"

# Per-OS launch commands for known apps. `webbrowser`/`open`/`xdg-open` cover
# most of this, but a few apps need an OS-specific binary name.
_APP_LAUNCH = {
    "Windows": {
        "chrome": ["cmd", "/c", "start", "chrome"],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "vscode": ["cmd", "/c", "code"],
        "file_explorer": ["explorer.exe"],
        "terminal": ["cmd", "/c", "start", "cmd"],
        "spotify": ["cmd", "/c", "start", "spotify"],
    },
    "Darwin": {
        "chrome": ["open", "-a", "Google Chrome"],
        "notepad": ["open", "-a", "TextEdit"],
        "calculator": ["open", "-a", "Calculator"],
        "vscode": ["open", "-a", "Visual Studio Code"],
        "file_explorer": ["open", "."],
        "terminal": ["open", "-a", "Terminal"],
        "spotify": ["open", "-a", "Spotify"],
    },
    "Linux": {
        "chrome": ["google-chrome"],
        "notepad": ["gedit"],
        "calculator": ["gnome-calculator"],
        "vscode": ["code"],
        "file_explorer": ["xdg-open", "."],
        "terminal": ["x-terminal-emulator"],
        "spotify": ["spotify"],
    },
}

# Process names used to find & close a running app with psutil.
_PROCESS_NAMES = {
    "Windows": {
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calculator": "CalculatorApp.exe",
        "vscode": "Code.exe",
        "terminal": "cmd.exe",
        "spotify": "Spotify.exe",
    },
    "Darwin": {
        "chrome": "Google Chrome",
        "notepad": "TextEdit",
        "calculator": "Calculator",
        "vscode": "Code",
        "terminal": "Terminal",
        "spotify": "Spotify",
    },
    "Linux": {
        "chrome": "chrome",
        "notepad": "gedit",
        "calculator": "gnome-calculator",
        "vscode": "code",
        "terminal": "x-terminal-emulator",
        "spotify": "spotify",
    },
}


def open_app(name: str) -> str:
    """Launch a known desktop app by its canonical name (see intent_router.APP_ALIASES)."""
    if name == "youtube":
        return open_url("https://www.youtube.com")

    launch_map = _APP_LAUNCH.get(OS_NAME, {})
    cmd = launch_map.get(name)
    if not cmd:
        return f"Mujhe '{name}' kholna nahi aata abhi (not supported on {OS_NAME} yet)."

    try:
        subprocess.Popen(cmd)
        return f"{name} khol diya!"
    except FileNotFoundError:
        log.exception("Failed to launch %s", name)
        return f"'{name}' install nahi lag raha is machine par."


def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open_new_tab(url)
    return "Naya tab khol diya!"


def search_web(query: str) -> str:
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open_new_tab(url)
    return f"'{query}' search kar diya!"


def play_media(query: str) -> str:
    """Search & play the first matching YouTube result — for songs/videos."""
    try:
        import pywhatkit

        pywhatkit.playonyt(query)
        return f"'{query}' bajaa raha hoon YouTube par!"
    except Exception:
        # Fallback: just open a YouTube search — still one click away from playing.
        log.exception("pywhatkit playback failed, falling back to a search tab")
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        webbrowser.open_new_tab(url)
        return f"'{query}' YouTube par search kar diya, click karke chala lo!"


def close_app(name: str) -> str:
    process_map = _PROCESS_NAMES.get(OS_NAME, {})
    proc_name = process_map.get(name, name)

    closed = 0
    for proc in psutil.process_iter(["name"]):
        try:
            if proc_name.lower() in (proc.info["name"] or "").lower():
                proc.terminate()
                closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if closed:
        return f"{name} band kar diya!"
    return f"'{name}' chal hi nahi raha tha lagta hai."


def execute(command: Command) -> str:
    """Dispatch a routed Command to the matching action function."""
    if command.intent is Intent.OPEN_APP:
        return open_app(command.target)
    if command.intent is Intent.OPEN_URL:
        return open_url(command.target)
    if command.intent is Intent.SEARCH_WEB:
        return search_web(command.target)
    if command.intent is Intent.PLAY_MEDIA:
        return play_media(command.target)
    if command.intent is Intent.CLOSE_APP:
        return close_app(command.target)

    raise ValueError(f"execute() called with a non-action intent: {command.intent}")
