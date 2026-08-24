# Talking about this project in an interview

A cheat-sheet of how to describe Vrox confidently, at different levels of
depth depending on how much time/interest the interviewer has.

## 30-second pitch

"I built Vrox, a local voice assistant that chats naturally in Hindi and
English and can control my computer — opening apps, playing YouTube videos,
searching the web — all by voice. The whole thing runs on my own machine
for free: local speech recognition, a local LLM through Ollama, and free
neural text-to-speech, so there's no API-cost ceiling on how much I can
demo it. I also built a small web layer so I can control my PC from my
phone over WiFi, and set up CI on GitHub that lints and tests the code on
every push."

## The 5 components, in one sentence each

1. **Ears (STT):** local Whisper model turns your speech into text, fully
   offline, multilingual by default.
2. **Router:** a fast, regex-based classifier decides "is this a system
   command or just conversation?" before anything expensive runs.
3. **Hands (Actions):** OS-specific functions that actually open apps,
   play media, search, or close windows — one file, branches by OS.
4. **Brain:** a local LLM (via Ollama) holds the actual conversation, with
   a system prompt defining a warm, Hinglish-mixing personality and a
   short rolling memory of recent turns.
5. **Voice (TTS):** free neural text-to-speech (edge-tts) speaks the reply
   back naturally.

## Likely follow-up questions, and how to answer them

**"Why not just use ChatGPT's API / a cloud LLM?"**
Cost and control. A cloud LLM API charges per token on every single turn,
which adds up fast for a chatty voice assistant, and it means the demo's
uptime depends on having a funded API key. Running a small open model
locally via Ollama removes that constraint entirely — I can demo this as
much as I want for $0. It's a similar tradeoff to on-device vs cloud
inference in production ML systems, which felt like a good thing to
practice reasoning about.

**"Why regex instead of using the LLM to decide what action to take?"**
Latency and reliability. A regex match is instant and deterministic; an
LLM call adds hundreds of milliseconds to seconds of latency and isn't
guaranteed to make the same decision twice. Since the command vocabulary
(open/play/search/close) is small and well-defined, a rule-based router is
the right tool — I'd only reach for an LLM-based classifier or
function-calling if the vocabulary grew large or fuzzy enough that regex
stopped scaling.

**"How would you scale this to more users / make it a real product?"**
Two changes: (1) move the Brain behind a small hosted API so multiple
devices/users share one service instead of each needing local Ollama, and
(2) replace the bounded in-memory conversation history with real
persistent storage (e.g. a lightweight DB) keyed per user, so
conversations survive restarts. Both are called out as future work in
docs/ARCHITECTURE.md.

**"What was the hardest part?"**
Good honest answers, pick what actually felt true while building:
- Getting the OS-control code to work sanely across Windows/Mac/Linux
  without three completely separate codepaths (solved with one
  per-OS command table in `actions.py`).
- Deciding where to draw the line between "instant rule-based command" and
  "send it to the LLM" — too aggressive a router misfires on normal
  conversation, too passive and every command pays LLM latency.
- Keeping voice replies short enough to feel like a real conversation
  instead of the LLM writing paragraph-length answers out loud.

**"Why isn't this deployed live on the internet?"**
Because the core feature — controlling a specific computer's apps and
screen — only makes sense running *on* that computer; there's no server
that can open Chrome on your laptop except your laptop. So I deployed the
part that's honestly deployable: the code + CI live on GitHub, and the app
itself is deployed onto my machine and reachable from other devices on my
home network, the same pattern used by self-hosted tools like Home
Assistant or Plex. I think being able to articulate *why* a "just deploy
it to the cloud" approach doesn't fit this problem is itself a useful
signal — not every system should be a hosted web service.

**"What would you change/add next?"**
- Wake-word detection ("Hey Vrox") instead of push-to-talk.
- A small learned intent classifier once the command set grows beyond
  what regex comfortably handles.
- Persistent memory (remembering preferences across sessions, e.g. "she
  likes lo-fi music").
- Streaming responses (start speaking the first sentence of a reply while
  the rest is still generating) to cut perceived latency further.

## Concepts this project demonstrates (say these explicitly if asked "what did you learn")

- Speech-to-text and text-to-speech pipelines, and the free/offline vs.
  paid/cloud tradeoffs between them.
- Local LLM inference and prompt/system-message design for a consistent
  personality.
- Simple, explainable NLU via rule-based intent classification, as an
  alternative to always reaching for a model.
- Cross-platform system programming (`subprocess`, `psutil`,
  `platform.system()`).
- A minimal client-server architecture (FastAPI + a browser client) for
  remote control over a local network.
- CI fundamentals: linting + automated tests wired into GitHub Actions.
- Being deliberate about *what* to deploy where, instead of defaulting to
  "put everything in the cloud."
