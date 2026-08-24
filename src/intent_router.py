"""
A tiny, deliberately simple NLU layer.

Design (easy to explain in an interview): rather than sending every single
utterance to the LLM and asking it to decide "should I open an app?", we
run a fast, deterministic, regex/keyword-based router FIRST:

    mic text -> intent_router -> either
                                    (a) a structured Command (open app, play
                                        a video, search, close a window), or
                                    (b) None, meaning "this is just
                                        conversation, send it to the LLM."

Why not let the LLM decide everything?
  * Latency: a regex match is instant; an LLM call is 300ms-2s+.
  * Reliability: "khol do YouTube" or "open chrome" should ALWAYS open
    the app, not depend on the model's mood that day.
  * Simplicity: this is the kind of hand-rolled rule-based NLU that is
    easy to reason about and explain, versus a black-box classifier.

Both Hindi and English trigger words are recognized, since the assistant
is meant to be used in Hinglish.
"""

import re
from dataclasses import dataclass
from enum import Enum


class Intent(Enum):
    OPEN_APP = "open_app"
    PLAY_MEDIA = "play_media"
    SEARCH_WEB = "search_web"
    OPEN_URL = "open_url"
    CLOSE_APP = "close_app"
    CHAT = "chat"  # fallback -> goes to the LLM


@dataclass
class Command:
    intent: Intent
    target: str = ""  # e.g. app name, search query, song name, url
    raw_text: str = ""


# Known apps and their aliases in both English and Hindi/Hinglish.
APP_ALIASES = {
    "chrome": ["chrome", "google chrome", "browser", "ब्राउज़र"],
    "notepad": ["notepad", "note pad", "notes", "नोटपैड"],
    "youtube": ["youtube", "you tube", "यूट्यूब"],
    "calculator": ["calculator", "calc", "कैलकुलेटर"],
    "vscode": ["vs code", "vscode", "visual studio code", "code editor"],
    "file_explorer": ["file explorer", "files", "explorer", "फाइल्स"],
    "terminal": ["terminal", "command prompt", "cmd", "powershell"],
    "spotify": ["spotify"],
}

_OPEN_TRIGGERS = r"(open|launch|start|khol|kholo|khol do|chalao|चालू करो|खोलो|खोल दो)"
_CLOSE_TRIGGERS = r"(close|quit|exit|band karo|band kar do|बंद करो|बंद कर दो)"
_PLAY_TRIGGERS = r"(play|bajao|chala do|सुनाओ|बजाओ)"
_SEARCH_TRIGGERS = r"(search( for)?|google|dhundo|dhoondo|khojo|ढूंढो|सर्च करो)"


def _find_app(text: str) -> str | None:
    for canonical, aliases in APP_ALIASES.items():
        for alias in aliases:
            if alias in text:
                return canonical
    return None


def _strip_trigger(text: str, pattern: str) -> str:
    """Remove the matched trigger phrase, returning whatever text remains as the target."""
    return re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip(" :,-")


def route(text: str) -> Command:
    """
    Classify a transcribed utterance into a Command.
    Returns Intent.CHAT when nothing rule-based matches — that's the signal
    to hand the sentence over to the LLM for a normal conversational reply.
    """
    if not text:
        return Command(Intent.CHAT, raw_text=text)

    lowered = text.lower().strip()

    # 1. "play <song/video>" -> YouTube playback (checked before generic "open"
    #    so that "play believer on youtube" isn't misread as "open youtube").
    if re.search(_PLAY_TRIGGERS, lowered):
        target = _strip_trigger(lowered, _PLAY_TRIGGERS)
        target = re.sub(r"\bon youtube\b|\byoutube pe\b|\byoutube par\b", "", target).strip()
        if target:
            return Command(Intent.PLAY_MEDIA, target=target, raw_text=text)

    # 2. Close an app/window.
    if re.search(_CLOSE_TRIGGERS, lowered):
        app = _find_app(lowered)
        target = app or _strip_trigger(lowered, _CLOSE_TRIGGERS)
        return Command(Intent.CLOSE_APP, target=target, raw_text=text)

    # 3. Open a known app.
    if re.search(_OPEN_TRIGGERS, lowered):
        app = _find_app(lowered)
        if app:
            return Command(Intent.OPEN_APP, target=app, raw_text=text)
        # "open a new tab and search for ..." style phrasing
        remainder = _strip_trigger(lowered, _OPEN_TRIGGERS)
        if remainder.startswith(("http://", "https://", "www.")):
            return Command(Intent.OPEN_URL, target=remainder, raw_text=text)

    # 4. Explicit search command.
    if re.search(_SEARCH_TRIGGERS, lowered):
        target = _strip_trigger(lowered, _SEARCH_TRIGGERS)
        if target:
            return Command(Intent.SEARCH_WEB, target=target, raw_text=text)

    # 5. Nothing matched -> treat as normal conversation.
    return Command(Intent.CHAT, raw_text=text)
