# Multi-Agent Architecture

Full multi-agent system with orchestrator, specialized agents, shared state via OpenViking, and unified memory.

## Overview

```
OPERATOR (you)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS (orchestrator)                     │
│   Routes tasks, coordinates agents, manages shared state    │
│   Model: Opus (architecture, decisions, routing)            │
└──────────┬──────────┬──────────┬──────────┬────────────────┘
           │          │          │          │
     ┌─────▼──┐ ┌────▼───┐ ┌───▼────┐ ┌───▼────┐
     │ FRIDAY │ │ KAREN  │ │ EDITH  │ │ HOMER  │
     │research│ │content │ │ devops │ │ coder  │
     │analyst │ │comms   │ │ infra  │ │ builds │
     └────────┘ └────────┘ └────────┘ └────────┘
           │          │          │          │
           └──────────┴──────────┴──────────┘
                          │
              ┌───────────▼───────────┐
              │      OPENVIKING       │
              │  shared semantic DB   │
              │  (replaces mirrors)   │
              └───────────────────────┘
```

## Directory Layout

```
~/.claude/                              # GLOBAL (all agents)
├── CLAUDE.md                           # Global rules, conventions
└── rules/
    ├── bash.md
    ├── python.md
    └── typescript.md

~/.claude-lab/
│
├── jarvis/                             # ORCHESTRATOR
│   ├── .claude/
│   │   ├── CLAUDE.md                   # SOUL: orchestrator identity
│   │   ├── core/
│   │   │   ├── AGENTS.md              # Models, routing rules, agent registry
│   │   │   ├── USER.md               # Operator profile
│   │   │   ├── rules.md              # Boundaries, permissions
│   │   │   ├── warm/decisions.md     # 14d rolling decisions
│   │   │   ├── hot/recent.md         # 72h rolling journal
│   │   │   └── MEMORY.md             # COLD archive
│   │   ├── tools/TOOLS.md            # Servers, Docker, services
│   │   ├── orchestration/            # ★ UNIQUE TO ORCHESTRATOR
│   │   │   ├── programs/             # Workflow templates (.prose)
│   │   │   │   ├── research_brief.prose
│   │   │   │   ├── weekly_review.prose
│   │   │   │   ├── incident_triage.prose
│   │   │   │   └── build_feature.prose
│   │   │   ├── routers/              # Task routing rules
│   │   │   │   └── task_router.md    # Which agent gets which task
│   │   │   └── templates/            # Response/report templates
│   │   ├── skills/
│   │   ├── agents/                   # Subagent definitions
│   │   ├── runbooks/                 # Step-by-step operational procedures
│   │   └── policies/                 # Detailed policy files
│   │       ├── security.md
│   │       ├── models.md
│   │       └── deployments.md
│   └── secrets/
│       ├── openviking.key
│       └── telegram/bot-token
│
├── friday/                             # RESEARCH / ANALYTICS
│   ├── .claude/
│   │   ├── CLAUDE.md                   # SOUL: researcher identity
│   │   ├── core/                      # Same structure as jarvis
│   │   │   ├── AGENTS.md
│   │   │   ├── USER.md
│   │   │   ├── rules.md
│   │   │   ├── warm/decisions.md
│   │   │   ├── hot/recent.md
│   │   │   └── MEMORY.md
│   │   ├── tools/TOOLS.md
│   │   ├── projects/                  # ★ Active research projects
│   │   ├── decisions/                 # ★ Research-backed decisions
│   │   ├── experiments/               # ★ A/B tests, hypotheses
│   │   ├── skills/
│   │   ├── runbooks/
│   │   └── policies/
│   └── secrets/
│
├── karen/                              # CONTENT / COMMUNICATIONS
│   ├── .claude/
│   │   ├── CLAUDE.md                   # SOUL: content creator identity
│   │   ├── core/                      # Same structure
│   │   ├── tools/TOOLS.md
│   │   ├── style/                     # ★ Tone of voice, brand guides
│   │   ├── drafts/                    # ★ WIP content pieces
│   │   ├── skills/
│   │   ├── runbooks/
│   │   └── policies/
│   └── secrets/
│
├── edith/                              # DEVOPS / INFRASTRUCTURE
│   ├── .claude/
│   │   ├── CLAUDE.md                   # SOUL: devops engineer identity
│   │   ├── core/                      # Same structure
│   │   ├── tools/TOOLS.md
│   │   ├── incidents/                 # ★ Incident logs, postmortems
│   │   ├── experiments/               # ★ Infra experiments
│   │   ├── skills/
│   │   ├── runbooks/                  # ★ Runbooks are critical for devops
│   │   └── policies/
│   └── secrets/
│
├── homer/                              # CODER / BUILDER
│   ├── .claude/
│   │   ├── CLAUDE.md                   # SOUL: coder identity
│   │   ├── core/                      # Same structure
│   │   ├── tools/TOOLS.md
│   │   ├── projects/                  # ★ Active code projects
│   │   ├── repos/                     # ★ Repo-specific configs
│   │   ├── experiments/               # ★ Code experiments, prototypes
│   │   ├── skills/
│   │   ├── runbooks/
│   │   └── policies/
│   └── secrets/
│
├── shared/                             # SHARED RESOURCES
│   ├── gateway/                       # Telegram gateway
│   │   ├── gateway.py
│   │   ├── config.json                # All agents registered here
│   │   ├── state/                     # Session files per agent
│   │   └── media-inbound/             # Downloaded media
│   └── skills/                        # Shared skills (symlinked into each agent)
│       ├── groq-voice/
│       ├── web-search/
│       ├── task-board/
│       └── ...
│
├── orchestration/                      # GLOBAL ORCHESTRATION
│   ├── programs/                      # Reusable workflow templates
│   │   ├── research_brief.prose       # "Research X and produce brief"
│   │   ├── weekly_review.prose        # "Collect status from all agents"
│   │   ├── incident_triage.prose      # "Assess, assign, track incident"
│   │   └── build_feature.prose        # "Plan, code, test, deploy"
│   ├── routers/                       # Global routing rules
│   │   └── default_router.md         # Fallback routing
│   └── templates/                     # Report/output templates
│       ├── status_report.md
│       └── incident_report.md
│
├── bin/                                # UTILITY SCRIPTS
│   ├── install-local.sh               # Bootstrap new agent workspace
│   ├── doctor.sh                      # Health check all agents
│   ├── daily-rollup.sh                # Aggregate daily summaries
│   └── memory-gc.sh                   # Garbage collect old memory files
│
└── secrets/                            # GLOBAL SECRETS
    ├── env/                           # Environment files
    │   ├── .env.jarvis
    │   ├── .env.friday
    │   └── ...
    └── tokens/                        # API tokens
        ├── groq-api-key
        └── db-service-account.json
```

