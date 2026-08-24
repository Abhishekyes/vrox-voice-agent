"""
The orchestrator that wires every component together into one turn of
conversation. Both the CLI (vrox_cli.py) and the LAN web server
(src/server.py) call the same `handle_text()` function, so there is exactly
one place that defines "what happens when Vrox hears something" —
no logic duplicated between the two entry points.
"""

import logging

from src.actions import execute
from src.brain import Brain
from src.intent_router import Intent, route

log = logging.getLogger("vrox.pipeline")


class VroxPipeline:
    def __init__(self):
        self.brain = Brain()

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

        # It's a system command: execute it, then let the LLM react briefly.
        action_result = execute(command)
        return self.brain.reply(text, action_result=action_result)
