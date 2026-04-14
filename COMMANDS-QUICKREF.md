# Commands Quick Reference

Essential commands for daily work with Claude Code. Organized by workflow.

> **NOTE:** Some commands require the [Superpowers](https://github.com/obra/superpowers-marketplace) plugin. Install it first (see SETUP-GUIDE.md step 4).

## Core Workflow

| Command | What it does | When to use |
|---------|-------------|-------------|
| `/plan` | Create implementation plan before coding | **Always start here.** Before any feature or fix |
| `/tdd` | Test-driven development workflow | Writing new feature -- tests first, then code |
| `/code-review` | Quality + security review | After writing code, before commit |
| `/verify` | Build + lint + test in one step | Before creating PR |
| `/compact` | Compress conversation context | When agent starts forgetting or slowing down |
| `/clear` | Reset conversation (free, instant) | Between unrelated tasks |

## Decision Tree: What Command Do I Need?

```
Starting a task?
  └── /plan (always plan first)

Writing code?
  ├── New feature → /tdd (tests first)
  ├── Bug fix → /fix (if using skill)
  └── Refactor → /refactor (if using skill)

Code is written?
  ├── Review it → /code-review
  ├── Run tests → /verify
  └── Ready to merge → /commit or create PR manually

Context issues?
  ├── Agent is confused → /compact
  ├── Switching tasks → /clear
  └── Check token usage → /cost
```

## Session Management

| Command | What it does | When to use |
|---------|-------------|-------------|
| `/compact` | Summarize old messages, free context | At logical breakpoints (auto-compact handles 400K limit) |
| `/clear` | Full reset -- new conversation | Between unrelated tasks |
| `/cost` | Show token usage and cost | Monitor spending |
| `/model opus` | Switch to Opus | Complex architecture decisions |
| `/model sonnet` | Switch to Sonnet | Routine coding, bulk work |

## Git Workflow

| Command | What it does | When to use |
|---------|-------------|-------------|
| `git status` | Check what changed | Before committing |
| `git diff` | See exact changes | Review before commit |
| `/commit` | Create commit (if skill installed) | After verified chunk of work |

## Superpowers Commands

These require the Superpowers plugin:

| Command | What it does | When to use |
|---------|-------------|-------------|
| `/plan` | Structured implementation plan | Before any non-trivial work |
| `/tdd` | Test-driven development scaffold | New features |
| `/code-review` | Multi-perspective review | Before merge |
| `/brainstorm` | Explore ideas before implementation | Creative or ambiguous tasks |
| `/debug` | Systematic debugging workflow | When something breaks |

## Tips for Beginners

1. **Always /plan first** -- even for "quick" tasks. Plans catch issues before they cost time.

2. **Use /clear between tasks** -- it's free and prevents context pollution.

3. **Use /compact at logical breakpoints** -- after research (before implementation), after implementation (before testing).

4. **Start with Sonnet, switch to Opus when needed:**
   - Sonnet: routine coding, tests, simple features
   - Opus: architecture decisions, complex debugging, multi-file refactors

5. **Check /cost regularly** -- understand where tokens go.

## Command vs Skill vs Agent

| When you want to... | Use |
|---------------------|-----|
| Run a quick action | **Command** (`/plan`, `/tdd`, `/verify`) |
| Apply specialized knowledge | **Skill** (groq-voice, web-search, code-review) |
| Delegate a complex task | **Agent** (subagent via Agent tool) |

Commands are for **you** (operator). Skills are for **knowledge**. Agents are for **delegation**.
