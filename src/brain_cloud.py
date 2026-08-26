"""
Optional cloud brain: same `.reply()` interface as `src.brain.Brain`, but
backed by Groq's free-tier hosted inference instead of a local Ollama model.

Why this exists at all, given the whole point of Vrox is "free and local":
running Ollama + a 7B model needs real CPU/RAM that a free cloud box usually
doesn't have. Groq's API has a genuinely free tier (no card required) and is
extremely fast, which makes it a good fit specifically for a public *demo*
deployment (e.g. Hugging Face Spaces) — so people can try Vrox from a link
without installing anything. Running it yourself on your own machine still
defaults to Ollama; nothing about the local, $0, offline story changes.

Uses plain `requests` against Groq's OpenAI-compatible REST endpoint instead
of adding the `groq` SDK as a dependency — one less package to install.
"""

import logging

import requests

from src.config import SYSTEM_PROMPT, settings
from src.memory import ConversationMemory

log = logging.getLogger("vrox.brain_cloud")

_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqBrain:
    def __init__(self, memory: ConversationMemory | None = None):
        if not settings.groq_api_key:
            raise RuntimeError(
                "VROX_LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com/keys and set it as an env var."
            )
        self.memory = memory or ConversationMemory()

    def reply(self, user_text: str, action_result: str | None = None) -> str:
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

        resp = requests.post(
            _CHAT_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_llm_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=30,
        )
        resp.raise_for_status()
        reply_text = resp.json()["choices"][0]["message"]["content"].strip()

        self.memory.add_assistant(reply_text)
        log.info("Brain (groq) reply: %s", reply_text)
        return reply_text
