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
│  HOT (rolling 24 hours)                  │
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

### HOT (rolling 24 hours)

- File: `core/hot/recent.md`
- Contains: conversation journal (every message + response)
- Written by: Gateway process (auto-write after each interaction)
- Trim: cron job removes entries older than 24h
- Always in context via @include
- WARNING: without cron, can grow to 80KB+ before trimming. After cron runs, typical size is 8-30 KB

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
- Accessed via curl when old context needed (>24h)
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

### WARM -> COLD rotation (rotate-warm.sh, cron 04:30 UTC)

Entries older than 14 days in `core/warm/decisions.md` move to `core/MEMORY.md`.

```
# Cron: daily at 04:30 UTC (runs BEFORE trim-hot adds new entries to WARM)
30 4 * * * /path/to/rotate-warm.sh
```

Script logic (pure bash, no model):
1. Parse `## YYYY-MM-DD` headers in `decisions.md`
2. Sections older than 14 days -- append to `MEMORY.md`
3. Remove from `decisions.md`

### HOT -> WARM compression (trim-hot.sh, cron 05:00 UTC)

Entries older than 24h are collected and sent to **Sonnet** for smart summarization, then appended to WARM.

```
# Cron: daily at 05:00 UTC
0 5 * * * /path/to/trim-hot.sh
```

How it works:
1. If HOT (`recent.md`) is under 10 KB -- skip entirely
2. Acquire `flock` on HOT file (prevents conflicts with gateway writes)
3. Collect all entries with timestamps older than 24h
4. If more than 40 entries remain after removing old ones -- also collect the oldest entries
5. Send collected entries to **Sonnet** with prompt: extract key facts as `- YYYY-MM-DD HH:MM: fact/decision/result`
6. Append Sonnet output to `core/warm/decisions.md`
7. Rewrite `recent.md` with remaining (recent) entries only

Key details:
- Runs from `/tmp` working directory to avoid loading project CLAUDE.md (saves ~35K tokens per run)
- **Bash fallback:** if Sonnet is unavailable (rate limit, timeout), falls back to extracting first 120 characters of each entry
- Uses `flock` for safe concurrent access with gateway process

### WARM compression (compress-warm.sh, cron 06:00 UTC)

After trim-hot.sh adds new entries to WARM daily, WARM can grow large with raw per-entry facts. compress-warm.sh uses **Sonnet** to re-compress WARM by grouping related events into topic-based key facts.

```
# Cron: daily at 06:00 UTC (runs AFTER trim-hot adds new entries)
0 6 * * * /path/to/compress-warm.sh
```

How it works:
1. If WARM (`decisions.md`) is under 10 KB or under 50 lines -- skip
2. Send full WARM content to Sonnet: "group related events into topic-based key facts"
3. If Sonnet returns fewer than 3 lines -- skip (garbage protection)
4. Replace WARM content with compressed output
5. Typical result: 110 raw entries -- 15-20 key facts

Safety:
- **Sonnet unavailable** (rate limit, timeout) -- skip, retry next run
- **Sonnet returns < 3 lines** -- skip, do not overwrite (garbage protection)
- Original content is backed up before overwrite

### COLD archival (memory-rotate.sh, cron 21:00 UTC)

When COLD (`MEMORY.md`) exceeds 5 KB, older content is moved to monthly archives.

```
# Cron: daily at 21:00 UTC
0 21 * * * /path/to/memory-rotate.sh
```

Script logic (pure bash, no model):
1. If `MEMORY.md` is under 5 KB -- skip
2. Move content to `archive/YYYY-MM.md` (grouped by month)
3. Keep only recent entries in `MEMORY.md`

### Recommended cron schedule

