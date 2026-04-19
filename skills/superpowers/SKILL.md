---
name: superpowers
description: "Agentic skills framework (pcvelz fork): TDD, debugging, planning, code-review, git-worktrees, parallel agents. 15 skills with .tasks.json persistence between sessions."
user-invocable: false
---

# Superpowers (pcvelz)

[Superpowers](https://github.com/pcvelz/superpowers) -- extended fork of obra/superpowers for Claude Code.
15 built-in skills that auto-activate by development context.
Key advantage: `.tasks.json` persistence -- plans survive between sessions.

## Install

```bash
claude plugins marketplace add pcvelz/superpowers
claude plugins install superpowers@superpowers-marketplace
```

## Skills Included (15)

### Testing & Quality
- **test-driven-development** -- RED-GREEN-REFACTOR cycle
- **verification-before-completion** -- verify fix actually works before claiming done
- **systematic-debugging** -- 4-phase root cause analysis

### Planning
- **brainstorming** -- 9-step design-first flow, hard gate before code
- **writing-plans** -- plans with `.tasks.json` (goal, files, acceptanceCriteria, verifyCommand)
- **executing-plans** -- loads `.tasks.json`, continues from last completed task

### Collaboration
- **requesting-code-review** -- pre-review checklist
- **receiving-code-review** -- implement review feedback with rigor
- **dispatching-parallel-agents** -- concurrent subagent workflows
- **subagent-driven-development** -- two-stage review (spec compliance + code quality)

### Git
- **using-git-worktrees** -- isolated development branches
- **finishing-a-development-branch** -- merge/PR decisions

### Meta
- **writing-skills** -- TDD framework for creating new skills
- **using-superpowers** -- meta-skill, auto-invocation rules
- **shared** -- shared utilities for other skills

## Key Differences from obra/superpowers

- `.tasks.json` persistence -- plans survive session restarts
- Pre-commit hook -- blocks commit if tasks incomplete
- Task metadata: `verifyCommand`, `acceptanceCriteria` per task
- PlanMode explicitly banned (EnterPlanMode/ExitPlanMode)
- Multi-IDE: Claude Code + Codex + Cursor + OpenCode
- Built-in code-reviewer subagent in agents/

## Integration

Works as a plugin layer on top of CLAUDE.md memory architecture.
Does not replace existing memory/rules -- complements them with
proven development workflows that activate automatically.

## Reference

- Repo: https://github.com/pcvelz/superpowers
- Upstream: https://github.com/obra/superpowers
- License: MIT
