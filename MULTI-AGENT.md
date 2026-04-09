# Multi-Agent Architecture

Multi-agent system with coordinator, specialized agents, shared state via OpenViking, and one Telegram gateway routing to multiple bots.

> **NOTE:** Agent names (Jarvis, Homer, Edith) are **examples**. When copying this architecture, replace them with your own names. The `install-local.sh` script handles renaming automatically.

## Overview

```
OPERATOR (you)
    │
    │  talks via 3 Telegram bots
    │
    ├──── @jarvis_bot ──┐
    ├──── @homer_bot ───┤
    └──── @edith_bot ───┤
                        ▼
              ┌──────────────────┐
              │  GATEWAY (1 proc) │
              │  routes by token  │
              └────────┬─────────┘
           ┌───────────┼───────────┐
           ▼           ▼           ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  JARVIS  │ │  HOMER   │ │  EDITH   │
     │ coordin. │ │  coder   │ │  inbox   │
     │ tasks    │ │  builds  │ │  knows   │
     └─────┬────┘ └─────┬────┘ └─────┬────┘
           └─────────────┼───────────┘
                         ▼
              ┌───────────────────┐
              │    OPENVIKING     │
              │ shared semantic DB │
              └───────────────────┘
```

> **Scaling:** Add a 4th agent = add a block in `config.json` + create bot in BotFather + run `install-local.sh`. One-click.

## Agents

> **These are example roles.** You might want: researcher + coder + devops, or marketer + coder + assistant, or any other combination.

| Agent | Role | Model | Subagents | Telegram bot |
|-------|------|-------|-----------|--------------|
| **Jarvis** | Coordinator | **Opus** | Many Sonnet subagents (search, analysis) | `@jarvis_bot` |
| **Homer** | Coder | **Opus** | Per-skill model (varies) | `@homer_bot` |
| **Edith** | Inbox / Knowledge | **Sonnet** | -- | `@edith_bot` |

### Why these models?

- **Jarvis** on Opus: coordinator needs deep reasoning for task routing, planning, multi-step workflows. Delegates bulk search/analysis to cheap Sonnet subagents.
- **Homer** on Opus: code quality is critical -- Opus produces better architecture, fewer bugs. Skills may use other models for specific tasks (e.g. Codex for review).
- **Edith** on Sonnet: inbox agent processes high volume of links, videos, articles. Sonnet handles parsing and summarization well at lower cost.

### Edith capabilities (universal inbox)

Edith is the "throw everything at it" agent. Send any link or content:

| Input | What Edith does |
|-------|----------------|
| **YouTube link** | Downloads audio, transcribes via Groq Whisper, summarizes |
| **Twitter/X link** | Reads tweet, thread, or profile |
| **Reddit link** | Reads post and top comments |
| **GitHub repo** | Clones, reads README, analyzes structure |
| **Instagram** | Fetches post via media downloader API |
| **Web article** | Fetches and reads full page |
| **PDF / document** | Downloads and extracts text |
| **Voice message** | Transcribes via Groq Whisper |

All processed content is stored in Edith's memory and pushed to OpenViking for cross-agent search.

## Gateway: 1 Process, 3 Bots

One gateway process polls all 3 bot tokens in parallel threads. Routes by `bot_token` to the correct agent workspace.

```
Telegram
┌──────────┐  ┌──────────┐  ┌──────────┐
│ @jarvis  │  │ @homer   │  │ @edith   │
│   bot    │  │   bot    │  │   bot    │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     ▼             ▼             ▼
┌─────────────────────────────────────────┐
│            GATEWAY (1 process)          │
│                                         │
│  token_1 → poll @jarvis  → agent=jarvis │
│  token_2 → poll @homer   → agent=homer  │
│  token_3 → poll @edith   → agent=edith  │
│                                         │
│  Route: bot_token → agent workspace     │
│  Sessions: sid-{agent}-{chat_id}        │
└─────────────────────────────────────────┘
```

### Gateway config.json