```crontab
# 1. Rotate WARM: move >14d entries to COLD (bash, no model)
30 4 * * * /path/to/rotate-warm.sh

# 2. Trim HOT: entries >24h -> Sonnet summary -> WARM
0 5 * * * /path/to/trim-hot.sh

# 3. Compress WARM: Sonnet re-compression by topic (>10KB only)
0 6 * * * /path/to/compress-warm.sh

# 4. Sync to OpenViking: HOT+WARM -> semantic search (bash + curl)
30 6 * * * /path/to/ov-session-sync.sh

# 5. Archive COLD: MEMORY.md >5KB -> archive/YYYY-MM.md (bash)
0 21 * * * /path/to/memory-rotate.sh
```

Order matters: rotate-warm first (clears old WARM entries), then trim-hot (adds new entries to WARM), then compress-warm (re-compresses if WARM grew too large), then ov-session-sync (uploads compressed state to OpenViking).

## OpenViking: Triggers and Data Flow

OpenViking data is synced via two mechanisms: **batch sync** (recommended) and **real-time push** (optional).

### Method 1: Batch sync via cron + Stop hook (recommended)

A shell script (`ov-session-sync.sh`) collects HOT + WARM memory and uploads to OpenViking as a single resource. Runs on two triggers:

| Trigger | When | How |
|---------|------|-----|
| **Cron** | Daily at 06:30 UTC (after memory rotation) | `30 6 * * * bash scripts/ov-session-sync.sh` |
| **Stop hook** | Every time Claude Code finishes responding | `settings.json` → `hooks.Stop` |

**What the script does:**

```
1. Health check → OpenViking reachable?
2. Build markdown summary from HOT (last 10 entries) + WARM (full)
3. POST /api/v1/resources/temp_upload → upload markdown as temp file
4. POST /api/v1/resources → add_resource with target URI + wait=true
5. OpenViking indexes content, creates embeddings automatically
```

**Target URI pattern:** `viking://resources/{agent}-sessions/{YYYY-MM-DD}`

