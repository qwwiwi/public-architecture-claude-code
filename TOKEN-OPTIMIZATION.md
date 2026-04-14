# Token Optimization Guide

How to reduce token usage by 60-70% from day one. Essential for cost control and agent performance.

## Quick Setup: settings.json

Add to `~/.claude/settings.json` (global) or `.claude/settings.json` (project-only):

```json
{
  "env": {
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "400000"
  }
}
```

### What this does

| Setting | Default | Recommended | Why |
|---------|---------|-------------|-----|
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | ~800000 | **400000** | Default auto-compact triggers at ~800K tokens (80% of 1M context window). Setting to 400K compacts earlier, keeping context fresh and improving thinking depth. Recommendation from Boris Cherny (head of Claude Code at Anthropic) |

## Model Strategy

### Core principle

**Opus for code and decisions, Sonnet for subagents and bulk work.** No half-measures — code quality requires the best model. Subagents handle volume.

### Model roles

| Model | ID | Role | Use for |
|---|---|---|---|
| **Opus 4.6** | claude-opus-4-6 | **Primary** | Code writing, review, planning, coordination |
| **Sonnet 4.6** | claude-sonnet-4-6 | **Subagents** | Research, search, exploration, data collection |
| **Codex GPT-5.4** | OpenAI | **Optional** | Double review (second opinion alongside Opus) |
| **Sonar** | Perplexity | **Optional** | Web research, fact-checking |

> **Opus via OpenRouter — NEVER.** Use native Anthropic API or Anthropic Max subscription ($100-200/mo).

### Cost comparison (Anthropic Max subscription)

| Model | Input | Output | Relative cost |
|-------|-------|--------|---------------|
| **Sonnet 4.6** | $3/M | $15/M | **1x** (baseline for subagents) |
| **Opus 4.6** | $15/M | $75/M | **~5x** (worth it for code quality) |

> **On Max subscription ($100-200/mo):** All models included. Cost = rate limit consumption, not $. Sonnet subagents = faster responses + less context consumed.

### Practical model strategy

| Agent role | Model | Why |
|-----------|-------|-----|
| Coordinator | Opus | Deep reasoning for routing, planning |
| Coder | Opus | Code quality requires the best model |
| Code reviewer | Opus + Codex GPT-5.4 | Double review — two independent models |
| Subagents (search, analysis) | Sonnet | Fast, cost-effective for bulk work |
| Web research | Sonar (Perplexity) | Specialized for web search |

## Context Management

### The problem

Claude Code has a base context window of 1,000,000 tokens (1M). However, model quality degrades well before that limit. We set `CLAUDE_CODE_AUTO_COMPACT_WINDOW=400000` to auto-compact at 400K — this is the **working context**. As conversation approaches this limit:
- Agent quality **degrades** past ~50% of working context (~200K tokens)
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
| Using Sonnet for code | Code quality suffers | Opus for code, Sonnet only for subagents |
| Never compacting | Context pollution, quality drops | `/compact` at logical breakpoints |
| CLAUDE.md > 200 lines | Agent ignores instructions | Extract to skills, keep core lean |
| No cron compression | HOT memory eats 70% of context | Set up cron scripts (see MEMORY.md) |
| Running everything in one session | Context fills up | `/clear` between unrelated tasks |
| Not checking /cost | Surprise bills or slow responses | Check periodically |

## Summary: Day 1 Checklist

- [ ] Set `CLAUDE_CODE_AUTO_COMPACT_WINDOW: 400000` in settings.json
- [ ] Use Opus as primary model (code, review, planning)
- [ ] Use Sonnet for subagents (search, research, exploration)
- [ ] Keep CLAUDE.md under 200 lines
- [ ] Use `/compact` at logical breakpoints
- [ ] Use `/clear` between tasks
