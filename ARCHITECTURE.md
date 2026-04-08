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
    │ 1. Receive message
    │ 2. Transcribe voice ([Groq](https://groq.com) Whisper)
    │ 3. Launch Claude Code
    │ 4. Write to HOT (recent.md)
    │ 5. Reply in Telegram
    ▼
Claude Code (model)
    │ context loaded
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
├── Write: after each session
│   POST /api/v1/memories/save
│
└── Search: when old context needed (>72h)
    POST /api/v1/search/find
    {"query": "topic", "limit": 10}
```

Install: `pip install openviking --upgrade`

## Memory Rotation

```
HOT (72h)  → cron trim entries >72h
WARM (14d) → rotate old decisions to COLD
COLD       → grows, Read tool on demand
L4         → OpenViking, forever
```
