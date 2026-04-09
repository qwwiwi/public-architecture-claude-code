# Files Reference -- Complete Map

Every file in the agent workspace, its role, who fills it, when it loads, and access rules.

## Legend

- **Loads:** `always` = every session start, `on-demand` = Read tool / Skill tool, `never` = not loaded
- **Writer:** who creates/updates the file
- **Access:** who can read/modify

---

## Layer 1: Global (`~/.claude/`)

Shared across ALL agents on this machine. Loaded every session.

| File | Role | Loads | Writer | Access |
|------|------|-------|--------|--------|
| **CLAUDE.md** | Global rules, code conventions, git policy, project paths | always | operator (manual) | all agents read, only operator edits |
| **rules/bash.md** | Bash coding standards: `set -euo pipefail`, quoting | always | operator (manual) | all agents read, only operator edits |
| **rules/python.md** | Python standards: type hints, pathlib, Google docstrings | always | operator (manual) | all agents read, only operator edits |
| **rules/typescript.md** | TS standards: strict, no any, Zod, interfaces | always | operator (manual) | all agents read, only operator edits |

**Who can touch:** Only the operator. Agents NEVER modify global files.

---

## Layer 2: Identity (`{workspace}/.claude/`)

Per-agent identity. Loaded every session via `@include` directives in CLAUDE.md.

| File | Role | Loads | Writer | Access |
|------|------|-------|--------|--------|
| **CLAUDE.md** | SOUL -- agent character, personality, principles, priorities, workflow rules. Contains `@include` directives that pull in other files | always | operator (manual) | agent reads, only operator edits |
| **core/AGENTS.md** | Operating rules: models, message bus paths, subagent config, cross-review rules, pipelines, analytics | always (@include) | operator (manual) | agent reads, only operator edits |
| **core/USER.md** | Operator profile: name, timezone, channels, products, communication style | always (@include) | operator (manual) | agent reads, only operator edits |
| **core/rules.md** | Boundaries: what agent can/cannot do, red zones, security, git policy, Telegram rules | always (@include) | operator (manual) | agent reads, only operator edits |
| **tools/TOOLS.md** | Infrastructure map: servers, SSH, Docker, systemd, ports, GitHub, secrets paths | always (@include) | operator (manual) or agent with permission | agent reads, agent can suggest edits |

**Who can touch:** Operator only. These are the agent's constitution -- agent cannot self-modify identity.

---

## Layer 3: Memory -- WARM (`core/warm/`)

Rolling 14-day memory. Auto-compressed. Loaded every session.

| File | Role | Loads | Writer | Access |
|------|------|-------|--------|--------|
| **warm/decisions.md** | Recent architectural/operational decisions. Topic-based key facts, auto-compressed by Sonnet | always (@include) | **trim-hot.sh** (cron, appends summaries from HOT), **compress-warm.sh** (cron, re-compresses), agent (during session for important decisions) | agent reads, cron writes, operator can edit |

**Lifecycle:**
1. `trim-hot.sh` (05:00 UTC) extracts old HOT entries -> appends to WARM as `## YYYY-MM-DD (auto-compressed)` sections
2. `compress-warm.sh` (06:00 UTC) re-compresses WARM if >10KB using Sonnet -> topic-based key facts
3. `rotate-warm.sh` (04:30 UTC) moves entries >14 days to COLD (MEMORY.md)
4. Agent can write important decisions during session

**Who can touch:** Cron scripts (automated), agent (append only), operator (full access).

---

## Layer 4: Memory -- HOT (`core/hot/`)

Rolling 72h journal. Every conversation turn recorded. Loaded every session.

| File | Role | Loads | Writer | Access |
|------|------|-------|--------|--------|
| **hot/recent.md** | Full conversation journal: timestamp, source tag, user snippet (200 chars), agent snippet (200 chars). Emergency trim at 20KB/600 lines | always (@include) | **gateway.py** (`append_to_hot_memory()` with fcntl lock), **trim-hot.sh** (cron, compresses old entries) | agent reads, gateway writes, cron trims |

**Entry format:**
```
### YYYY-MM-DD HH:MM [source_tag]
**Принц:** user message snippet (200 chars max)
**Agent:** agent response snippet (200 chars max)
```

**Source tags:** `own_text`, `own_voice`, `forwarded`, `external_media`

**Who can touch:** Gateway (append via fcntl lock), cron (trim/compress), agent (read only). Operator can edit.

---

## Layer 5: Memory -- COLD (`core/`)

