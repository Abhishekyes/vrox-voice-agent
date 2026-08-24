"""
Conversation memory — deliberately the simplest thing that works.

No vector database, no embeddings, no external memory service: just a
Python list of {"role", "content"} dicts, capped to the last N turns so the
prompt sent to the local LLM stays small (keeps replies fast on a laptop
CPU/GPU). This is an easy, honest thing to explain in an interview: "short
-term memory is just a bounded list; there is no long-term memory yet — a
natural 'future work' talking point."
"""

from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    max_turns: int = 12  # keep the last N user+assistant exchanges
    _messages: list[dict] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant(self, text: str) -> None:
        self._messages.append({"role": "assistant", "content": text})
        self._trim()

    def history(self) -> list[dict]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def _trim(self) -> None:
        max_messages = self.max_turns * 2
        if len(self._messages) > max_messages:
            self._messages = self._messages[-max_messages:]
