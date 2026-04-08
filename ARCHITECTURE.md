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
