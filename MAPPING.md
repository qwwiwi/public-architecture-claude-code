# File Mapping -- OpenClaw vs Claude Code vs Our Architecture

How three systems name and use the same concepts. Use this to understand where each file comes from and why we chose our structure.

## Identity Files

| Concept | OpenClaw | Claude Code (official) | Our Architecture | Loads |
|---------|----------|----------------------|-----------------|-------|
| Agent personality, values, tone | `SOUL.md` | `CLAUDE.md` | `CLAUDE.md` (SOUL section) | always |
| Agent name, creature, avatar | `IDENTITY.md` | _(inside CLAUDE.md)_ | _(inside CLAUDE.md)_ | always |
| Operating rules, models, subagents | `AGENTS.md` | _(inside CLAUDE.md)_ | `core/AGENTS.md` (@include) | always |
| Operator profile | `USER.md` | _(inside CLAUDE.md or rules/)_ | `core/USER.md` (@include) | always |
| Infrastructure, servers, services | `TOOLS.md` | _(inside CLAUDE.md)_ | `tools/TOOLS.md` (@include) | always |
| Boundaries, permissions, red zones | _(inside AGENTS.md)_ | `.claude/rules/*.md` | `core/rules.md` (@include) | always |
| First-run setup ritual | `BOOTSTRAP.md` (deleted after) | _(none)_ | _(none -- install.sh replaces this)_ | once |
| Periodic heartbeat checklist | `HEARTBEAT.md` | _(none)_ | _(cron scripts instead)_ | always |

### Why we split CLAUDE.md into multiple files

Claude Code officially uses one `CLAUDE.md` per scope. OpenClaw uses 7 separate files.

We use **1 CLAUDE.md + @include** -- best of both:
- Claude Code sees one entry point (CLAUDE.md)
- Content is split into focused files (like OpenClaw)
- `@include` directive loads them automatically
- Each file stays under 200 lines (Anthropic recommendation)

```
CLAUDE.md                    # SOUL: personality, principles (entry point)
  @core/AGENTS.md            # models, subagents, pipelines
  @core/USER.md              # operator profile
  @core/rules.md             # boundaries, security
  @tools/TOOLS.md            # servers, services, paths
  @core/warm/decisions.md    # rolling 14-day memory
  @core/hot/recent.md        # rolling 24h journal
```

---

## Memory

| Concept | OpenClaw | Claude Code (official) | Our Architecture |
|---------|----------|----------------------|-----------------|
| Short-term journal | `memory/YYYY-MM-DD.md` (daily) | _(auto memory)_ | `core/hot/recent.md` (24h rolling) |
| Medium-term decisions | _(inside MEMORY.md)_ | _(auto memory)_ | `core/warm/decisions.md` (14d rolling) |
| Long-term archive | `MEMORY.md` (manual curated) | `~/.claude/projects/*/memory/MEMORY.md` | `core/MEMORY.md` (cold, on-demand) |
| Lessons from mistakes | _(inside MEMORY.md)_ | _(auto memory)_ | `core/LEARNINGS.md` (on-demand) |
| Semantic search | _(none)_ | _(none)_ | OpenViking L4 (HTTP API) |

### How memory compression works

```
Gateway writes -> HOT (24h, full dialogue)
                    |
              trim-hot.sh (cron 05:00 UTC)
                    |
                    v
               WARM (14d, compressed key facts)
                    |
              rotate-warm.sh (cron 04:30 UTC)
                    |
                    v
               COLD (archive, on-demand Read)
                    |
              memory-rotate.sh (cron 21:00 UTC)
                    |
                    v
               archive/YYYY-MM.md (monthly files)
```

OpenClaw uses daily files (`memory/YYYY-MM-DD.md`) and a silent pre-compaction flush.
Claude Code uses auto memory (Claude decides what to save).
We use **cron + Sonnet compression** -- automated, predictable, agent-independent.

---

## Configuration

