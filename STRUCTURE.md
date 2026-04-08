# File Structure

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
    │   ├── skills/                    shared skills (symlinked)
    │   │   ├── groq-voice/            voice transcription
    │   │   ├── web-search/            web search
    │   │   ├── super-power/           super-power skill
    │   │   └── ...
    │   ├── gateway/                   Telegram gateway
    │   │   ├── gateway.py
    │   │   ├── config.json
    │   │   └── media-inbound/
    │   └── messages/                  inter-agent messages
    │       └── inbox/
    │           ├── claude-code/
    │           └── jarvis/
    │
    ├── claude-code/                   WORKSPACE: Claude Code
    │   ├── .claude/
    │   │   ├── CLAUDE.md              SOUL (identity, character)
    │   │   │   @core/AGENTS.md
    │   │   │   @core/USER.md
    │   │   │   @core/rules.md
    │   │   │   @tools/TOOLS.md
    │   │   │   @core/warm/decisions.md
    │   │   │   @core/hot/recent.md
    │   │   │
    │   │   ├── core/
    │   │   │   ├── AGENTS.md          models, subagents config
    │   │   │   ├── USER.md            operator profile
    │   │   │   ├── rules.md           boundaries, permissions
    │   │   │   ├── warm/
    │   │   │   │   └── decisions.md   rolling 14 days
    │   │   │   ├── hot/
    │   │   │   │   └── recent.md      rolling 72 hours
    │   │   │   ├── MEMORY.md          COLD archive
    │   │   │   └── LEARNINGS.md       lessons from mistakes
    │   │   │
    │   │   ├── tools/
    │   │   │   └── TOOLS.md           servers, Docker, services
    │   │   │
    │   │   ├── skills/ → ../../shared/skills (symlink)
    │   │   └── agents/                subagent .md definitions
    │   │
    │   └── secrets/
    │       └── openviking.key
    │
    └── jarvis/                        WORKSPACE: JARVIS
        ├── .claude/
        │   ├── CLAUDE.md              SOUL (different character)
        │   │   (same @include structure)
        │   ├── core/
        │   │   (same structure as claude-code)
        │   ├── tools/TOOLS.md
        │   ├── skills/ → ../../shared/skills (symlink)
        │   └── agents/
        │
        └── secrets/
            ├── telegram/bot-token
            └── openviking.key
```

## What's Isolated vs Shared

| Isolated (per agent) | Shared |
|---------------------|--------|
| CLAUDE.md (SOUL) | ~/.claude/CLAUDE.md (global) |
| rules.md (boundaries) | ~/.claude/rules/*.md |
| TOOLS.md (servers) | shared/skills/ |
| HOT recent.md (journal) | shared/gateway/ |
| WARM decisions.md | shared/messages/ |
| COLD MEMORY.md | OpenViking (namespaced) |
| Telegram bot | |
| Gateway process | |
| Subagents | |
