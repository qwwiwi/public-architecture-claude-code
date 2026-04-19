# Multi-Agent Architecture

Multi-agent system with coordinator, specialized agents, shared state via OpenViking, and one Telegram gateway routing to multiple bots.

> **NOTE:** Agent names (Jarvis, Homer, Edith) are **examples**. When copying this architecture, replace them with your own names. The `install.sh` script handles renaming automatically.

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

> **Scaling:** Add a 4th agent = add a block in `config.json` + create bot in BotFather + run `install.sh`. One-click.

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
│       │   ├── hot/recent.md         # 24h rolling journal
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
│   └── skills/                        # Shared skills (symlinked)
│       ├── groq-voice/               # Voice transcription
│       ├── superpowers/              # TDD, debugging, planning, review
│       └── ...                       # (10 base skills total)
```

## Gateway Features

The gateway handles much more than simple message routing. Full feature list:

### Core Features

| Feature | Description |
|---------|-------------|
| **Multi-bot polling** | One process polls all bot tokens in parallel threads |
| **Session management** | `--resume` for context continuity, `--resume` for context continuity, `/reset` for fresh start |
| **Voice transcription** | Auto-transcribe `.ogg` via Groq Whisper before passing to agent |
| **Source classification** | Tags every message: `own_text`, `own_voice`, `forwarded`, `external_media` |
| **HOT memory write** | Appends every interaction to `core/hot/recent.md` (file-locked) |
| **OpenViking push** | Background push to semantic memory with anti-pollution guards |
| **Emergency trim** | Auto-trims HOT when >20KB (keeps last 600 lines) |
| **Media download** | Photos, documents, stickers -- downloaded to `media-inbound/` |

### Advanced Features

| Feature | Description | Config |
|---------|-------------|--------|
| **Forward context** | Agent sees `[Forwarded from: Name]` prefix on forwarded messages | Automatic |
| **Ack reactions** | Eyes emoji reaction on every incoming message (instant feedback) | Automatic |
| **Inline buttons** | Send messages with clickable buttons, handle callbacks | `send_message_with_buttons()`, `register_callback_handler()` |
| **Sticker cache** | File-based cache (`state/sticker-cache.json`) for sticker descriptions | Automatic |
| **Webhook API** | HTTP endpoint for external integrations to inject messages | `webhook_port`, `webhook_token` in config |
| **Per-topic routing** | Route Telegram forum topics to specific agents | `topic_routing` per agent |
| **Streaming modes** | `partial` (edit-in-place) or `off` (single response) | `streaming_mode` per agent |
| **Smart text chunking** | Split long responses by `\n` before hard split at 4000 chars | Automatic |
| **Reply safety** | `allow_sending_without_reply` prevents errors on deleted messages | Automatic |
| **Callback queries** | Prefix-based handler dispatch for inline button clicks | `dispatch_callback_query()` |

### Forward Context

When operator forwards a message, the agent sees who it was from:

```
# What the agent receives:
[Forwarded from: John Doe]
Original message text here

# What OpenViking stores (with anti-pollution guard):
[source:forwarded | forwarded from: john doe]
[extraction hint: this content was FORWARDED... Do NOT extract as user's own preferences]
Original message text here
```

### Webhook API

External services can inject messages into agent queues:

```bash
curl -X POST http://localhost:8095/hooks/jarvis \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Alert: CPU usage above 90%"}'
```

Configure in `config.json`:
```json
{
  "webhook_port": 8095,
  "webhook_token": "YOUR_SECRET_TOKEN"
}
```

### Per-Topic Routing

Route Telegram forum (group with topics) threads to specific agents:

```json
{
  "name": "jarvis",
  "topic_routing": {
    "-1001234567890": {
      "42": "jarvis",
      "43": "homer"
    }
  }
}
```

Messages in topic 42 go to Jarvis, topic 43 to Homer. Messages outside configured topics are ignored.

### Streaming Modes

| Mode | Behavior | Use case |
|------|----------|----------|
| `partial` (default) | Edit message in real-time as agent responds | Interactive agents |
| `off` | Single message after full response | Inbox agents, batch processing |

```json
{
  "name": "edith",
  "streaming_mode": "off"
}
```

### Extended config.json

```json
{
  "webhook_port": 8095,
  "webhook_token": "YOUR_SECRET_TOKEN",
  "agents": [
    {
      "name": "jarvis",
      "bot_token_env": "TG_TOKEN_JARVIS",
      "workspace": "~/.claude-lab/jarvis/.claude",
      "model": "opus",
      "role": "coordinator",
      "streaming_mode": "partial",
      "agent_names": ["jarvis", "homer", "edith"],
      "topic_routing": {}
    },
    {
      "name": "edith",
      "bot_token_env": "TG_TOKEN_EDITH",
      "workspace": "~/.claude-lab/edith/.claude",
      "model": "sonnet",
      "role": "inbox",
      "streaming_mode": "off"
    }
  ]
}
```

## Key Design Decisions

### 1. Secrets -- ONE folder for all

All secrets live in `shared/secrets/`. No duplication per agent.

Why: fewer places to manage, rotate, and audit. Agents access via symlinks or env vars.

### 2. Shared skills vs specialized

| Type | Path | Example | Who uses |
|------|------|---------|----------|
| **Shared** | `shared/skills/` | groq-voice, superpowers, perplexity-research | All agents (symlinked) |
| **Specialized** | `{agent}/.claude/skills/` | custom agent-specific skills | Only that agent |

Shared skills are symlinked into each agent's `skills/` at install time. Specialized skills live only in the agent's workspace.

### 3. One gateway, multiple bots

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
shared/state/tasks.json         temp_upload + add_resource
shared/state/agents.json        (auto-indexed to semantic store)
mirrors/sync-cron.sh            ov-session-sync.sh (cron + Stop hook)
```

### Namespacing

Each agent writes under its own user namespace but can search across all:

```bash
OV_KEY=$(cat ~/.claude-lab/shared/secrets/openviking.key)

# Agent syncs sessions to its own namespace (via ov-session-sync.sh or manual)
# Step 1: upload markdown
curl -X POST "http://localhost:1933/api/v1/resources/temp_upload" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: my-team" \
  -H "X-OpenViking-User: jarvis" \
  -F "file=@session-summary.md"
# Step 2: add resource (returns after indexing)
curl -X POST "http://localhost:1933/api/v1/resources" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: my-team" \
  -H "X-OpenViking-User: jarvis" \
  -H "Content-Type: application/json" \
  -d '{"temp_file_id":"<from step 1>","to":"viking://resources/jarvis-sessions/2026-04-10","wait":true}'

# Any agent can search across ALL namespaces
curl -X POST "http://localhost:1933/api/v1/search/find" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: my-team" \
  -H "X-OpenViking-User: jarvis" \
  -d '{"query": "what did homer decide about the API design", "limit": 10}'
```

> Replace `my-team` with your account name. Replace `jarvis` with the searching agent's name.

## Inter-Agent Communication

3 channels:

| Channel | Use case | Example |
|---------|----------|---------|
| **Telegram** | Operator talks to agent directly | Send @homer_bot a code task |
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
# 1. Create Telegram bot via BotFather (optional)
# 2. Run install script (from cloned repo)
cd public-architecture-claude-code
bash install.sh

# What it does:
# - Asks agent name, role, model, your name
# - Creates ~/.claude-lab/{agent}/.claude/ with all dirs
# - Fills templates, replaces {{AGENT_NAME}} etc.
# - Installs 10 base skills (symlinked)
# - Sets up cron scripts for memory management
```

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
