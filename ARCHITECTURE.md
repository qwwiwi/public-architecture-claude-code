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

```
HOT (72h)  → emergency trim at 20KB (auto, on every write)
           → cron trim entries >72h (daily 05:00 UTC)
           → /compact command: extract facts → WARM, keep last 48h

WARM (14d) → cron rotate >14d entries to COLD (daily 04:00 UTC)

COLD       → grows, Read tool on demand
           → /reset saves context here before session wipe

L4         → OpenViking, fire-and-forget after every message, forever
```

### Recommended crontab

```crontab
# Trim HOT: remove entries >72h from recent.md
0 5 * * * /path/to/trim-hot.sh

# Rotate WARM: move >14d decisions to MEMORY.md (COLD)
0 4 * * * /path/to/rotate-warm.sh

# Backup memory files
0 3 * * * /path/to/backup.sh
```

### Gateway commands for memory

| Command | What it does |
|---------|-------------|
| `/compact` | Extract key facts from last 24h HOT → WARM, trim HOT to 48h |
| `/reset` | Save important context to COLD (MEMORY.md), start new session |
| `/reset force` | Delete session immediately, no save |
| `/status` | Show session age, memory file sizes (rules, warm, hot, cold) |
