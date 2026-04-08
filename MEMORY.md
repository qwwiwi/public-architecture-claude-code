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

## Memory Operations (Flush, Compaction, Rotation)

### HOT write (every message)

Gateway calls `append_to_hot_memory()` after **every** interaction:

```
User sends message -> Claude responds -> append to core/hot/recent.md
```

- Format: `### YYYY-MM-DD HH:MM [source_tag]` + user snippet (200 chars) + agent snippet (200 chars)
- File locking: `fcntl.LOCK_EX` prevents interleaved writes from concurrent handlers
- Source tags: `own_text`, `own_voice`, `forwarded`, `external_media`

### Emergency trim (automatic, on write)

If `recent.md` exceeds **20 KB** after a write:

```
hot file > 20KB → keep last 600 lines (~150 entries) → find first ### header → rewrite
```

- Trigger: checked on every `append_to_hot_memory()` call
- Keeps: last 600 lines (entries are 4 lines each = ~150 entries = ~2-3 days)
- Trims from the top, preserving entry boundaries (finds first `### ` header)

### /compact command (manual)

Operator sends `/compact` in Telegram:

```
1. Read core/hot/recent.md
2. Extract key facts from last 24h (decisions, preferences, pending actions)
3. ADD extracted facts to beginning of core/warm/decisions.md as:
   ## YYYY-MM-DD
   - fact 1
   - fact 2
4. Trim hot/recent.md: keep last 48h only
```

- Model: Sonnet (cheaper, fast enough for extraction)
- Timeout: 180 seconds
- Runs in background thread (non-blocking)

### /reset command (session reset)

Operator sends `/reset` in Telegram:

```
1. Claude reads current context (via --resume old session)
2. Saves important info to core/MEMORY.md (COLD):
   - current focus, decisions, pending actions, user preferences
3. Deletes session ID file (state/sid-{agent}-{chat}.txt)
4. Next message starts a fresh session
```

- `/reset force` — skips saving, immediately deletes session
- Model: Sonnet (for the save step)
- After reset, first message injects latest MEMORY.md section as context bridge

### WARM -> COLD rotation (cron, every 14 days)

Entries older than 14 days in `core/warm/decisions.md` should move to `core/MEMORY.md`.

```
# Example cron (runs daily at 04:00 UTC)
0 4 * * * /path/to/rotate-warm.sh
```

Script logic:
1. Parse `## YYYY-MM-DD` headers in `decisions.md`
2. Sections older than 14 days → append to `MEMORY.md`
3. Remove from `decisions.md`

### HOT trim (cron, daily)

Entries older than 72h should be removed from `core/hot/recent.md`.

```
# Example cron (runs daily at 05:00 UTC)
0 5 * * * /path/to/trim-hot.sh
```

Script logic:
1. Parse `### YYYY-MM-DD HH:MM` headers
2. Remove entries older than 72 hours
3. Rewrite file with remaining entries

### Recommended cron schedule

```crontab
# HOT trim: remove entries >72h (daily 05:00 UTC)
0 5 * * * /path/to/trim-hot.sh

# WARM rotate: move >14d decisions to COLD (daily 04:00 UTC)
0 4 * * * /path/to/rotate-warm.sh

# Backup: snapshot memory files (daily 03:00 UTC)
0 3 * * * /path/to/backup.sh
```

## OpenViking: Triggers and Data Flow

### When data is pushed

Gateway pushes to OpenViking after **every message** where:

| Source tag | Pushed to OV? | Reason |
|------------|---------------|--------|
| `own_text` | Yes | Operator's own words — extract preferences, decisions |
| `own_voice` | Yes | Same as text (after Groq transcription) |
| `forwarded` | Yes (with guard) | Third-party content — extract events, NOT user preferences |
| `external_media` | No | Media only goes to HOT, not OV (avoids pollution) |
| transcription failed | No | Broken audio — skip to avoid garbage |

### What is sent

```
POST /api/v1/sessions                          → create session
POST /api/v1/sessions/{sid}/messages           → user message (max 3000 chars)
POST /api/v1/sessions/{sid}/messages           → agent response (max 3000 chars)
POST /api/v1/sessions/{sid}/extract            → trigger LLM extraction
DELETE /api/v1/sessions/{sid}                  → cleanup
```

Each message includes metadata prefix: `[chat:{id} agent:{name} at {timestamp}]`

### Anti-pollution guards

For forwarded and external content, OV receives extraction hints:

- **Forwarded:** `[extraction hint: this content was FORWARDED ... Do NOT extract as user's own preferences]`
- **External media:** `[extraction hint: this is external media ... Do NOT extract as user's preferences]`

### What OpenViking extracts

OpenViking runs its own LLM on the session to extract structured memories:
- User preferences and decisions
- Named entities (tools, projects, people)
- Action items and commitments
- Patterns and recurring topics

These are stored as embeddings and searchable via:
```bash
curl -X POST "http://localhost:1933/api/v1/search/find" \
  -H "X-API-Key: $KEY" \
  -H "X-OpenViking-Account: $ACCOUNT" \
  -H "X-OpenViking-User: $AGENT" \
  -d '{"query": "topic", "limit": 10}'
```

### Threading model

- Push runs in a **bounded ThreadPoolExecutor** (max 2 workers)
- Fire-and-forget: does not block message response
- Session is always cleaned up in `finally` block (prevents leaks)

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

Opus 4.6 / Sonnet 4.6 context window: 1,000,000 tokens (~830K usable).
Startup cost: 2-4% of context window.
CLAUDE.md recommended size: under 200 lines (beyond that Claude starts ignoring instructions).
@import max recursion depth: 5 hops.
