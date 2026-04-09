---
name: superpowers
description: "Agentic skills framework: TDD, debugging, planning, code-review, git-worktrees, parallel agents. 14 built-in skills that auto-activate by development context."
user-invocable: false
---

# Superpowers

[Superpowers](https://github.com/obra/superpowers) -- agentic skills framework for Claude Code.
14 built-in skills that auto-activate by development context.

## Install

```bash
claude plugins marketplace add obra/superpowers-marketplace
claude plugins install superpowers@superpowers-marketplace
```

## Skills Included

### Testing & Quality
- **test-driven-development** -- RED-GREEN-REFACTOR cycle
- **verification-before-completion** -- verify fix actually works before claiming done
- **systematic-debugging** -- 4-phase root cause analysis

### Planning
- **brainstorming** -- refine ideas through questioning before implementation
- **writing-plans** -- detailed implementation plans with checkpoints
- **executing-plans** -- batch execution with review gates

### Collaboration
- **requesting-code-review** -- pre-review checklist
- **receiving-code-review** -- implement review feedback with rigor
- **dispatching-parallel-agents** -- concurrent subagent workflows
- **subagent-driven-development** -- two-stage review process

### Git
- **using-git-worktrees** -- isolated development branches
- **finishing-a-development-branch** -- merge/PR decisions

### Meta
- **writing-skills** -- create new skills
- **using-superpowers** -- intro to skills system

## Integration

Works as a plugin layer on top of CLAUDE.md memory architecture.
Does not replace existing memory/rules -- complements them with
proven development workflows that activate automatically.

## Reference

- Repo: https://github.com/obra/superpowers
- Author: Jesse Vincent
- License: MIT