**Stop hook configuration** (in `~/.claude/settings.json`):

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "bash scripts/ov-session-sync.sh >> /tmp/ov-session-sync.log 2>&1 &",
        "timeout": 10
      }]
    }]
  }
}
```

**Why batch sync over real-time:** Simpler, no threading issues, no session lifecycle to manage. HOT+WARM already contain compressed context — uploading once per session (or daily) is sufficient for semantic search.

### Method 2: Real-time push from gateway (optional)

Gateway can push to OpenViking after **every message** where:

| Source tag | Pushed to OV? | Reason |
|------------|---------------|--------|
| `own_text` | Yes | Operator's own words — extract preferences, decisions |
| `own_voice` | Yes | Same as text (after Groq transcription) |
| `forwarded` | Yes (with guard) | Third-party content — extract events, NOT user preferences |
| `external_media` | No | Media only goes to HOT, not OV (avoids pollution) |
| transcription failed | No | Broken audio — skip to avoid garbage |

**Anti-pollution guards** for forwarded content:

- **Forwarded:** `[extraction hint: this content was FORWARDED ... Do NOT extract as user's own preferences]`
- **External media:** `[extraction hint: this is external media ... Do NOT extract as user's preferences]`

**Threading model:**
- Push runs in a **bounded ThreadPoolExecutor** (max 2 workers)
- Fire-and-forget: does not block message response

### Searching OpenViking

Both methods produce embeddings searchable via the same API:

```bash
curl -X POST "http://localhost:1933/api/v1/search/find" \
  -H "X-API-Key: $KEY" \
  -H "X-OpenViking-Account: $ACCOUNT" \
  -H "X-OpenViking-User: $AGENT" \
  -d '{"query": "topic", "limit": 10}'
```

**Note:** `localhost:1933` is the default. For multi-VPS setups, use the Tailscale IP of the server running OpenViking (e.g., `100.x.x.x:1933`).

## Data Priority

1. Real system checks (exec) — ground truth
2. HOT/WARM (in context) — navigation
3. COLD (Read tool) — archive
4. OpenViking L4 (curl) — semantic search
5. Web search (Perplexity) — internet

## Token Budget

### Token counting rules

BPE tokenizers split Cyrillic characters into more tokens than Latin. If your agent operates in a non-Latin language, token counts will be significantly higher than byte counts suggest.

| Content type | Tokens per byte | Why |
|-------------|----------------|-----|
| Russian text (Cyrillic) | ~0.45 | Each Cyrillic char = 2 bytes UTF-8, often 1 token per char |
| English text (Latin) | ~0.25-0.30 | ASCII chars pack efficiently into BPE tokens |
| Mixed markdown/code | ~0.25 | Code keywords and markdown syntax tokenize well |

This means a 10 KB file in Russian consumes ~4,500 tokens, while the same 10 KB in English consumes ~2,500-3,000 tokens. Plan accordingly.

### Per-file budget (detailed)

| Component | Typical Size | Tokens (Russian) | Tokens (English) |
|-----------|-------------|-------------------|-------------------|
| Global CLAUDE.md | ~8 KB | ~3,600 | ~2,400 |
| Project CLAUDE.md | ~8 KB | ~3,600 | ~2,400 |
| AGENTS.md | ~6 KB | ~2,700 | ~1,800 |
| USER.md | ~2 KB | ~900 | ~600 |
| rules.md | ~5 KB | ~2,250 | ~1,500 |
| TOOLS.md | ~6 KB | ~2,700 | ~1,800 |
| Language rules (rules/*.md) | ~3 KB | ~1,350 | ~900 |
| **IDENTITY subtotal** | **~38 KB** | **~17,100** | **~11,400** |
| WARM decisions.md | 3-15 KB | 1,350-6,750 | 900-4,500 |
| HOT recent.md | 5-80 KB | 2,250-36,000 | 1,500-24,000 |

IDENTITY is fixed cost -- it loads every session regardless. WARM and HOT are variable and controlled by the compression cron jobs.

### Three load scenarios

**Scenario 1: After all cron jobs (optimal)**

All 4 cron scripts ran successfully. HOT trimmed to ~20 KB, WARM compressed to ~3 KB.

```
IDENTITY: 17,100 + WARM: 1,350 + HOT: 9,000 = 27,450 tokens (2.7% of 1M)
```

This is the target operating state. The agent starts each session with clean, focused context.

**Scenario 2: End of day, before cron (loaded)**

Active day with 150+ messages. HOT grew to ~80 KB, WARM accumulated entries from trim-hot.

```
IDENTITY: 17,100 + WARM: 6,750 + HOT: 36,000 = 59,850 tokens (6.0% of 1M)
```

Still within acceptable range but agent quality starts degrading. The operator should run `/compact` manually or wait for cron.

**Scenario 3: Cron broken, gateway writing for a week (worst case)**

Cron jobs failed silently. No compression for 7 days. HOT has accumulated ~200 KB of raw logs.

```
IDENTITY: 17,100 + WARM: 6,750 + HOT: 90,000 = 113,850 tokens (11.4% of 1M)
```

Agent noticeably ignores instructions buried in IDENTITY. Emergency trim (>20 KB) will eventually cap HOT at ~600 lines, but quality is already degraded.

### Key insight

Even at maximum load, the architecture uses only 6-11% of the Opus context window. The 1M token limit is never the bottleneck. The compression system exists not to save money but to keep context CLEAN -- an agent with 80 KB of raw conversation logs performs worse than one with 20 KB of structured facts, because attention is finite even when context is not.

### Reference limits

- Opus 4.6 / Sonnet 4.6 context window: 1,000,000 tokens (~830K usable after system prompt)
- CLAUDE.md recommended size: under 200 lines (beyond that Claude starts ignoring instructions)
- @import max recursion depth: 5 hops
- Sonnet compression (compress-warm.sh) keeps WARM compact at ~3 KB even with daily additions from trim-hot.sh