| Concept | OpenClaw | Claude Code (official) | Our Architecture |
|---------|----------|----------------------|-----------------|
| Global config | `~/.openclaw/config.json` | `~/.claude/settings.json` | `~/.claude/settings.json` |
| Project config | `openclaw.json` | `.claude/settings.json` | `.claude/settings.json` |
| Local overrides | _(env vars)_ | `.claude/settings.local.json` | `.claude/settings.local.json` |
| Language rules | _(inside AGENTS.md)_ | `~/.claude/rules/*.md` | `~/.claude/rules/*.md` |
| Path-specific rules | _(none)_ | `rules/*.md` with `paths:` frontmatter | `rules/*.md` with `paths:` frontmatter |

---

## Skills

| Concept | OpenClaw | Claude Code (official) | Our Architecture |
|---------|----------|----------------------|-----------------|
| Skill definition | `skills/*/config.json` + `handler.js` | `skills/*/SKILL.md` | `skills/*/SKILL.md` |
| Skill trigger | JSON config | YAML frontmatter in SKILL.md | YAML frontmatter in SKILL.md |
| Shared skills | `~/.openclaw/skills/` (global) | `~/.claude/skills/` (global) | `shared/skills/` (symlinked) |
| Skill arguments | `{{input}}` | `$ARGUMENTS`, `$0`, `$1` | `$ARGUMENTS` |
| Skill isolation | process fork | `context: fork` frontmatter | `context: fork` frontmatter |
| Skill model override | _(none)_ | `model:` frontmatter | `model:` frontmatter |

---

## Multi-Agent

| Concept | OpenClaw | Claude Code (official) | Our Architecture |
|---------|----------|----------------------|-----------------|
| Agent isolation | `~/.openclaw/workspace-{id}/` | separate project dirs | `~/.claude-lab/{agent}/.claude/` |
| Shared resources | _(none built-in)_ | _(none built-in)_ | `~/.claude-lab/shared/` |
| Inter-agent messaging | _(none built-in)_ | _(none built-in)_ | message bus (inbox per agent) |
| Subagent definitions | _(none)_ | `.claude/agents/*.md` | `.claude/agents/*.md` |
| Gateway/router | _(none)_ | _(none)_ | `shared/gateway/` (Telegram) |
| Secrets sharing | per-agent `auth-profiles.json` | _(none built-in)_ | `shared/secrets/` (one folder) |

---

## Folder Naming

| Our path | Why this name | Based on |
|----------|---------------|----------|
| `~/.claude/` | Official Claude Code global dir | Claude Code official |
| `~/.claude-lab/` | Multi-agent workspace root | Our convention (lab = workspace) |
| `~/.claude-lab/shared/` | Resources shared across agents | Our convention |
| `~/.claude-lab/{agent}/.claude/` | Per-agent project directory | Claude Code project scope |
| `core/` | Identity + memory files | Our convention (core = essential) |
| `core/warm/` | 14-day rolling memory | Our convention (warm = recent) |
| `core/hot/` | 24h rolling journal | Our convention (hot = very recent) |
| `tools/` | Infrastructure descriptions | OpenClaw convention (TOOLS.md) |
| `skills/` | Callable commands | Claude Code official |
| `agents/` | Subagent definitions | Claude Code official |
| `scripts/` | Cron jobs, utilities | Our convention |

---

## Key Decisions

### What we took from OpenClaw
- Separate identity files (SOUL, AGENTS, USER, TOOLS) instead of one giant CLAUDE.md
- Explicit MEMORY.md as curated archive
- LEARNINGS.md for mistake tracking
- Per-agent workspace isolation

### What we took from Claude Code
- `@include` directive to compose CLAUDE.md from parts
- `.claude/rules/` for language-specific rules with path matching
- `.claude/skills/` with SKILL.md format and YAML frontmatter
- `.claude/agents/` for subagent definitions
- `settings.json` for hooks, permissions, config

### What we added
- **4-layer memory** (HOT -> WARM -> COLD -> L4 semantic) with cron compression
- **Shared resources** (`shared/secrets/`, `shared/skills/`, `shared/gateway/`)
- **Telegram gateway** routing multiple bots to multiple agents
- **Sonnet compression** for memory management (not just truncation)
- **Message bus** for inter-agent communication
- **OpenViking** for semantic memory search
