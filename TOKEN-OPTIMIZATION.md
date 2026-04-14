# Token Optimization Guide

How to reduce token usage by 60-70% from day one. Essential for cost control and agent performance.

## Quick Setup: settings.json

Add to `~/.claude/settings.json` (global) or `.claude/settings.json` (project-only):

```json
{
  "model": "sonnet",
  "env": {
    "MAX_THINKING_TOKENS": "10000",
    "CLAUDE_CODE_SUBAGENT_MODEL": "haiku",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "400000"
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
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | ~800000 | **400000** | fresher context | Default auto-compact triggers at ~800K tokens (80% of 1M context window). Setting to 400K compacts earlier, keeping context fresh and improving thinking depth. Recommendation from Boris Cherny (head of Claude Code at Anthropic) |

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

### Models reference

| Model | ID | Strength | Forbidden |
|---|---|---|---|
| Opus 4.6 | claude-opus-4-6 | Primary: code writing, coordination, Russian | -- |
| Codex GPT-5.4 | OpenAI | Optional: architecture review, audit, double review | -- |
| Sonnet 4.6 | claude-sonnet-4-6 | Mass tasks, data collection, bulk operations | Code review |
| Haiku 4.5 | claude-haiku-4-5 | Light tasks, classification, quick lookups | Complex code, architecture |
| Sonar | Perplexity | Web research, fact-checking | Code |

> **Opus via OpenRouter -- NEVER.** Use native Anthropic API or Anthropic Max subscription.

### Practical model strategy

| Agent role | Model | Why |
|-----------|-------|-----|
| Coordinator | Opus | Needs deep reasoning for routing, planning |
| Coder | Opus (main) + Sonnet (subagents) | Code quality matters, but search/tests can be cheaper |
| Inbox / Knowledge | Sonnet | High volume, parsing/summarization |
| Subagents (search, analysis) | Haiku or Sonnet | Cheapest for bulk work |

## Context Management

### The problem

Claude Code has a context window (1,000,000 tokens / 1M for Opus 4.6 and Sonnet 4.6). As conversation grows:
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
| core/AGENTS.md | 2-5 KB | 900-2,400 | On-demand (Read tool), NOT @include |
| core/USER.md | 1-2 KB | 400-765 | Minimal |
| core/rules.md | 2-4 KB | 900-1,935 | Only active rules |
| core/warm/decisions.md | 1-3 KB | 450-1,400 | Auto-compressed by cron |
| **core/hot/recent.md** | **8-30 KB** | **3,600-13,500** | **#1 target for optimization** |
| tools/TOOLS.md | 3-6 KB | 1,300-2,565 | On-demand (Read tool), NOT @include |
| **TOTAL** | **22-65 KB** | **9,750-29,700** | |

### How to keep it lean

1. **CLAUDE.md under 200 lines** -- Anthropic's recommendation. Move reference material to skills.
2. **Cron scripts for HOT memory** -- Without compression, HOT grows to 80KB+ per day. See MEMORY.md.
3. **Prune TOOLS.md** -- Remove servers/services you don't actively use.
4. **Don't duplicate rules** -- Global `~/.claude/rules/*.md` apply to all agents. Don't repeat in per-agent rules.

## Output Compression: Terse Mode

The single biggest hidden cost is **output tokens** -- verbose responses eat 3-5x more than necessary. Add this to CLAUDE.md or rules.md to cut output tokens by up to 75%:

```markdown
## Output style
Drop: articles (a/an/the), filler (just/really/basically/actually/simply),
pleasantries (sure/certainly/of course/happy to), hedging.
Fragments OK. Short synonyms (big not extensive, fix not "implement a solution for").
Technical terms exact. Code blocks unchanged. Errors quoted exact.

Pattern: [thing] [action] [reason]. [next step].
```

### Before vs After

| Before | After | Savings |
|--------|-------|---------|
| "Sure! I'd be happy to help you with that. The issue you're experiencing is likely caused by a problem in the authentication middleware." | "Bug in auth middleware. Token expiry check uses `<` not `<=`. Fix:" | ~75% |
| "I've successfully implemented the changes you requested. The function now correctly handles edge cases." | "Done. Edge cases handled." | ~80% |

### Why it works

- **Output tokens cost 5x more than input** (Opus: $15 input vs $75 output per 1M)
- Shorter responses = faster streaming = less rate limit consumed
- Agent still writes full code blocks and exact error messages -- only prose is compressed
- On Max subscription: same quality, 3x faster responses

### How aggressive to go

| Level | Add to rules | Effect |
|-------|-------------|--------|
| **Light** | "Be concise. No filler." | ~30% reduction |
| **Medium** | The full prompt above | ~60% reduction |
| **Heavy** | Add: "Max 2 sentences per response unless code." | ~75% reduction |

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
