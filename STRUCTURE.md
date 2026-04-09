# File Structure

> **NOTE:** Agent names (`claude-code`, `jarvis`) are examples. Replace with your own.

## Directory Layout

```
~/
├── .claude/                           GLOBAL (all agents read this)
│   ├── CLAUDE.md                      global rules, conventions
│   └── rules/
│       ├── bash.md                    set -euo pipefail...
│       ├── python.md                  type hints, pathlib...
│       └── typescript.md              strict, no any...
│
└── .claude-lab/
    ├── shared/                        SHARED RESOURCES
    │   ├── secrets/                   ONE folder for all secrets
    │   │   ├── .env                   shared env vars
    │   │   ├── groq-api-key           Groq Whisper API key
    │   │   ├── openviking.key         OpenViking API key
    │   │   ├── db-service-account.json  database service account
    │   │   └── telegram/
    │   │       ├── bot-token-agent1   per-bot tokens
    │   │       └── bot-token-agent2
    │   ├── skills/                    shared skills (symlinked)
    │   │   ├── groq-voice/            voice transcription
    │   │   ├── superpowers/           TDD, debugging, planning, review
    │   │   ├── vibe-kanban/           kanban task board (MCP)
    │   │   └── ...                    (11 base skills total)
    │   └── gateway/                   Telegram gateway
    │       ├── gateway.py
    │       ├── config.json
    │       ├── state/                 session files per agent
    │       └── media-inbound/         downloaded media
    │
    ├── claude-code/                   WORKSPACE: Agent 1 (example name)
    │   └── .claude/
    │       ├── CLAUDE.md              SOUL (identity, character)
    │       │   @core/AGENTS.md
    │       │   @core/USER.md
    │       │   @core/rules.md
    │       │   @tools/TOOLS.md
    │       │   @core/warm/decisions.md
    │       │   @core/hot/recent.md
    │       │
    │       ├── core/
    │       │   ├── AGENTS.md          models, subagents config
    │       │   ├── USER.md            operator profile
    │       │   ├── rules.md           boundaries, permissions
    │       │   ├── warm/
    │       │   │   └── decisions.md   rolling 14 days
    │       │   ├── hot/
    │       │   │   └── recent.md      rolling 72 hours
    │       │   ├── MEMORY.md          COLD archive
    │       │   └── LEARNINGS.md       lessons from mistakes
    │       │
    │       ├── tools/
    │       │   └── TOOLS.md           servers, Docker, services
    │       │
    │       ├── skills/ → ../../shared/skills (symlink)
    │       ├── agents/                subagent .md definitions
    │       └── scripts/
    │           ├── trim-hot.sh        cron: compress HOT >24h
    │           ├── compress-warm.sh   cron: compress WARM >10KB
    │           ├── rotate-warm.sh     cron: move WARM >14d to COLD
    │           └── memory-rotate.sh   cron: archive COLD >5KB
    │
    └── jarvis/                        WORKSPACE: Agent 2 (example name)
        └── .claude/
            ├── CLAUDE.md              SOUL (different character)
            │   (same @include structure)
            ├── core/
            │   (same structure as agent 1)
            ├── tools/TOOLS.md
            ├── skills/ → ../../shared/skills (symlink)
            ├── agents/
            └── scripts/
```

## What's Isolated vs Shared

| Isolated (per agent) | Shared |
|---------------------|--------|
| CLAUDE.md (SOUL) | ~/.claude/CLAUDE.md (global) |
| rules.md (boundaries) | ~/.claude/rules/*.md |
| TOOLS.md (servers) | shared/skills/ |
| HOT recent.md (journal) | shared/gateway/ |
| WARM decisions.md | shared/secrets/ |
| COLD MEMORY.md | OpenViking (namespaced) |
| Subagents | |
| Scripts (per-agent cron) | |
