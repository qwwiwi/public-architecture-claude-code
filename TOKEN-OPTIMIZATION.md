# Token Optimization Guide

How to reduce token usage by 60-70% from day one. Essential for cost control and agent performance.

## Quick Setup: settings.json

Add to `~/.claude/settings.json`:

```json
{
  "model": "sonnet",
  "env": {
    "MAX_THINKING_TOKENS": "10000",
    "CLAUDE_CODE_SUBAGENT_MODEL": "haiku",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50"
  }
}
```

### What each setting does

| Setting | Default | Recommended | Savings | Why |
|---------|---------|-------------|---------|-----|
| `model` | opus | **sonnet** | ~60% cost | Sonnet handles 90% of tasks well |
| `MAX_THINKING_TOKENS` | unlimited | **10000** | ~70% hidden cost | Limits internal reasoning (hidden tokens you still pay for) |
| `CLAUDE_CODE_SUBAGENT_MODEL` | inherits parent | **haiku** | ~90% for subagents | Exploration/search doesn't need Opus |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 80 | **50** | better quality | Compact earlier = cleaner context |

## Model Selection: When to Use What

```
Task complexity?
  │
  ├── Simple (formatting, search, rename, tests)
  │   └── Sonnet or Haiku
  │
  ├── Medium (feature, bug fix, refactor, API)
  │   └── Sonnet (default)
  │
  └── Complex (architecture, multi-file refactor, debugging, planning)
      └── Opus (/model opus)
```

### Cost comparison (Anthropic Max subscription)

| Model | Input | Output | Relative cost | Use for |
|-------|-------|--------|---------------|---------|
| **Haiku 4.5** | $0.80/M | $4/M | **1x** (baseline) | Subagents, search, exploration |
| **Sonnet 4.6** | $3/M | $15/M | **~4x** | Daily coding, tests, features |
| **Opus 4.6** | $15/M | $75/M | **~19x** | Architecture, complex debugging |

> **On Max subscription ($100-200/mo):** All models included. Cost = rate limit consumption, not $. Still, lighter models = faster responses + less context eaten.

### Practical model strategy

| Agent role | Model | Why |
|-----------|-------|-----|
| Coordinator | Opus | Needs deep reasoning for routing, planning |
| Coder | Opus (main) + Sonnet (subagents) | Code quality matters, but search/tests can be cheaper |
| Inbox / Knowledge | Sonnet | High volume, parsing/summarization |
| Subagents (search, analysis) | Haiku or Sonnet | Cheapest for bulk work |

## Context Management

### The problem

Claude Code has a context window (200K for Opus). As conversation grows:
- Agent quality **degrades** past ~50% usage
- Instructions get ignored
- Responses become less focused

### The solution: active context management

| Action | Command | When | Cost |
|--------|---------|------|------|
| **Compact** | `/compact` | At logical breakpoints | Free (conversation summary) |
| **Clear** | `/clear` | Between unrelated tasks | Free (full reset) |
| **Check usage** | `/cost` | Periodically | Free |

### When to compact vs clear

```
Same project, continuing work?
  └── /compact (keeps summary, loses raw messages)

Switching to different project/topic?
  └── /clear (full reset, clean start)

Agent acting weird / ignoring instructions?
  └── /clear (context is probably polluted)
```

## Memory Budget: What Eats Your Context

Every session starts by loading these files:

| File | Typical size | Tokens (~) | Can you reduce? |
|------|-------------|------------|-----------------|
| ~/.claude/CLAUDE.md | 2-7 KB | 900-3,200 | Keep under 200 lines |
| CLAUDE.md (SOUL) | 3-8 KB | 1,300-3,500 | Keep under 200 lines |
| core/AGENTS.md | 2-5 KB | 900-2,400 | Only what agent needs |
| core/USER.md | 1-2 KB | 400-765 | Minimal |
| core/rules.md | 2-4 KB | 900-1,935 | Only active rules |
| core/warm/decisions.md | 1-3 KB | 450-1,400 | Auto-compressed by cron |
| **core/hot/recent.md** | **8-30 KB** | **3,600-13,500** | **#1 target for optimization** |
| tools/TOOLS.md | 3-6 KB | 1,300-2,565 | Only active servers |
| **TOTAL** | **22-65 KB** | **9,750-29,700** | |

### How to keep it lean

1. **CLAUDE.md under 200 lines** -- Anthropic's recommendation. Move reference material to skills.
2. **Cron scripts for HOT memory** -- Without compression, HOT grows to 80KB+ per day. See MEMORY.md.
3. **Prune TOOLS.md** -- Remove servers/services you don't actively use.
4. **Don't duplicate rules** -- Global `~/.claude/rules/*.md` apply to all agents. Don't repeat in per-agent rules.

## Beginner Mistakes to Avoid

| Mistake | Why it's bad | Fix |
|---------|-------------|-----|
| Always using Opus | 19x more expensive, slower | Default to Sonnet, switch to Opus for complex tasks |
| Never compacting | Context pollution, quality drops | `/compact` at logical breakpoints |
| CLAUDE.md > 200 lines | Agent ignores instructions | Extract to skills, keep core lean |
| No cron compression | HOT memory eats 70% of context | Set up 4 cron scripts (see MEMORY.md) |
| Running everything in one session | Context fills up | `/clear` between unrelated tasks |
| Not checking /cost | Surprise bills or slow responses | Check periodically |

## Summary: Day 1 Checklist

- [ ] Set `model: sonnet` in settings.json
- [ ] Set `MAX_THINKING_TOKENS: 10000`
- [ ] Set `CLAUDE_CODE_SUBAGENT_MODEL: haiku`
- [ ] Set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: 50`
- [ ] Keep CLAUDE.md under 200 lines
- [ ] Use `/compact` at logical breakpoints
- [ ] Use `/clear` between tasks
- [ ] Switch to `/model opus` only for complex work