## How OpenViking Replaces Shared State

Traditional multi-agent systems use **shared files** + **mirrors** for coordination:

```
OLD: File-based shared state
shared/state/tasks/     ← JSON files, sync conflicts
shared/state/agents/    ← manual mirror-sync.sh
shared/state/claims/    ← race conditions
mirrors/                ← stale copies per agent
```

OpenViking eliminates this entirely:

```
NEW: OpenViking semantic DB
┌──────────┐     POST /sessions/{sid}/messages
│  JARVIS  │────────────────────────┐
│  FRIDAY  │────────────────────┐   │
│  KAREN   │──────────────┐     │   │
│  EDITH   │────────┐     │     │   │
│  HOMER   │──┐     │     │     │   │
└──────────┘  │     │     │     │   │
              ▼     ▼     ▼     ▼   ▼
         ┌──────────────────────────────┐
         │         OPENVIKING           │
         │  account: my-team          │
         │  users: jarvis, friday, ...  │
         │                              │
         │  ┌─── Semantic Index ───┐    │
         │  │ Facts, preferences,  │    │
         │  │ decisions, entities  │    │
         │  │ (auto-extracted)     │    │
         │  └──────────────────────┘    │
         └──────────────────────────────┘
              │     │     │     │   │
              ▼     ▼     ▼     ▼   ▼
         POST /search/find {query, limit}
         Every agent can SEARCH all shared knowledge
```

### Why OpenViking is Better

| Aspect | File Mirrors | OpenViking |
|--------|-------------|------------|
| **Sync** | Cron mirror-sync.sh, stale data | Real-time, no sync needed |
| **Conflicts** | File write races | No conflicts (append-only) |
| **Search** | grep through JSON files | Semantic search (meaning-based) |
| **Storage** | Growing file tree | Auto-managed by OV LLM |
| **Cross-agent** | Each agent copies shared/ | Each agent searches one DB |
| **Dedup** | Manual | LLM deduplicates on extract |

### OpenViking Namespacing

Each agent writes under its own user namespace but can search across all:

