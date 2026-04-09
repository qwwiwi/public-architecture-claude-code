# Claude Code Agent Architecture

Universal architecture for Claude Code agents with local memory layers and semantic search.

## What's Inside

| File | Description |
|------|-------------|
| **[SETUP-GUIDE.md](SETUP-GUIDE.md)** | **End-to-end: от нуля до работающего агента (готовые промпты)** |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full architecture diagram and flows |
| **[MULTI-AGENT.md](MULTI-AGENT.md)** | **Мульти-агентная система: 3 агента, 3 Telegram-бота, 1 gateway, OpenViking** |
| **[FILES-REFERENCE.md](FILES-REFERENCE.md)** | **Полная карта каждого файла: роль, кто пишет, когда грузится, доступ** |
| [STRUCTURE.md](STRUCTURE.md) | Directory layout (single or multi-agent) |
| [MEMORY.md](MEMORY.md) | 4-layer memory system with token budget |
| [CHECKLIST.md](CHECKLIST.md) | Step-by-step: create a new agent from scratch |
| [SKILLS.md](SKILLS.md) | How to create and configure skills |
| [SUBAGENTS.md](SUBAGENTS.md) | Custom subagents: agents/*.md format, built-in types, examples |
| [HOOKS.md](HOOKS.md) | Lifecycle hooks: auto-format, validation, security |
| [examples/](examples/) | Template files (CLAUDE.md, AGENTS.md, rules, etc.) |
| [scripts/](scripts/) | Memory management scripts (trim-hot, compress-warm, rotate) |
| [skills/](skills/) | Recommended skills (Superpowers, etc.) |

## Quick Start

1. Clone this repo
2. Follow [CHECKLIST.md](CHECKLIST.md) to create your agent workspace
3. Customize identity files from [examples/](examples/)
4. (Optional) Set up Telegram gateway: [jarvis-telegram-gateway](https://github.com/qwwiwi/jarvis-telegram-gateway)
5. (Optional) Install [claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) plugin for interactive Telegram access
6. (Optional) Deploy [OpenViking](https://github.com/volcengine/OpenViking) for semantic memory

## Two Ways to Connect Telegram

> Agent names are **examples**. Replace with your own.

| Method | Use Case | Repo |
|--------|----------|------|
| **claude-code-telegram** (plugin) | Interactive coding via Telegram | [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) |
| **Telegram Gateway** (standalone) | Autonomous multi-agent: voice, progress, memory, 3+ bots | [qwwiwi/jarvis-telegram-gateway](https://github.com/qwwiwi/jarvis-telegram-gateway) |

## Architecture at a Glance

```
~/.claude/                        GLOBAL (all agents)
├── CLAUDE.md                     global rules
└── rules/*.md                    language conventions

~/.claude-lab/
├── shared/                       SHARED
│   ├── secrets/                  one folder for all secrets
│   ├── skills/                   shared skills (symlinked)
│   └── gateway/                  Telegram gateway (optional)
│
├── agent-1/.claude/              WORKSPACE: Agent 1
│   ├── CLAUDE.md                 SOUL (identity)
│   ├── core/                     memory layers
│   ├── tools/TOOLS.md            available tools
│   └── skills/ -> shared/skills
│
└── agent-2/.claude/              WORKSPACE: Agent 2
    └── (same structure)
```

## Memory Layers

```
IDENTITY ──── always in context (CLAUDE.md, rules, tools)
WARM 14d ──── always in context (decisions.md)
HOT 72h ──── always in context (recent.md, gateway writes)
COLD ──────── Read tool on demand (MEMORY.md)
L4 ────────── OpenViking search on demand
```

## Recommended Plugins

```bash
# Superpowers: TDD, debugging, planning, code review
claude plugins marketplace add obra/superpowers-marketplace
claude plugins install superpowers@superpowers-marketplace
```

## License

MIT