```json
{
  "agents": [
    {
      "name": "jarvis",
      "bot_token_env": "TG_TOKEN_JARVIS",
      "workspace": "~/.claude-lab/jarvis/.claude",
      "model": "opus",
      "role": "coordinator"
    },
    {
      "name": "homer",
      "bot_token_env": "TG_TOKEN_HOMER",
      "workspace": "~/.claude-lab/homer/.claude",
      "model": "opus",
      "role": "coder"
    },
    {
      "name": "edith",
      "bot_token_env": "TG_TOKEN_EDITH",
      "workspace": "~/.claude-lab/edith/.claude",
      "model": "sonnet",
      "role": "inbox"
    }
  ],
  "shared": {
    "secrets": "~/.claude-lab/shared/secrets/",
    "skills": "~/.claude-lab/shared/skills/",
    "gateway": "~/.claude-lab/shared/gateway/"
  }
}
```

> **Add 4th agent:** append another object to the `agents` array. Gateway auto-discovers.

## Directory Layout

> **Example names** -- replace `jarvis/`, `homer/`, `edith/` with your agent names.

```
~/.claude/                              # GLOBAL (all agents read this)
├── CLAUDE.md                           # Global rules, conventions
└── rules/
    ├── bash.md
    ├── python.md
    └── typescript.md

~/.claude-lab/
│
├── jarvis/                             # COORDINATOR (example name)
│   └── .claude/
│       ├── CLAUDE.md                   # SOUL: identity, character, principles
│       ├── core/
│       │   ├── AGENTS.md              # Models, routing rules, agent registry
│       │   ├── USER.md               # Operator profile
│       │   ├── rules.md              # Boundaries, permissions
│       │   ├── warm/decisions.md     # 14d rolling decisions
│       │   ├── hot/recent.md         # 72h rolling journal
│       │   └── MEMORY.md             # COLD archive
│       ├── tools/TOOLS.md            # Servers, Docker, services
│       ├── skills/                    # Agent-specific + symlinks to shared
│       └── agents/                   # Subagent definitions
│
├── homer/                              # CODER (example name)
│   └── .claude/
│       ├── CLAUDE.md                   # SOUL: coder identity
│       ├── core/                      # Same structure as above
│       ├── tools/TOOLS.md
│       └── skills/
│
├── edith/                              # INBOX / KNOWLEDGE (example name)
│   └── .claude/
│       ├── CLAUDE.md                   # SOUL: knowledge manager identity
│       ├── core/                      # Same structure as above
│       ├── tools/TOOLS.md
│       └── skills/
│
├── _template/                          # ONE-CLICK new agent
│   └── .claude/
│       ├── CLAUDE.md.template         # SOUL template with placeholders
│       ├── core/                      # Empty structure
│       └── install.sh                 # Bootstrap script
│
├── shared/                             # SHARED RESOURCES (all agents)
│   ├── secrets/                       # ONE folder for all secrets
│   │   ├── .env                       # Shared env vars
│   │   ├── groq-api-key
│   │   ├── openviking.key
│   │   └── db-service-account.json
│   ├── gateway/                       # Telegram gateway (1 process)
│   │   ├── gateway.py
│   │   ├── config.json               # Agent registry (see above)
│   │   ├── state/                    # Session files per agent
│   │   └── media-inbound/            # Downloaded media
│   ├── kanban/                        # VIBE KANBAN (shared task board)
│   │   └── .vibe-kanban/             # SQLite DB, auto-created by npx
│   └── skills/                        # Shared skills (symlinked)
│       ├── groq-voice/               # Voice transcription
│       ├── web-search/               # Web search
│       ├── task-board/               # Task management
│       └── ...
│
├── bin/                                # UTILITY SCRIPTS
│   ├── install-local.sh               # Bootstrap new agent workspace
│   ├── doctor.sh                      # Health check all agents
│   ├── daily-rollup.sh                # Aggregate daily summaries
│   └── memory-gc.sh                   # Garbage collect old memory
│
└── orchestration/                      # GLOBAL ORCHESTRATION
    ├── programs/                      # Reusable workflow templates
    │   ├── research_brief.prose
    │   ├── build_feature.prose
    │   └── incident_triage.prose
    ├── routers/
    │   └── default_router.md
    └── templates/
        ├── status_report.md
        └── incident_report.md
```

