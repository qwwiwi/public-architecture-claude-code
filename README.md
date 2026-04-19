# Claude Code Agent Architecture

Universal architecture for Claude Code agents with local memory layers, hooks, self-improvement, and semantic search.

## Quick Install

```bash
git clone https://github.com/qwwiwi/public-architecture-claude-code.git
cd public-architecture-claude-code
bash install.sh
```

The script asks agent name, role, model, your name -- then creates the full workspace with all files. Run again to add more agents.

## Working Context: 400K (not 1M)

Base context window of Claude Code is 1,000,000 tokens (1M). But model quality degrades well before that limit. We set one env variable:

```json
{
  "env": {
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "400000"
  }
}
```

Auto-compact triggers at 400K instead of default 800K. Recommendation from Boris Cherny (Claude Code lead at Anthropic). **All calculations below use 400K as the working context.**

This is the **only** env variable you need to change. No MAX_THINKING_TOKENS, no SUBAGENT_MODEL, no AUTOCOMPACT_PCT -- leave defaults.

## Folder Structure

```
.claude/
├── CLAUDE.md              # SOUL -- identity, role, style, boundaries
├── settings.json          # Settings: env vars, hooks, permissions
├── core/
│   ├── USER.md            # Owner profile: name, channels, product, communication style
│   ├── rules.md           # Operational rules: security, boundaries, formatting
│   ├── AGENTS.md          # Agent directory (on-demand, NOT loaded at startup)
│   ├── MEMORY.md          # Cold memory, lessons index
│   ├── LEARNINGS.md       # Lesson archive from mistakes
│   ├── warm/
│   │   └── decisions.md   # Key decisions (last 14 days)
│   └── hot/
│       ├── handoff.md     # Last 10 entries from conversation log (loaded at startup)
│       ├── recent.md      # Full conversation log (NOT loaded into session)
│       └── archive/       # Old logs by date
├── tools/
│   └── TOOLS.md           # Tool/service directory (on-demand, NOT loaded at startup)
├── skills/                # Skills -- reusable capabilities
│   ├── present/SKILL.md   # HTML visualization
│   └── .../SKILL.md       # Other skills
├── hooks/                 # Shell scripts for automation
│   ├── block-dangerous.sh # Blocks rm -rf, force push, DROP TABLE
│   ├── protect-files.sh   # Protects .env, .pem, .key, secrets/*
│   ├── activity-logger.sh # Logs every tool call to JSONL (PostToolUse)
│   ├── session-logger.sh  # Logs session start/stop events
│   └── ...
├── logs/
│   └── activity/          # Daily JSONL activity logs (chmod 600)
│       ├── 2026-04-15.jsonl
│       └── ...
└── scripts/               # Cron scripts for memory rotation
    ├── trim-hot.sh        # HOT > 24h -> Sonnet compresses -> WARM
    ├── rotate-warm.sh     # WARM > 14 days -> COLD
    ├── rotate-activity-logs.sh  # Activity logs > 30 days -> delete
    └── ...
```

### What loads at startup

Only 4 files load via `@include` (plus global CLAUDE.md and rules):

