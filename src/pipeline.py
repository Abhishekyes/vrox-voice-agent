"""
The orchestrator that wires every component together into one turn of
conversation. Both the CLI (vrox_cli.py) and the LAN web server
(src/server.py) call the same `handle_text()` function, so there is exactly
one place that defines "what happens when Vrox hears something" —
no logic duplicated between the two entry points.
"""

import logging

from src.actions import execute
from src.brain import create_brain
from src.config import settings
from src.intent_router import Intent, route

log = logging.getLogger("vrox.pipeline")

_DEMO_ACTION_NOTE = (
    "(The user asked for a system action, but this is the public web demo, "
    "which has no desktop to control — so nothing was actually executed. "
    "Explain briefly and warmly that this action only works when Vrox is "
    "run locally on their own PC, and point them to the GitHub repo.)"
)


class VroxPipeline:
    def __init__(self):
        self.brain = create_brain()

    def handle_text(self, text: str) -> str:
        """
        Given already-transcribed user text, decide whether it's a system
        command or plain conversation, act accordingly, and return the
        natural-language reply that should be spoken back.
        """
        text = text.strip()
        if not text:
            return ""

        command = route(text)
        log.info("Routed %r -> %s", text, command.intent)

        if command.intent is Intent.CHAT:
            return self.brain.reply(text)

        # In demo mode (the public cloud deployment) there's no real desktop
        # to control, and running subprocess/psutil calls on a shared public
        # server for anonymous visitors is a bad idea regardless — so skip
        # actually executing the action and let the LLM explain that instead.
        if settings.demo_mode:
            return self.brain.reply(text, action_result=_DEMO_ACTION_NOTE)

        # It's a system command: execute it, then let the LLM react briefly.
        action_result = execute(command)
        return self.brain.reply(text, action_result=action_result)