## Key Design Decisions

### 1. Vibe Kanban -- local task board for all agents

All agents share one vibe-kanban instance. Operator sees the board in browser, agents interact via MCP.

Why: visual task tracking, git worktree isolation per task, no cloud dependency, no paid services. Operator creates tasks, agents execute and update statuses in real-time.

### 2. Secrets -- ONE folder for all

All secrets live in `shared/secrets/`. No duplication per agent.

Why: fewer places to manage, rotate, and audit. Agents access via symlinks or env vars.

### 3. Shared skills vs specialized

| Type | Path | Example | Who uses |
|------|------|---------|----------|
| **Shared** | `shared/skills/` | groq-voice, web-search, task-board | All agents (symlinked) |
| **Specialized** | `{agent}/.claude/skills/` | code-review (Homer), content-sort (Edith) | Only that agent |

Shared skills are symlinked into each agent's `skills/` at install time. Specialized skills live only in the agent's workspace.

### 4. One gateway, multiple bots

One `gateway.py` process manages all bots. Per-bot threads poll Telegram independently. Routing is by `bot_token` match to `config.json` agent entry.

Benefits:
- One process to monitor/restart
- Shared media-inbound folder
- Shared transcription (Groq)
- Unified session management

## OpenViking -- Shared Semantic Memory

All agents push to and search from one OpenViking instance. Replaces file-based shared state.

```
OLD: File mirrors          →  NEW: OpenViking
shared/state/tasks.json         POST /sessions/{sid}/messages
shared/state/agents.json        (auto-extracted to semantic index)
mirrors/sync-cron.sh            curl /search/find {query}
```

### Namespacing

Each agent writes under its own user namespace but can search across all:

```bash
OV_KEY=$(cat ~/.claude-lab/shared/secrets/openviking.key)

# Agent writes to its own namespace
curl -X POST "http://127.0.0.1:1933/api/v1/sessions" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: my-team" \
  -H "X-OpenViking-User: jarvis"       # ← namespace per agent

# Any agent can search across ALL namespaces
curl -X POST "http://127.0.0.1:1933/api/v1/search/find" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: my-team" \
  -H "X-OpenViking-User: jarvis" \
  -d '{"query": "what did homer decide about the API design", "limit": 10}'
```

> Replace `my-team` with your account name. Replace `jarvis` with the searching agent's name.

## Task Management -- Vibe Kanban

