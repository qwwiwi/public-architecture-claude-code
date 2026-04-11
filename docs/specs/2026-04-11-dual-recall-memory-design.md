# Dual Recall Memory Architecture

**Date:** 2026-04-11
**Status:** Approved
**Author:** {{AGENT_NAME}} + Operator

## Problem

Agent loads CLAUDE.md, USER.md, rules.md, decisions.md, handoff.md at session start (~500 lines, ~6.5K tokens). But TOOLS.md (354 lines), AGENTS.md (137 lines), LEARNINGS.md (growing) are NOT in context -- agent reads them manually via Read tool only when it guesses they're needed.

This causes:
- Missed context: agent doesn't know the right SSH command, port, or API path
- Wasted Opus tokens: reading 500-line files on expensive model
- No automatic recall: agent must decide to search, often doesn't

## Solution: Dual Recall on UserPromptSubmit

Two parallel hooks fire on every user message, before the agent starts thinking:

```
User sends message
    |
UserPromptSubmit (parallel):
    +-- Hook 1: auto-recall.mjs --> OV semantic search
    |   --> <relevant-memories> (dialogs, preferences, entities)
    |
    +-- Hook 2: local-recall.mjs --> Sonnet API
        --> reads TOOLS.md + AGENTS.md + LEARNINGS.md
        --> Sonnet extracts only relevant lines
        --> <local-context> (IPs, commands, rules, lessons)
    |
Both results in additionalContext
    |
Agent (Opus) receives message + OV memories + local context
    |
Agent responds
```

## Components

### Hook 1: auto-recall.mjs (existing)

- **Location:** `~/{{MEMORY_PLUGIN_DIR}}/scripts/auto-recall.mjs`
- **Trigger:** UserPromptSubmit
- **Search scope:** {{MEMORY_SERVICE}} user + agent memories
- **Ranking:** base score + leaf boost + temporal boost + preference boost + lexical overlap
- **Output:** `<relevant-memories>` block in additionalContext
- **Timeout:** 8 seconds
- **Status:** Already implemented, no changes needed

### Hook 2: local-recall.mjs (new)

- **Location:** `~/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall.mjs`
- **Trigger:** UserPromptSubmit (parallel with Hook 1)
- **Timeout:** 10 seconds

**Flow:**
1. Receive JSON on stdin: `{"prompt": "user message text"}`
2. Read local files:
   - `$AGENT_WORKSPACE/tools/TOOLS.md`
   - `$AGENT_WORKSPACE/core/AGENTS.md`
   - `$AGENT_WORKSPACE/core/LEARNINGS.md`
3. Call Anthropic API (Sonnet):
   - System: "You are a context extractor. From the provided reference files, find ONLY lines relevant to the user's query. Return 5-15 lines max. If nothing is relevant, return empty."
   - User: "Query: {prompt}\n\n---TOOLS.MD---\n{tools}\n\n---AGENTS.MD---\n{agents}\n\n---LEARNINGS.MD---\n{learnings}"
4. Return Sonnet's response as additionalContext:
   ```
   <local-context source="TOOLS.md, AGENTS.md, LEARNINGS.md">
   {relevant lines from Sonnet}
   </local-context>
   ```
5. On timeout/error: return empty additionalContext + `<local-recall-failed/>`

**API details:**
- Model: claude-sonnet-4-6
- Max tokens: 500
- Temperature: 0
- Input: ~4,000 tokens (files + prompt)
- Output: ~200-500 tokens
- Auth: `ANTHROPIC_API_KEY` env var (from Max subscription OAuth, no separate key needed)

### settings.json configuration

```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "node ~/{{MEMORY_PLUGIN_DIR}}/scripts/auto-recall.mjs",
          "timeout": 8
        },
        {
          "type": "command",
          "command": "node ~/{{MEMORY_PLUGIN_DIR}}/scripts/local-recall.mjs",
          "timeout": 10
        }
      ]
    }
  ]
}
```