```bash
# Agent writes to its own namespace
OV_KEY=$(cat ~/.claude-lab/jarvis/secrets/openviking.key)
curl -X POST "http://127.0.0.1:1933/api/v1/sessions" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: my-team" \
  -H "X-OpenViking-User: jarvis"       # ← namespace

# Any agent can search across ALL namespaces
curl -X POST "http://127.0.0.1:1933/api/v1/search/find" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: my-team" \
  -H "X-OpenViking-User: jarvis" \
  -d '{"query": "what did homer decide about the API design", "limit": 10}'
```

## Agent Roles and Boundaries

### Jarvis (Orchestrator)

**What he does:**
- Receives all operator messages first
- Routes tasks to the right agent
- Coordinates multi-agent workflows
- Maintains global state awareness via OpenViking search
- Runs orchestration programs (.prose workflows)
- Produces aggregated reports

**What he doesn't do:**
- Write production code (delegates to Homer)
- Write content (delegates to Karen)
- Deep research (delegates to Friday)
- Infra changes (delegates to Edith)

**Unique files:**
- `orchestration/programs/*.prose` -- workflow templates
- `orchestration/routers/*.md` -- task routing rules

### Friday (Research / Analytics)

**What he does:**
- Deep web research (Perplexity, search)
- Data analysis, market trends
- Competitor analysis
- Fact-checking, source validation
- Produces research briefs and decision support

**Unique files:**
- `projects/` -- active research projects
- `decisions/` -- research-backed decisions with evidence
- `experiments/` -- hypotheses, A/B test designs

### Karen (Content / Communications)

**What she does:**
- Write posts, articles, scripts
- Tone of voice validation
- Content calendar management
- Social media strategy
- Brand consistency

**Unique files:**
- `style/` -- TOV guides, brand voice rules
- `drafts/` -- WIP content pieces

### Edith (DevOps / Infrastructure)

**What she does:**
- Server management, monitoring
- Incident response and triage
- CI/CD pipelines
- Security audits
- Infrastructure experiments

**Unique files:**
- `incidents/` -- incident logs, postmortems
- `experiments/` -- infra experiments (canary deploys, etc.)
- `runbooks/` -- critical (deploy, rollback, incident response)

### Homer (Coder / Builder)

**What he does:**
- Write and review code
- Build features, fix bugs
- Refactoring, testing
- API design and implementation
- Code experiments and prototypes

**Unique files:**
- `projects/` -- active code projects
- `repos/` -- per-repo configs and notes
- `experiments/` -- code prototypes, spikes

## Inter-Agent Communication

### Via Gateway (Telegram)

Each agent has its own Telegram bot. Operator talks to any agent directly.
Gateway routes based on which bot received the message.

```json
// config.json
{
  "agents": {
    "jarvis": { "enabled": true, "workspace": "~/.claude-lab/jarvis/.claude" },
    "friday": { "enabled": true, "workspace": "~/.claude-lab/friday/.claude" },
    "karen":  { "enabled": true, "workspace": "~/.claude-lab/karen/.claude" },
    "edith":  { "enabled": true, "workspace": "~/.claude-lab/edith/.claude" },
    "homer":  { "enabled": true, "workspace": "~/.claude-lab/homer/.claude" }
  }
}
```

### Via Message Bus (Agent-to-Agent)

Agents communicate through a shared message bus (any DB with inbox pattern works -- Redis, SQLite, RTDB, etc.):

```bash
# Jarvis delegates to Homer
msgbus send homer \
  '{"from":"jarvis","body":"Build the API endpoint for /users","priority":"P1"}'

# Homer reads inbox
msgbus inbox homer
```

### Via OpenViking (Shared Knowledge)

Agents don't need to message each other for knowledge -- they search OpenViking:

```bash
# Karen needs to know what Homer built
curl -X POST ".../search/find" \
  -d '{"query": "what API endpoints did homer build this week"}'

# Friday needs Edith's incident history
curl -X POST ".../search/find" \
  -d '{"query": "recent infrastructure incidents and resolutions"}'
```

## Orchestration Programs (.prose)

Reusable workflow templates that Jarvis executes:

### research_brief.prose

```
PROGRAM: Research Brief
TRIGGER: Operator asks for research on a topic
AGENTS: friday (primary), jarvis (review)

STEPS:
1. Jarvis receives request, extracts topic and constraints
2. Jarvis delegates to Friday with structured brief request
3. Friday performs deep research (web search, source analysis)
4. Friday writes findings to decisions/ and pushes to OpenViking
5. Jarvis reviews brief, asks clarifying questions if needed
6. Jarvis presents final brief to operator
```

### build_feature.prose

