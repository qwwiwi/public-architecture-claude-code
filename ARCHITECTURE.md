# Agent Architecture — Local Files + OpenViking

No external databases. Only local files and semantic search.

## Entry Points

```
Operator
├── Terminal (SSH/local) → Claude Code (interactive)
└── Telegram (@bot)      → JARVIS Gateway (autonomous)
```

## Agents

| Agent | Mode | Permissions | Session | Gateway |
|-------|------|-------------|---------|---------|
| Claude Code | Interactive | Manual approve | Long (hours) | No (standard CLI) |
| JARVIS | Autonomous | Bypass | Short (request-response) | Yes (systemd) |

## Context Loading (at session start)

```
Claude Code launch
│
├── ~/.claude/CLAUDE.md           global rules
├── ~/.claude/rules/*.md          language rules
│
└── {agent}/.claude/CLAUDE.md     agent SOUL
    ├── @core/AGENTS.md           models, subagents
    ├── @core/USER.md             operator profile
    ├── @core/rules.md            boundaries
    ├── @tools/TOOLS.md           servers, tools
    ├── @core/warm/decisions.md   rolling 14 days
    └── @core/hot/recent.md       rolling 72 hours

~15-35K tokens depending on HOT size
```

## Session Management

```
Session lifecycle:
  1. First message   → new session ID (UUID), saved in state/sid-{agent}-{chat}.txt
  2. Subsequent msgs → claude --resume <session_id> (preserves context)
  3. /reset          → save to COLD, delete session file, next msg = new session
  4. /reset force    → delete session file immediately, no save
  5. Post-reset      → first message injects latest MEMORY.md section as context bridge
```

Key commands:
- `claude --continue` — resume last conversation
- `claude --resume` — pick from session list
- `claude -n "name"` — name a session
- `/rewind` or `Esc+Esc` — restore from checkpoint (conversation, code, or both)

Checkpoints are created on every Claude action and persist across sessions.

## On-Demand (NOT in context)

```
COLD memory    → Read tool (MEMORY.md, LEARNINGS.md)
Skills         → Skill tool (shared/skills/)
OpenViking L4  → curl localhost:1933
Web search     → Perplexity / DuckDuckGo
```

## Complete Data Flow

End-to-end path from operator message to memory persistence:

```
OPERATOR sends message (Telegram)
    |
    v
GATEWAY (systemd service, always running)
    | 1. Receive message (long-polling thread)
    | 2. Classify source:
    |    - own_text: operator typed directly
    |    - own_voice: operator sent voice message
    |    - forwarded: operator forwarded from another chat
    |    - external_media: photo/video/document (not voice)
    | 3. Download media if present (20MB limit)
    | 4. Transcribe voice via Groq Whisper (whisper-large-v3-turbo)
    |    - If transcription fails: message still processed, marked as failed
    | 5. Launch Claude Code: claude -p --resume <session_id>
    |    - Session ID stored in state/sid-{agent}-{chat}.txt
    |    - If no session file: new session (claude -p --session-id <uuid>)
    |    - Context loaded via @include from CLAUDE.md
    | 6. Stream progress to Telegram (real-time status updates)
    | 7. Get response from Claude Code
    |
    v
MEMORY WRITE (parallel, after every message)
    | A. HOT: append to core/hot/recent.md (ALWAYS, all source tags)
    |    - fcntl.LOCK_EX for concurrent safety
    |    - Format: ### YYYY-MM-DD HH:MM [source_tag]
    |    - Snippet: 200 chars user + 200 chars agent
    |    - Emergency trim: if >20KB, keep last 600 lines
    |
    | B. OpenViking: push to localhost:1933 (FILTERED by source tag)
    |    - own_text: YES (extract preferences, decisions)
    |    - own_voice: YES (extract preferences, decisions)
    |    - forwarded: YES (with anti-pollution guard)
    |    - external_media: NO (avoids preference pollution)
    |    - transcription_failed: NO (avoids garbage)
    |    - Fire-and-forget: 2-thread pool, non-blocking
    |
    v
REPLY to operator in Telegram (markdown -> HTML, chunked at 4000 chars)
```

This is the critical path. Every message follows this exact sequence. Memory writes never block the response -- they happen in parallel after Claude Code returns.

## Why Memory Compression Matters

Without compression, HOT memory grows to 80KB+ per day. At 150+ messages per day with ~500 bytes each, this is expected. The problem: 80KB of raw conversation logs equals ~36,000 tokens -- roughly 70% of the total startup context at Opus level.

Quality degrades when context is bloated with raw logs. The agent spends most of its attention on unstructured conversation history instead of identity, rules, and tools. This is measurable -- an agent with 80KB of raw HOT performs noticeably worse at following instructions than one with 20KB of structured facts.

Sonnet compression solves this: 110 raw entries compress into 15-20 key facts (80% reduction). The 4 cron scripts (rotate-warm, trim-hot, compress-warm, memory-rotate) run daily and keep memory clean.

| Metric | Without compression | With compression |
|--------|--------------------|--------------------|
| HOT size (end of day) | 80 KB+ | 10-20 KB |
| Tokens consumed by HOT | ~36,000 | ~4,500-9,000 |
| Startup context used | ~70% | ~10-15% |
| Sonnet cost | n/a | $0 (Max subscription) |
| Agent instruction-following | Degraded | Optimal |