Archive. NOT loaded into session context. Accessed via Read tool when needed.

| File | Role | Loads | Writer | Access |
|------|------|-------|--------|--------|
| **MEMORY.md** | Permanent archive of decisions rotated from WARM (>14 days). May contain months of history | on-demand (Read tool) | **rotate-warm.sh** (cron, appends old WARM entries), **memory-rotate.sh** (cron, archives to monthly files) | agent reads on-demand, cron writes |
| **LEARNINGS.md** | Lessons from mistakes: context, what went wrong, correct approach, rule | on-demand (Read tool) | agent (during session when learning occurs) | agent reads/writes, operator reads |
| **archive/*.md** | Monthly archives (`2026-04.md`, `2026-03.md`). MEMORY.md archived here when >5KB | never (manual Read) | **memory-rotate.sh** (cron) | read-only archive |

**Who can touch:** Cron scripts (automated archival), agent (append learnings), operator (full access).

---

## Layer 6: Semantic Memory -- OpenViking (L4)

External semantic database. NOT a file. Accessed via HTTP API.

| Resource | Role | Loads | Writer | Access |
|----------|------|-------|--------|--------|
| **viking://user/{agent}/memories/*** | Extracted semantic facts from conversations. LLM-powered extraction of preferences, decisions, entities | on-demand (curl) | **gateway.py** (`push_to_openviking()` in background thread) | agent searches via curl, gateway writes |

**Anti-pollution guards:**
- `forwarded` messages -> "Do NOT extract as operator's own preferences"
- `external_media` -> "Not operator's own words"
- `own_text`/`own_voice` -> no guard (operator's direct words)

**Who can touch:** Gateway (write via API), agent (search via curl), OpenViking service (manages storage).

---

## Layer 6b: Task Board -- Vibe Kanban (`shared/kanban/`)

Local kanban board shared by all agents. NOT loaded into context. Accessed via MCP tools.

| Resource | Role | Loads | Writer | Access |
|----------|------|-------|--------|--------|
| **shared/kanban/.vibe-kanban/** | SQLite database with tasks, statuses, worktree mappings | never (MCP access) | agents (via MCP), operator (via browser UI) | all agents RW via MCP, operator RW via browser |

**MCP tools available to every agent:**
- `list_workspaces` -- see all tasks and statuses
- `create_session` -- start working on a task (creates git worktree)
- `run_session_prompt` -- execute work in task's worktree
- `get_execution` -- check execution status

**Who can touch:** Operator (browser drag-and-drop), agents (MCP tools). Data is local SQLite, no cloud.

---

## Layer 7: Skills (`skills/`)

Callable skills. NOT loaded at session start. Loaded on-demand when Skill tool invoked.

| Path | Role | Loads | Writer | Access |
|------|------|-------|--------|--------|
| **skills/{name}/SKILL.md** | Skill definition: frontmatter (description, triggers), instructions, `$ARGUMENTS` | on-demand (Skill tool) | developer (manual) | agent reads when skill called |
| **skills/{name}/*.sh** | Shell scripts used by skill | on-demand (skill execution) | developer (manual) | agent executes |
| **skills/{name}/*.py** | Python scripts used by skill | on-demand (skill execution) | developer (manual) | agent executes |

**Example skills:** groq-voice, superpowers, gws, youtube-transcript, twitter, quick-reminders, markdown-new, excalidraw, datawrapper, perplexity-research, vibe-kanban

**Who can touch:** Developer/operator creates skills. Agent can use but not modify.

---

## Layer 8: Subagent Definitions (`agents/`)

MD files defining subagent behavior. NOT loaded at session start. Used when Agent tool spawns subagent.

| Path | Role | Loads | Writer | Access |
|------|------|-------|--------|--------|
| **agents/{name}.md** | Subagent definition: frontmatter (`model:`, `description:`), instructions | on-demand (Agent tool) | developer (manual) | parent agent reads when spawning |

**Who can touch:** Developer/operator creates. Agent reads when spawning subagents.

---

## Layer 9: Scripts (`scripts/`)

Cron jobs, utilities, automation. NOT loaded into context. Executed by cron or manually.

| File | Role | Runs | Writer |
|------|------|------|--------|
| **trim-hot.sh** | Compress HOT >24h entries via Sonnet | cron 05:00 UTC daily | developer |
| **compress-warm.sh** | Re-compress WARM via Sonnet if >10KB | cron 06:00 UTC daily | developer |
| **rotate-warm.sh** | Move WARM >14d to COLD | cron 04:30 UTC daily | developer |
| **memory-rotate.sh** | Archive COLD >5KB to monthly files | cron 21:00 UTC daily | developer |

**Who can touch:** Developer/operator creates and maintains. Cron executes. Agent can read but should not modify without permission.

---

## Layer 10: Secrets (`secrets/`)

Credentials. NEVER loaded into context. NEVER committed to git. NEVER logged.

All secrets in ONE shared folder: `~/.claude-lab/shared/secrets/`

| Path | Role | Access |
|------|------|--------|
| **shared/secrets/openviking.key** | OpenViking API key | scripts read, agent NEVER outputs |
| **shared/secrets/telegram/bot-token-{agent}** | Telegram bot token (per bot) | gateway reads, agent NEVER outputs |
| **shared/secrets/db-service-account.json** | Database service account | message bus reads, agent NEVER outputs |
| **shared/secrets/groq-api-key** | Groq Whisper API key | transcription reads, agent NEVER outputs |

**Who can touch:** Operator only. Agent NEVER reads content, NEVER copies between servers, NEVER commits, NEVER outputs to stdout/stderr.

---

## Layer 11: Gateway (`shared/gateway/`)

Telegram router. Shared across agents. NOT loaded into agent context.

| File | Role | Writer | Access |
|------|------|--------|--------|
| **gateway.py** | Main router: Telegram polling -> Claude subprocess -> response -> memory | developer | developer edits, systemd runs |
| **config.json** | Agent configs: bot token path, workspace, model, timeout, env vars | developer/operator | developer edits |
| **state/sid-{agent}-{chat}.txt** | Session ID persistence | gateway (auto) | gateway reads/writes |
| **media-inbound/*.ogg** | Downloaded voice/media files | gateway (auto) | agent reads via path, auto-cleanup |

**Who can touch:** Developer maintains code. Gateway auto-manages state and media. Agent reads media paths but doesn't modify gateway.

---

## Summary: Context Budget

### Always loaded (every session start)

| File | Size | Tokens (~) |
|------|------|------------|
| ~/.claude/CLAUDE.md | 7 KB | 3,200 |
| ~/.claude/rules/*.md | 1 KB | 430 |
| CLAUDE.md (SOUL) | 8 KB | 3,500 |
| core/AGENTS.md | 5 KB | 2,400 |
| core/USER.md | 2 KB | 765 |
| core/rules.md | 4 KB | 1,935 |
| core/warm/decisions.md | 3 KB | 1,400 |
| core/hot/recent.md | 8-30 KB | 3,600-13,500 |
| tools/TOOLS.md | 6 KB | 2,565 |
| **TOTAL** | **44-66 KB** | **19,800-29,700** |

### On-demand (not in startup context)

| Resource | Size | When |
|----------|------|------|
| MEMORY.md (COLD) | 5+ KB | Agent needs old decisions |
| LEARNINGS.md | varies | Agent needs past mistakes |
| Skills (15) | ~50 KB total | Skill tool invocation |
| Scripts (30) | ~70 KB total | Never in context |
| OpenViking | unlimited | curl search |
| Secrets | <1 KB each | Never in context |

---

## Access Matrix

| File | Operator | Agent | Gateway | Cron | Other Agents |
|------|----------|-------|---------|------|--------------|
| Global CLAUDE.md | RW | R | - | - | R |
| SOUL CLAUDE.md | RW | R | - | - | **NO** |
| AGENTS.md | RW | R | - | - | **NO** |
| USER.md | RW | R | - | - | **NO** |
| rules.md | RW | R | - | - | **NO** |
| TOOLS.md | RW | R (suggest) | - | - | **NO** |
| warm/decisions.md | RW | R+append | - | RW | **NO** |
| hot/recent.md | RW | R | W (append) | RW | **NO** |
| MEMORY.md | RW | R+append | - | W | **NO** |
| LEARNINGS.md | RW | RW | - | - | **NO** |
| Vibe Kanban | RW (browser) | RW (MCP) | - | - | **shared** (all agents) |
| Skills | RW | R+execute | - | - | shared |
| Secrets | RW | **NEVER** | R | R | **NEVER** |
| gateway.py | RW | R | execute | - | - |
| config.json | RW | R | R | - | - |

**Key rule:** Each agent's workspace is **private**. Other agents CANNOT read another agent's core/, hot/, warm/, MEMORY.md, LEARNINGS.md without explicit operator permission.