All agents share one local kanban board powered by [vibe-kanban](https://github.com/BloopAI/vibe-kanban). No cloud, no external servers -- SQLite on your disk.

### How it works

```
OPERATOR (browser)           AGENTS (MCP)
      │                           │
      │  drag & drop tasks        │  list_workspaces / create_session
      │                           │  run_session_prompt / get_execution
      ▼                           ▼
┌─────────────────────────────────────────┐
│           VIBE KANBAN (localhost)       │
│                                         │
│  ┌──────┐  ┌──────────┐  ┌──────────┐  │
│  │ Todo │→ │InProgress│→ │ InReview │→ Done │
│  └──────┘  └──────────┘  └──────────┘  │
│                                         │
│  Storage: SQLite (.vibe-kanban/db)     │
│  Isolation: git worktree per task      │
└─────────────────────────────────────────┘
```

### Agent roles on the board

| Agent | What they do on kanban |
|-------|----------------------|
| **Coordinator** | Creates tasks, sets priorities, reviews InReview |
| **Coder** | Picks Todo, moves to InProgress, submits to InReview |
| **Inbox/Knowledge** | Creates research tasks from processed content |

### MCP integration

Every agent gets vibe-kanban via MCP (configured in `settings.json`):

```json
{
  "mcpServers": {
    "vibe-kanban": {
      "command": "npx",
      "args": ["-y", "vibe-kanban", "mcp"]
    }
  }
}
```

Agent receives 4 tools: `list_workspaces`, `create_session`, `run_session_prompt`, `get_execution`.

### Task lifecycle

```
Todo  -->  InProgress  -->  InReview  -->  Done
                |
                v
           Cancelled
```

Each task = separate git worktree + branch. Completed worktrees auto-cleanup after 72h.

## Inter-Agent Communication

4 channels:

| Channel | Use case | Example |
|---------|----------|---------|
| **Telegram** | Operator talks to agent directly | Send @homer_bot a code task |
| **Vibe Kanban** | Task management, status tracking | Operator creates task, agent picks it up |
| **Message bus** | Agent-to-agent delegation | Jarvis sends task to Homer |
| **OpenViking** | Shared knowledge lookup | Homer searches what Edith stored |

### Message bus (agent-to-agent)

Any DB with inbox pattern works -- Redis, SQLite, RTDB, etc.:

```bash
# Jarvis delegates to Homer
msgbus send homer \
  '{"from":"jarvis","body":"Build the API endpoint for /users","priority":"P1"}'

# Homer reads inbox
msgbus inbox homer
```

## Orchestration Programs (.prose)

Reusable workflow templates that the coordinator executes:

### build_feature.prose

```
PROGRAM: Build Feature
TRIGGER: Operator requests a new feature
AGENTS: jarvis (plan), homer (code)

STEPS:
1. Jarvis creates plan (architecture, files, tests)
2. Jarvis delegates implementation to Homer with plan
3. Homer codes, tests, commits, creates PR
4. Jarvis reviews PR
5. Jarvis confirms completion to operator
```

### research_brief.prose

```
PROGRAM: Research Brief
TRIGGER: Operator asks for research on a topic
AGENTS: jarvis (review), edith (research)

STEPS:
1. Jarvis receives request, extracts topic
2. Jarvis delegates to Edith with structured request
3. Edith researches, organizes findings
4. Edith pushes to OpenViking
5. Jarvis presents brief to operator
```

## Privacy Rules

1. **Agent workspaces are private** -- Homer cannot read Edith's hot/recent.md
2. **OpenViking is shared** -- any agent can search, writes are namespaced
3. **Message bus inbox is per-agent** -- only the recipient reads their inbox
4. **Gateway state is per-agent** -- session IDs isolated per (agent, chat)
5. **Orchestration programs are shared** -- all agents can read templates
6. **Global rules are shared** -- `~/.claude/` is read by all
7. **Secrets are shared** -- one folder, all agents access the same keys

## Adding a New Agent (One-Click)

```bash
# 1. Create Telegram bot via BotFather
# 2. Run install script
bash ~/.claude-lab/bin/install-local.sh \
  --name "friday" \
  --role "researcher" \
  --bot-token "$NEW_BOT_TOKEN"

# What it does:
# - Creates ~/.claude-lab/friday/.claude/ with all dirs
# - Copies CLAUDE.md.template, replaces {{AGENT_NAME}} and {{ROLE}}
# - Symlinks shared skills
# - Adds agent to gateway config.json
# - Restarts gateway
```

## Utility Scripts (bin/)

| Script | What it does | When |
|--------|-------------|------|
| **install-local.sh** | Bootstrap new agent workspace | Once per new agent |
| **doctor.sh** | Health check: files, secrets, services | Manual or cron weekly |
| **daily-rollup.sh** | Aggregate HOT summaries from all agents | Cron daily |
| **memory-gc.sh** | Archive old COLD files, clean temp media | Cron weekly |

## Memory Flow

```
OPERATOR MESSAGE (via any Telegram bot)
    │
    ▼
GATEWAY → route by bot_token → agent workspace
    ├── Download media, transcribe audio
    ├── Invoke: claude -p --resume {sid-agent-chat}
    │
    ▼
AGENT SESSION
    ├── Reads: SOUL + AGENTS + USER + rules + WARM + HOT + TOOLS
    ├── Works: code / research / organize / coordinate
    ├── Writes: response to Telegram
    │
    ▼
POST-RESPONSE (parallel)
    ├── Gateway: append to HOT (hot/recent.md, file lock)
    └── Gateway: push to OpenViking (background)
              │
              ▼
CRON SCRIPTS (daily)
    ├── trim-hot.sh    → compress HOT >24h entries
    ├── rotate-warm.sh → move WARM >14d to COLD
    ├── compress-warm.sh → re-compress WARM if >10KB
    └── memory-gc.sh   → archive COLD >5KB to monthly files
```