The compression system exists not to save money but to keep context CLEAN. An agent with 80KB of raw conversation logs performs worse than one with 20KB of structured facts -- even though both fit within the 1M token window.

## Gateway Flow (Telegram → Claude Code)

```
Operator (Telegram)
    │ voice / text / photo
    ▼
Gateway (systemd service)
    │ 1. Receive message (polling thread)
    │ 2. Classify source (own_text / own_voice / forwarded / external_media)
    │ 3. Download media (photo, video, document — 20MB limit)
    │ 4. Transcribe voice ([Groq](https://groq.com) Whisper — whisper-large-v3-turbo)
    │ 5. Launch Claude Code (claude -p --resume <session_id>)
    │ 6. Stream progress (real-time status in Telegram: plan, tools, subagents)
    │ 7. Write to HOT (core/hot/recent.md — fcntl lock, 200 char snippets)
    │ 8. Push to OpenViking (fire-and-forget, 2-thread pool — own_text/voice/forwarded only)
    │ 9. Reply in Telegram (markdown → HTML, chunked at 4000 chars)
    ▼
Claude Code (model)
    │ context loaded via @include
    ▼
Response to operator
```

## Inter-Agent Communication

Agents communicate via local inbox files or shared message bus:

```
Agent A → shared/messages/inbox/{agent-b}
Agent B → shared/messages/inbox/{agent-a}
```

## OpenViking (Local Semantic Search)

[OpenViking](https://github.com/volcengine/OpenViking) -- open-source context database for AI agents. Manages memories, resources, and skills through a filesystem paradigm with tiered context loading.

```
localhost:1933
│
├── Account: {org}
│   ├── User: claude-code    (own embeddings)
│   └── User: jarvis         (own embeddings)
│
├── Write: after EVERY message (gateway auto-push)
│   POST /api/v1/sessions           → create
│   POST /api/v1/sessions/{id}/messages  → user + agent msgs (max 3000 chars each)
│   POST /api/v1/sessions/{id}/extract   → LLM extracts structured memories
│   DELETE /api/v1/sessions/{id}         → cleanup
│
├── What triggers push:
│   own_text     → yes (extract preferences, decisions)
│   own_voice    → yes (after Groq transcription)
│   forwarded    → yes (with anti-pollution guard)
│   external_media → NO (hot only, avoids preference pollution)
│
└── Search: when old context needed (>72h)
    POST /api/v1/search/find
    {"query": "topic", "limit": 10}
```

Install: `pip install openviking --upgrade`

## Memory Rotation and Cron

Complete data flow with Sonnet-based compression:

```
Gateway (every message) -> HOT (recent.md)
  |
  +-- Emergency trim (auto, >20KB, bash)
  |     Keeps last 600 lines, trims from top
  |
  +-- trim-hot.sh (cron 05:00 UTC, Sonnet)
  |     Entries >24h -> Sonnet summary -> WARM
  |     >40 entries remaining -> oldest also compressed
  |     Fallback: bash (first 120 chars if Sonnet unavailable)
  |     Runs from /tmp to avoid loading CLAUDE.md (~35K tokens saved)
  |     flock for safe concurrent access with gateway
  |
  +-- compress-warm.sh (cron 06:00 UTC, Sonnet)
  |     WARM >10KB -> Sonnet re-compression by topic
  |     110 raw entries -> 15-20 key facts
  |     Skip if <10KB or <50 lines or Sonnet unavailable
  |     Garbage protection: skip if Sonnet returns <3 lines
  |
  +-- rotate-warm.sh (cron 04:30 UTC, bash)
  |     WARM >14d -> COLD (pure bash, no model)
  |
  +-- memory-rotate.sh (cron 21:00 UTC, bash)
  |     COLD >5KB -> archive/YYYY-MM.md (pure bash)
  |
  +-- /compact command (manual, Sonnet)
  |     Extract key facts from last 24h HOT -> WARM, trim HOT to 48h
  |
  +-- /reset command (manual, Sonnet)
        Save important context to COLD, start new session

L4     -> OpenViking, fire-and-forget after every message, forever
```

### Recommended crontab

```crontab
# 1. Rotate WARM: move >14d entries to COLD (bash, no model)
30 4 * * * /path/to/rotate-warm.sh

# 2. Trim HOT: entries >24h -> Sonnet summary -> WARM
0 5 * * * /path/to/trim-hot.sh

# 3. Compress WARM: Sonnet re-compression by topic (>10KB only)
0 6 * * * /path/to/compress-warm.sh

# 4. Archive COLD: MEMORY.md >5KB -> archive/YYYY-MM.md (bash)
0 21 * * * /path/to/memory-rotate.sh
```

Order: rotate-warm (clear old) -> trim-hot (add new to WARM) -> compress-warm (re-compress if needed).

### Gateway commands for memory

| Command | What it does |
|---------|-------------|
| `/compact` | Extract key facts from last 24h HOT → WARM, trim HOT to 48h |
| `/reset` | Save important context to COLD (MEMORY.md), start new session |
| `/reset force` | Delete session immediately, no save |
| `/status` | Show session age, memory file sizes (rules, warm, hot, cold) |