| File | What it does | Size | Tokens |
|------|-------------|------|--------|
| ~/.claude/CLAUDE.md | Global rules for all projects (workflow, git, security) | 7 KB | ~3,200 |
| ~/.claude/rules/*.md | Language rules (python.md, typescript.md, bash.md) | 1 KB | ~430 |
| CLAUDE.md (SOUL) | Agent identity, style, role, boundaries, coordination | 8 KB | ~3,500 |
| core/USER.md | Owner profile: name, channels, product, communication style | 2 KB | ~765 |
| core/rules.md | Operational rules: security, boundaries, formatting | 4 KB | ~1,935 |
| core/warm/decisions.md | Key decisions from last 14 days | 3 KB | ~1,400 |
| core/hot/handoff.md | Last 10 entries from conversation log (NOT the full HOT) | 1-4 KB | 450-1,800 |
| **TOTAL** | | **26-29 KB** | **~11-13K** |

**11-13K tokens out of 400K working context = ~3%.** The remaining 97% is for actual work.

`recent.md` (the full conversation log) is **NOT loaded** into the session -- only `handoff.md` (last 10 entries). AGENTS.md and TOOLS.md are also NOT loaded at startup -- the agent reads them via Read tool on demand. This saves ~18K tokens.

## 4 Memory Layers

```
IDENTITY ──── always in context (CLAUDE.md, USER.md, rules.md)
WARM 14d ──── always in context (decisions.md)
HOT ────────── handoff.md at startup (last 10 entries, NOT full recent.md)
COLD ──────── Read tool on demand (MEMORY.md, LEARNINGS.md)
L4 ────────── Semantic search on demand (OpenViking or similar)
```

- **IDENTITY + WARM + HOT** -- loaded automatically at startup via `@include`
- **COLD** -- agent reads via Read tool when old context is needed
- **L4** -- agent searches via curl when information older than 24 hours is needed

## Cron Scripts: Automatic Memory Rotation

| Time | Script | What it does |
|------|--------|-------------|
| 04:30 | rotate-warm.sh | WARM older than 14 days -> COLD |
| 05:00 | trim-hot.sh | HOT older than 24h -> Sonnet compresses -> WARM |
| 06:00 | compress-warm.sh | WARM over 10KB -> Sonnet recompresses |
| 06:30 | ov-session-sync.sh | HOT + WARM -> semantic search (L4) |
| 21:00 | memory-rotate.sh | COLD over 5KB -> archive/YYYY-MM.md |
| 05:00 | rotate-activity-logs.sh | Activity logs older than 30 days -> delete |

Order matters: rotate WARM first, then compress HOT, then recompress WARM, then sync to L4.

Sonnet is used for compression (not Opus) -- 4x cheaper with same summarization quality.

## Hooks: Automation Without Agent Involvement

Hooks are shell commands that execute on Claude Code lifecycle events. CLAUDE.md is a recommendation (~80% compliance). Hooks are **enforcement (100%)**.

### Basic hooks (any agent)

| Hook | Event | Purpose |
|------|-------|---------|
| **block-dangerous.sh** | PreToolUse -> Bash | Blocks rm -rf, git push --force, DROP TABLE, curl \| bash. Exit 2 = operation cancelled |
| **protect-files.sh** | PreToolUse -> Edit\|Write | Protects .env, .pem, .key, secrets/*, package-lock.json from accidental modification |
| **log-commands.sh** | PostToolUse -> Bash | Logs every command to command-log.txt. Audit trail |

### Advanced hooks (multi-agent system)

| Hook | Event | Purpose |
|------|-------|---------|
| **session-bootstrap.sh** | SessionStart | Loads top-5 lessons from episodes.jsonl, checks inbox, sets heartbeat online |
| **auto-recall.mjs** | UserPromptSubmit | Sends prompt to semantic search, returns relevant memories. Long-term memory without CLAUDE.md overhead |
| **correction-detector.sh** | UserPromptSubmit | Catches correction phrases ("не надо", "неправильно") -- triggers learning capture |
| **review-reminder.sh** | PostToolUse | After 10+ edits, reminds to run code review before commit |
| **flush-to-openviking.sh** | PreCompact | Saves HOT+WARM to semantic search before compaction. Nothing is lost |
| **write-handoff.sh** | Stop | Generates handoff.md -- last entries, active topics, modified files. Next session starts where this one left off |

## Activity Logging: Tool Call Audit Trail

Every tool call the agent makes (Bash, Read, Edit, Write, Grep, Glob, Agent, Skill) is logged to local JSONL files automatically via Claude Code hooks. **No LLM involvement** -- pure shell scripts, zero network calls.

### Why

- **Skill usage analysis** -- which skills are used, how often, for which tasks. Identify underused skills
- **Error tracking** -- every failed tool call is logged with error details. Find patterns in failures
- **Decision analysis** -- understand how the agent approaches tasks (tool sequence, subagent dispatch)
- **Efficiency auditing** -- detect redundant operations, excessive file reads, unnecessary tool calls

### How it works

```
PostToolUse ──────> activity-logger.sh ──> logs/activity/YYYY-MM-DD.jsonl
PostToolUseFailure ─┘
SessionStart ─────> session-logger.sh ──┘
Stop ─────────────┘
```

Two hooks in `settings.json`:
- **activity-logger.sh** -- fires on every tool call (success or failure). Extracts tool name, input details, errors
- **session-logger.sh** -- fires on session start and stop. Marks session boundaries in the same log file

### JSONL schema

```json
{
  "ts": "2026-04-15T22:03:14Z",
  "session": "53ab607f-9984-40f4-abbb-f549939862c6",
  "event": "PostToolUse",
  "tool": "Bash",
  "detail": {"command": "git status", "description": "Show status"},
  "error": null,
  "cwd": "/home/user/.claude-lab/agent/.claude"
}
```

Detail fields vary by tool:

| Tool | Detail fields |
|------|--------------|
| Bash | command, description |
| Read | file_path, offset, limit |
| Edit/Write | file_path |
| Grep | pattern, path, glob |
| Glob | pattern, path |
| Agent | description, subagent_type, model |
| Skill | skill, args |

### Analytics queries

```bash
# Most used tools today
jq -r '.tool' logs/activity/2026-04-15.jsonl | sort | uniq -c | sort -rn

# All Skill invocations (which skills, when, what args)
jq 'select(.tool == "Skill")' logs/activity/*.jsonl

# Errors only
jq 'select(.error != null)' logs/activity/*.jsonl

# Session count per day
grep -c '"SessionStart"' logs/activity/*.jsonl

# Tools per session
jq -r '[.session, .tool] | @tsv' logs/activity/*.jsonl | sort | uniq -c | sort -rn
```

### Security

- Log files are `chmod 600` (umask 077) -- only the agent owner can read them
- Tool output/response is **not logged** -- only tool name and input parameters
- Bash commands are logged in full (for audit), but secrets in env vars are not captured
- Logs rotate after 30 days via `rotate-activity-logs.sh` (cron at 05:00 UTC)

### Design decisions

- **Single jq call** per hook invocation -- all JSON is built inside jq, no shell string interpolation (prevents JSON injection)
- **Best-effort** -- no `set -e`, fallback error entry on parse failure. A broken hook should never block the agent
- **No network calls** -- pure local disk I/O, 5-second timeout
- **Daily rotation** -- one file per day, easy to grep by date range

## Model Strategy

**Opus for code and decisions, Sonnet for subagents.** No half-measures -- code quality requires the best model. Subagents handle volume.

| Model | ID | Role | Use for |
|---|---|---|---|
| **Opus 4.6** | claude-opus-4-6 | **Primary** | Code writing, review, planning, coordination |
| **Sonnet 4.6** | claude-sonnet-4-6 | **Subagents** | Research, search, exploration, memory compression |
| **Codex GPT-5.4** | OpenAI | **Double review** | Code review via `/codex:review` and `/codex:adversarial-review` (plugin `openai/codex-plugin-cc`) |
| **Sonar** | Perplexity | **Optional** | Web research, fact-checking |

| Model | Input | Output | Relative cost |
|-------|-------|--------|---------------|
| Sonnet 4.6 | $3/M | $15/M | 1x (baseline for subagents) |
| Opus 4.6 | $15/M | $75/M | ~5x (worth it for code quality) |

On Max subscription ($100-200/mo) all models are included. Cost = rate limit consumption, not $. Sonnet for subagents = faster responses + less context consumed.

> **Opus via OpenRouter -- NEVER.** Use native Anthropic API or Anthropic Max subscription.

## Terse Mode: Output Token Savings

Output tokens cost 5x more than input (Opus: $15 vs $75 per 1M tokens). At 400K working context, every token counts. Add to rules.md:

```markdown
## Output style
Drop: articles (a/an/the), filler, pleasantries, hedging.
Fragments OK. Short synonyms.
Pattern: [thing] [action] [reason]. [next step].
```

| Before | After | Savings |
|--------|-------|---------|
| "Sure! I'd be happy to help you with that. The issue is likely caused by a problem in the auth middleware." | "Bug in auth middleware. Token expiry check uses `<` not `<=`. Fix:" | ~75% |

## Learnings v2: Self-Improvement

The agent records lessons from mistakes. Not just "remember this" -- **systematically change the system** so the mistake doesn't repeat.

### Detection: correction-detector.sh

The hook (UserPromptSubmit) scans every user message for trigger words:

| Category | Trigger words |
|----------|--------------|
| Direct corrections | "не надо", "не нужно", "неправильно", "не так", "не делай", "перестань" |
| Accusatory questions | "почему ты", "зачем ты", "ты не", "ты забыла", "ты опять" |
| Broken state | "сломал", "сломала", "сломано", "не работает" |
| Repeated instructions | "я же говорил", "я уже говорил", "сколько раз" |

On match, the hook injects: "CORRECTION DETECTED. Record a learning via `learnings-engine.mjs capture`."

### Pipeline: from mistake to system change

```
User correction
  -> correction-detector.sh (catches trigger)
  -> learnings-engine.mjs capture (writes to episodes.jsonl)
  -> learnings-engine.mjs score (computes rating)
  -> learnings-engine.mjs lint (finds HOT/STALE/PROMOTE candidates)
  -> learnings-engine.mjs promote (changes the system)
```

### Episode format (episodes.jsonl)

```json
{
  "id": "EP-20260414-001",
  "ts": "2026-04-14T15:03:00Z",
  "type": "correction",
  "source": "prince",
  "context": "what happened",
  "error": "what went wrong",
  "rule": "rule for the future",
  "impact": "high",
  "tags": ["workflow", "git"],
  "freq": 1,
  "status": "active"
}
```

### Scoring

Each episode gets a composite score (0-1):

| Factor | Weight | How it's calculated |
|--------|--------|-------------------|
| Recency | 40% | Linear decay over 30 days |
| Frequency | 30% | How many times repeated (cap: 3) |
| Impact | 30% | critical=1.0, high=0.7, medium=0.4, low=0.1 |

Automatic triggers:
- **Score > 0.8** or **freq >= 3** -> candidate for PROMOTE (system change)
- **Score < 0.15** -> STALE (archive, lesson no longer relevant)
- **freq >= 3** -> HOT (rule isn't working, need to change the system, not just remember)

### Reliability pyramid (weak to strong)

1. **Session memory** -- lost on compact/reset
2. **episodes.jsonl** -- top-5 loaded at startup, fades after 30 days
3. **LEARNINGS.md** -- NOT loaded into context, but used to create skills and update other files
4. **TOOLS.md / SKILL.md** -- found by grep on demand
5. **CLAUDE.md / rules.md** -- always in context
6. **Scripts / Hooks** -- runs automatically, without agent involvement

The more critical the mistake -- the higher up the pyramid it gets promoted. Production bug -> straight to hook/script.

### LEARNINGS.md: not in context, but essential

LEARNINGS.md is **NOT loaded** into the session context (saves tokens). But it's the knowledge base from which:

- **Skills are created** -- repeating patterns get formalized into SKILL.md
- **TOOLS.md is updated** -- tool-related lessons go to the reference
- **rules.md is patched** -- critical rules get promoted to always-in-context
- **Hooks are written** -- the most important rules become automatic scripts

### Promotion targets by tags

| Episode tags | Target file | Needs owner OK? |
|-------------|-------------|-----------------|
| stack, models, tools | TOOLS.md | No (green zone) |
| workflow, communication | CLAUDE.md or SKILL.md | No (green zone) |
| security, git | rules.md | Yes (red zone) |
| config, scp | rules.md | Yes (red zone) |

## Three Load Scenarios

All percentages are relative to the **400K working context** (not 1M base):

| Scenario | Tokens | % of 400K |
|----------|--------|-----------|
| After cron (optimal) | ~27K | ~7% |
| End of day, before cron | ~60K | ~15% |
| Cron broken for a week | ~114K | ~29% |

At worst case (29% consumed by memory), only 284K tokens remain for actual work. Compression exists for **context cleanliness** and maintaining agent quality.

## Semantic Search (L4)

L4 is a local semantic database for long-term memory. The agent searches by meaning, not keywords.

How it works:
1. Stop hook or cron (06:30 UTC) pushes HOT + WARM to the semantic database
2. The database creates embeddings automatically
3. At next session, auto-recall.mjs searches for relevant information

Each agent writes to its own namespace but searches across all. Cross-agent search out of the box.

## Repositories and Tests

| Repo | Description |
|------|-------------|
| **[public-architecture-claude-code](https://github.com/qwwiwi/public-architecture-claude-code)** | Architecture, templates, scripts, install.sh |
| **[jarvis-telegram-gateway](https://github.com/qwwiwi/jarvis-telegram-gateway)** | Gateway: Telegram -> Claude Code |
| **[architecture-brain-tests](https://github.com/qwwiwi/architecture-brain-tests)** | 800 tests verifying everything above |

Test categories: T20 (security), T26 (models), T27 (COMPACT_WINDOW), T28 (Learnings v2), and 25+ more.

## Two Ways to Connect Telegram

| Method | Use Case | Repo |
|--------|----------|------|
| **claude-code-telegram** (plugin) | Interactive coding via Telegram | [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) |
| **Telegram Gateway** (standalone) | Autonomous multi-agent: voice, progress, memory, 3+ bots | [qwwiwi/jarvis-telegram-gateway](https://github.com/qwwiwi/jarvis-telegram-gateway) |

## Documentation

### Start Here (beginners)

| File | Description |
|------|-------------|
| [SETUP-GUIDE.md](SETUP-GUIDE.md) | End-to-end: from zero to working agent |
| [FIRST-AGENT.md](FIRST-AGENT.md) | Your first agent: step by step from workspace to Telegram |
| [COMMANDS-QUICKREF.md](COMMANDS-QUICKREF.md) | Command cheatsheet: /plan, /tdd, /code-review |
| [TOKEN-OPTIMIZATION.md](TOKEN-OPTIMIZATION.md) | Token optimization: 400K working context, model strategy |
| [AGENT-LAWS.md](AGENT-LAWS.md) | Hierarchy, rules, and agent laws: 9 principles, autonomy zones |

### Architecture (deep dive)

| File | Description |
|------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full architecture diagram and flows |
| [MEMORY.md](MEMORY.md) | 4-layer memory system with token budget |
| [LEARNINGS.md](LEARNINGS.md) | Self-improvement: learnings feedback loop |
| [MULTI-AGENT.md](MULTI-AGENT.md) | Multi-agent system: 3 agents, 3 Telegram bots, 1 gateway |
| [FILES-REFERENCE.md](FILES-REFERENCE.md) | Complete file map: role, who writes, when it loads |
| [STRUCTURE.md](STRUCTURE.md) | Directory layout (single or multi-agent) |

### Reference

| File | Description |
|------|-------------|
| [SKILLS.md](SKILLS.md) | How to create and configure skills |
| [SUBAGENTS.md](SUBAGENTS.md) | Custom subagents: agents/*.md format, built-in types |
| [HOOKS.md](HOOKS.md) | Lifecycle hooks: auto-format, validation, security |
| [AGENT-LAWS.md](AGENT-LAWS.md) | Hierarchy, rules, and agent laws |
| [MAPPING.md](MAPPING.md) | OpenClaw vs Claude Code vs our architecture |
| [CHECKLIST.md](CHECKLIST.md) | Step-by-step: create a new agent from scratch |

## License

MIT
