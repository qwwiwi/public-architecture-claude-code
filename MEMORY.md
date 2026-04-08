# Memory System — 4 Layers

## Overview

```
┌──────────────────────────────────────────┐
│  IDENTITY (manual only)                   │
│  CLAUDE.md + AGENTS + USER + rules        │
│  Always in context                        │
├──────────────────────────────────────────┤
│  WARM (rolling 14 days)                   │
│  core/warm/decisions.md                   │
│  Always in context, auto-rotate to COLD   │
├──────────────────────────────────────────┤
│  HOT (rolling 72 hours)                  │
│  core/hot/recent.md                       │
│  Always in context, gateway auto-writes   │
├──────────────────────────────────────────┤
│  COLD (archive, grows)                   │
│  MEMORY.md, LEARNINGS.md                  │
│  NOT in context, Read tool on demand      │
├──────────────────────────────────────────┤
│  L4 SEMANTIC (OpenViking)                │
│  localhost:1933                           │
│  NOT in context, curl on demand           │
└──────────────────────────────────────────┘
```

## Layer Details

### IDENTITY (always loaded)

| File | Purpose | Mutability |
|------|---------|-----------|
| CLAUDE.md | SOUL, character, workflow | Manual only |
| AGENTS.md | Models, subagents, pipelines | Manual only |
| USER.md | Operator profile | Manual only |
| rules.md | Boundaries, permissions | Manual only |
| TOOLS.md | Servers, Docker, services | Manual only |

### WARM (rolling 14 days)

- File: `core/warm/decisions.md`
- Contains: architectural and operational decisions
- Rotation: entries older than 14 days move to COLD (MEMORY.md)
- Always in context via @include

### HOT (rolling 72 hours)

- File: `core/hot/recent.md`
- Contains: conversation journal (every message + response)
- Written by: Gateway process (auto-write after each interaction)
- Trim: cron job removes entries older than 72h
- Always in context via @include
- WARNING: can grow to 80KB+ and consume 70%+ of startup tokens

### HOT Format

```markdown
### 2026-04-08 15:03 [own_voice]
**Operator:** (transcription of voice message)
**Agent:** (compressed response summary)

### 2026-04-08 15:10 [own_text]
**Operator:** text message here
**Agent:** response summary here
```

### COLD (archive)

- Files: `MEMORY.md`, `LEARNINGS.md`, `archive/`
- NOT loaded at startup
- Accessed via Read tool when needed
- Grows indefinitely

### L4 Semantic ([OpenViking](https://github.com/volcengine/OpenViking))

- Endpoint: `localhost:1933`
- NOT loaded at startup
- Accessed via curl when old context needed (>72h)
- Each agent has own namespace (User header)
- Search: `POST /api/v1/search/find`
- Stores embeddings of past conversations
- Install: `pip install openviking --upgrade`

## Data Priority

1. Real system checks (exec) — ground truth
2. HOT/WARM (in context) — navigation
3. COLD (Read tool) — archive
4. OpenViking L4 (curl) — semantic search
5. Web search (Perplexity) — internet

## Token Budget

| Component | Typical Size | Tokens (est.) |
|-----------|-------------|---------------|
| Global CLAUDE.md + rules | ~8 KB | ~2,500 |
| Project CLAUDE.md | ~8 KB | ~2,500 |
| @includes (AGENTS, USER, rules, TOOLS) | ~17 KB | ~6,000 |
| WARM decisions.md | ~1 KB | ~300 |
| HOT recent.md | 10-80 KB | 3,000-25,000 |
| **TOTAL** | **35-115 KB** | **15,000-35,000** |

Opus context window: 200,000 tokens.
Startup cost: 8-18% of context window.