## Error Handling: 3-Level Fallback

```
Level 1: Sonnet hook + OV hook (normal mode)
    | timeout/error
Level 2: Opus reads files via Read tool (ONE TIME fallback)
    | simultaneously
Level 3: Create task "fix hook {name}, reason: {error}"
    + Check status.anthropic.com for API outage
```

**Key rule:** Opus fallback is a one-time bandage, NOT a permanent mode. If a hook breaks, it becomes a task to fix.

## Model Distribution

| Task | Model | Why |
|------|-------|-----|
| Research, search, file reading, analysis | Sonnet | Cheaper, faster for search tasks |
| Coordination, code writing, final response | Opus | Stronger for synthesis and generation |
| Memory extraction ({{MEMORY_SERVICE}} VLM) | GPT-4o-mini | Best cost/quality for fact extraction |
| Embeddings ({{MEMORY_SERVICE}} search) | text-embedding-3-small | OpenAI, $0.02/1M tokens |
| Voice transcription | Groq Whisper | Free, fast |

## Access Zones (updated)

| Zone | Files | Who changes |
|------|-------|------------|
| **RED (read-only)** | CLAUDE.md, rules.md | Operator only |
| **YELLOW (self-edit)** | USER.md, AGENTS.md, TOOLS.md, warm/decisions.md, hot/recent.md | Agent on trigger |
| **GREEN (full autonomy)** | LEARNINGS.md, MEMORY.md, skills/*, agents/*.md, feedback_*.md | Agent freely |

## Memory Architecture (4 layers + dual recall)

```
Session start:
  CLAUDE.md + USER.md + rules.md + decisions.md + handoff.md
  (~500 lines, ~6.5K tokens, always in context)

Every message (parallel hooks):
  +-- OV semantic search --> <relevant-memories>
  +-- Sonnet local recall --> <local-context>

On demand (Read tool, Opus fallback only):
  TOOLS.md, AGENTS.md, LEARNINGS.md

Daily (05:00, memory-compact.sh):
  recent.md --> extract key facts --> decisions.md
  decisions.md > 14 sections --> oldest --> MEMORY.md
  LEARNINGS.md > 12KB --> archive old entries

Continuous (gateway):
  Every dialog --> recent.md (HOT)
  Every dialog --> {{MEMORY_SERVICE}} (L4, background)
```

## Cost Estimate

| Component | Per message | Monthly (1500 msgs) |
|-----------|-----------|---------------------|
| Sonnet local-recall | ~$0.015 | ~$22.50 |
| OV auto-recall | $0 (local search) | $0 |
| GPT-4o-mini extraction | ~$0.002 | ~$3.00 |
| Embeddings | ~$0.0001 | ~$0.15 |
| **Total memory system** | **~$0.017** | **~$25.65** |

## Scaling to Other Agents

- `local-recall.mjs` reads paths from `$AGENT_WORKSPACE` env var
- Same script works for any agent ({{AGENT_2_NAME}}, future agents)
- Each agent has own TOOLS.md/AGENTS.md/LEARNINGS.md
- Config in per-agent settings.json

## Files Changed

| File | Action |
|------|--------|
| `local-recall.mjs` | Create (new hook script) |
| `settings.json` (per agent) | Add second UserPromptSubmit hook |
| `LEARNINGS.md` | Updated zones in public architecture repo |
| `FILES-REFERENCE.md` | Updated USER.md zone |
| `MEMORY.md` (architecture doc) | Updated USER.md mutability |
| `templates/AGENTS.md.template` | Updated zones |
| `templates/TOOLS.md.template` | Updated zones |

## Open Items (next spec)

- **LEARNINGS registry with scoring** -- lesson-audit cron, score per lesson, auto-archive low-score
- **Symlinks** for USER.md + AGENTS.md (Claude Code task, in progress)
- **Cleanup .bak files** on all servers, backups only to DO Spaces
