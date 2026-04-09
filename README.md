# Claude Code Agent Architecture

Universal architecture for Claude Code agents with local memory layers and semantic search.

## What's Inside

### Start Here (beginners)

| File | Description |
|------|-------------|
| **[SETUP-GUIDE.md](SETUP-GUIDE.md)** | **End-to-end: от нуля до работающего агента (готовые промпты)** |
| **[FIRST-AGENT.md](FIRST-AGENT.md)** | **Твой первый агент: пошагово от workspace до Telegram** |
| **[AGENT-LAWS.md](AGENT-LAWS.md)** | **Иерархия, правила и законы агентов: 9 принципов, зоны автономности, скиллы** |
| **[COMMANDS-QUICKREF.md](COMMANDS-QUICKREF.md)** | **Шпаргалка команд: /plan, /tdd, /code-review, decision tree** |
| **[TOKEN-OPTIMIZATION.md](TOKEN-OPTIMIZATION.md)** | **Оптимизация токенов: экономия 60-70% с первого дня** |

### Architecture (deep dive)

| File | Description |
|------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full architecture diagram and flows |
| [MULTI-AGENT.md](MULTI-AGENT.md) | Мульти-агентная система: 3 агента, 3 Telegram-бота, 1 gateway |
| [FILES-REFERENCE.md](FILES-REFERENCE.md) | Полная карта каждого файла: роль, кто пишет, когда грузится |
| [STRUCTURE.md](STRUCTURE.md) | Directory layout (single or multi-agent) |
| [MEMORY.md](MEMORY.md) | 4-layer memory system with token budget |
| [CHECKLIST.md](CHECKLIST.md) | Step-by-step: create a new agent from scratch |

### Reference

| File | Description |
|------|-------------|
| [MAPPING.md](MAPPING.md) | Маппинг: OpenClaw vs Claude Code vs наша архитектура |
| [SKILLS.md](SKILLS.md) | How to create and configure skills |
| [SUBAGENTS.md](SUBAGENTS.md) | Custom subagents: agents/*.md format, built-in types |
| [HOOKS.md](HOOKS.md) | Lifecycle hooks: auto-format, validation, security |
| [templates/](templates/) | Universal templates with {{placeholders}} for install.sh |
| [examples/](examples/) | Filled example files (CLAUDE.md, AGENTS.md, rules, etc.) |
| [scripts/](scripts/) | Memory management scripts (trim-hot, compress-warm, rotate) |
| [skills/](skills/) | Recommended skills (Superpowers, etc.) |

## Quick Install (one command)

```bash
git clone https://github.com/qwwiwi/public-architecture-claude-code.git
cd public-architecture-claude-code
bash install.sh
```

The script asks agent name, role, model, your name -- then creates the full workspace with all files filled in. Run again to add more agents.

## Quick Start

### Beginners (first agent)

1. Run `bash install.sh` -- creates workspace in 2 minutes
2. Read [FIRST-AGENT.md](FIRST-AGENT.md) to understand what each file does
3. Learn commands from [COMMANDS-QUICKREF.md](COMMANDS-QUICKREF.md)
4. Optimize tokens with [TOKEN-OPTIMIZATION.md](TOKEN-OPTIMIZATION.md)
5. Detailed walkthrough: [SETUP-GUIDE.md](SETUP-GUIDE.md)

### Experienced (full architecture)

1. Run `bash install.sh` or fill [templates/](templates/) manually
2. See [MAPPING.md](MAPPING.md) for design decisions (OpenClaw vs Claude Code vs ours)
3. Set up [Telegram Gateway](https://github.com/qwwiwi/jarvis-telegram-gateway) for multi-agent
4. Deploy [OpenViking](https://github.com/volcengine/OpenViking) for semantic memory
5. See [MULTI-AGENT.md](MULTI-AGENT.md) for 3-agent architecture

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
│   ├── kanban/                   vibe-kanban task board (SQLite)
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

## Task Board

```
npx vibe-kanban              # opens browser kanban UI
```

All agents share one board via MCP. Operator sees tasks in browser, agents manage via `list_workspaces` / `create_session` tools. Data: local SQLite, no cloud.

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
