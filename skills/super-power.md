# Super Power Skill

## What

[Superpowers](https://github.com/obra/superpowers) -- agentic skills framework for Claude Code.
14 built-in skills that auto-activate by development context.

## Install

```
/plugin install superpowers@claude-plugins-official
```

## Skills Included

### Testing & Quality
- **test-driven-development** -- RED-GREEN-REFACTOR cycle
- **verification-before-completion** -- verify fix actually works
- **systematic-debugging** -- 4-phase root cause analysis

### Planning
- **brainstorming** -- refine ideas through questioning
- **writing-plans** -- detailed implementation plans
- **executing-plans** -- batch execution with checkpoints

### Collaboration
- **requesting-code-review** -- pre-review checklist
- **receiving-code-review** -- implement review feedback
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
