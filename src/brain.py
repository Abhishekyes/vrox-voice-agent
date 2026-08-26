"""
Brain: the conversational core, powered by a local LLM through Ollama.

Concept (simple to explain in an interview):
  * Ollama is a free tool that runs open-weight LLMs (Llama, Qwen, Mistral,
    etc.) entirely on your own machine — no API key, no per-token cost,
    no data leaving your laptop.
  * We keep one persistent system prompt (the personality — see
    src/config.py) plus a short rolling window of chat history
    (src/memory.py), and send that whole list to Ollama's chat endpoint
    each turn, the same "messages" shape used by most chat APIs.
  * When the intent_router has already executed a system command (e.g.
    "opened Chrome"), we pass that outcome in as a short system note so
    the LLM reacts to it naturally instead of re-deciding what to do.
"""

import logging

import ollama

from src.config import SYSTEM_PROMPT, settings
from src.memory import ConversationMemory

log = logging.getLogger("vrox.brain")


class Brain:
    def __init__(self, memory: ConversationMemory | None = None):
        self.memory = memory or ConversationMemory()
        self._client = ollama.Client(host=settings.ollama_host)

    def reply(self, user_text: str, action_result: str | None = None) -> str:
        """
        Get a natural-language reply from the local LLM.

        `action_result` is an optional short note describing a system
        action that already ran (e.g. "opened Chrome"), so the model can
        react to it ("Done, khol diya!") instead of trying to perform it
        itself in text.
        """
        self.memory.add_user(user_text)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if action_result:
            messages.append(
                {
                    "role": "system",
                    "content": f"(A system action already ran with this result: {action_result}. "
                    "React to it briefly and naturally, don't re-explain it.)",
                }
            )
        messages += self.memory.history()

        response = self._client.chat(model=settings.llm_model, messages=messages)
        reply_text = response["message"]["content"].strip()

        self.memory.add_assistant(reply_text)
        log.info("Brain reply: %s", reply_text)
        return reply_text


def create_brain(memory: ConversationMemory | None = None):
    """
    Factory that returns the right brain implementation for `VROX_LLM_PROVIDER`
    — the local Ollama-backed `Brain` by default, or `GroqBrain` for a hosted
    deployment. Both expose the same `.reply(user_text, action_result=None)`
    method, so every caller (CLI, server) can stay provider-agnostic.
    """
    if settings.llm_provider == "groq":
        from src.brain_cloud import GroqBrain

        return GroqBrain(memory)
    return Brain(memory)