```
PROGRAM: Build Feature
TRIGGER: Operator requests a new feature
AGENTS: jarvis (plan), homer (code), edith (deploy), friday (research if needed)

STEPS:
1. Jarvis creates plan (architecture, files, tests)
2. If unknowns: Jarvis delegates research to Friday
3. Jarvis delegates implementation to Homer with plan
4. Homer codes, tests, commits, creates PR
5. Jarvis reviews PR (or delegates cross-review)
6. Jarvis delegates deploy to Edith
7. Edith deploys, monitors, reports back
8. Jarvis confirms completion to operator
```

### incident_triage.prose

```
PROGRAM: Incident Triage
TRIGGER: Alert, error report, or operator escalation
AGENTS: edith (primary), jarvis (coordination), homer (fix if code)

STEPS:
1. Jarvis receives alert, classifies severity (P1-P4)
2. Jarvis delegates to Edith for investigation
3. Edith checks logs, metrics, identifies root cause
4. If code fix needed: Edith delegates to Homer
5. Homer fixes, tests, creates PR
6. Edith deploys fix, monitors
7. Edith writes postmortem to incidents/
8. Jarvis reports resolution to operator
```

## Shared Files vs Agent-Private Files

| Resource | Scope | Why |
|----------|-------|-----|
| `~/.claude/CLAUDE.md` | All agents | Same coding standards |
| `~/.claude/rules/*.md` | All agents | Same language rules |
| `shared/skills/` | All agents (symlinked) | Reuse tools |
| `shared/gateway/` | All agents | One gateway process |
| `orchestration/programs/` | Jarvis reads, all can reference | Workflow templates |
| `bin/` | Operator runs | Maintenance scripts |
| `secrets/` | Per-agent isolated | Security boundary |
| `core/*` | Per-agent isolated | **Private** memory/identity |
| `hot/recent.md` | Per-agent isolated | **Private** conversation journal |
| OpenViking | Shared read, namespaced write | Cross-agent knowledge |

## Privacy Rules

1. **Agent workspaces are private** -- Homer cannot read Karen's hot/recent.md
2. **OpenViking is shared** -- any agent can search, writes are namespaced
3. **Message bus inbox is per-agent** -- only the recipient reads their inbox
4. **Secrets are per-agent** -- each agent has its own keys
5. **Gateway state is per-agent** -- session IDs isolated per (agent, chat)
6. **Orchestration programs are shared** -- all agents can read templates
7. **Global rules are shared** -- `~/.claude/` is read by all

## Utility Scripts (bin/)

| Script | What It Does | When |
|--------|-------------|------|
| **install-local.sh** | Bootstrap a new agent workspace: create dirs, copy templates, generate keys | Once per new agent |
| **doctor.sh** | Health check: verify all agents have required files, secrets exist, services running | Manual or cron weekly |
| **daily-rollup.sh** | Aggregate HOT summaries from all agents into one daily report | Cron daily |
| **memory-gc.sh** | Garbage collect: archive old COLD files, clean temp media, compact OpenViking | Cron weekly |

## Memory Flow (Full System)

```
OPERATOR MESSAGE
    │
    ▼
GATEWAY (gateway.py)
    ├── Route to correct agent bot
    ├── Download media, transcribe audio
    ├── Invoke: claude -p --resume {sid}
    │
    ▼
AGENT SESSION
    ├── Reads: SOUL + AGENTS + USER + rules + WARM + HOT + TOOLS
    ├── Works: code, research, content, etc.
    ├── Writes: response to Telegram
    │
    ▼
POST-RESPONSE (parallel)
    ├── Gateway: append to HOT (hot/recent.md, fcntl lock)
    └── Gateway: push to OpenViking (background thread)
              │
              ▼
         OPENVIKING extracts semantic facts
         (available to ALL agents via search)

CRON (daily)
    ├── 04:30 rotate-warm.sh    WARM >14d -> COLD
    ├── 05:00 trim-hot.sh       HOT >24h -> Sonnet compress -> WARM
    ├── 06:00 compress-warm.sh  WARM >10KB -> Sonnet re-compress
    └── 21:00 memory-rotate.sh  COLD >5KB -> archive/YYYY-MM.md
```

## Getting Started

1. Create workspaces for each agent using `bin/install-local.sh`
2. Write SOUL (CLAUDE.md) for each agent with unique character
3. Share skills via symlinks: `ln -s ../../shared/skills skills`
4. Register all agents in `shared/gateway/config.json`
5. Deploy OpenViking and create API keys per agent
6. Write orchestration programs in `orchestration/programs/`
7. Start gateway: `python3 shared/gateway/gateway.py`
8. Talk to any agent via their Telegram bot
