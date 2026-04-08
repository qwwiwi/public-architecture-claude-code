# Subagents — Delegate Tasks to Specialized Agents

Subagents are isolated Claude Code instances spawned via the Agent tool. Each runs in its own context, with its own tools and model.

## Built-in Subagent Types

| Type | Model | Tools | Best for |
|------|-------|-------|----------|
| **Explore** | Haiku (fast) | Read-only (Read, Glob, Grep) | Codebase search, finding files, quick answers |
| **Plan** | Inherits parent | Read-only | Architecture research, planning |
| **general-purpose** | Inherits parent | All tools | Complex multi-step tasks, code changes |

## When to Use Subagents

**Use subagents for:**
- Codebase exploration (keeps main context clean)
- Parallel independent tasks (up to 5 simultaneously)
- Expensive research (route to cheaper models: Haiku/Sonnet)
- Restricted operations (read-only agent can't break code)
- Long investigations that would pollute main context

**Do NOT use subagents for:**
- Simple file search — use Glob/Grep directly (faster)
- Reading 2-3 known files — use Read directly
- Tasks requiring main conversation context
- Tasks that need to spawn their own subagents (no nesting)

## Custom Subagents — agents/*.md

Create custom subagent definitions in `.claude/agents/`:

```
~/.claude/agents/          (user scope — all projects)
.claude/agents/            (project scope — shared via git)
```

### Format

```yaml
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep, Bash
model: sonnet
permissionMode: default
maxTurns: 50
memory: project
effort: high
isolation: worktree
background: false
color: blue
skills:
  - api-conventions
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
---

You are a senior code reviewer. Analyze code for:
- Logic errors and edge cases
- Security vulnerabilities
- Performance issues
- Code style violations
```

### All Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique ID (lowercase + hyphens) |
| `description` | Yes | When Claude delegates to this agent (shown in tool picker) |
| `tools` | No | Allowlist of tools (e.g., `Read, Glob, Grep`). Default: all |
| `disallowedTools` | No | Denylist of tools |
| `model` | No | `sonnet`, `opus`, `haiku`, `inherit`, or full model ID |
| `permissionMode` | No | `default`, `acceptEdits`, `auto`, `bypassPermissions`, `plan` |
| `maxTurns` | No | Max agentic turns before stopping |
| `memory` | No | `user`, `project`, `local` — enables persistent memory for this subagent |
| `effort` | No | `low`, `medium`, `high`, `max` |
| `isolation` | No | `worktree` — runs in isolated git worktree |
| `background` | No | `true` = runs in background, notifies on completion |
| `color` | No | UI color (red, blue, green, yellow...) |
| `skills` | No | Skills to preload into subagent's context |
| `hooks` | No | Lifecycle hooks scoped to this subagent |
| `initialPrompt` | No | First prompt when launched via `--agent` CLI flag |
| `mcpServers` | No | MCP servers available to this subagent |

### Model Resolution (priority)

1. `CLAUDE_CODE_SUBAGENT_MODEL` env var (overrides everything)
2. Per-invocation `model` parameter (in Agent tool call)
3. Frontmatter `model` field
4. Parent conversation model (inherits)

## Practical Examples

### Read-only auditor

```yaml
---
name: security-audit
description: Scan code for security vulnerabilities
tools: Read, Glob, Grep
model: sonnet
effort: high
---
Scan for OWASP Top 10 vulnerabilities. Report findings as:
| File | Line | Severity | Issue | Fix |
```

### Background researcher

```yaml
---
name: web-research
description: Research topics using web search
tools: Read, Grep, WebSearch, WebFetch
model: sonnet
background: true
---
Research $ARGUMENTS. Return structured findings with sources.
```

### Isolated code worker

```yaml
---
name: refactor-worker
description: Refactor code in isolated worktree
tools: Read, Edit, Write, Glob, Grep, Bash
model: sonnet
isolation: worktree
---
Refactor the specified code. Run tests after changes.
```

## Limits

- Max 5 concurrent subagents (recommended)
- Subagents cannot spawn other subagents (no nesting)
- Each subagent has its own context window (isolated)
- Results return as text to parent — not the full subagent context
- `isolation: worktree` creates a temporary git worktree (auto-cleaned if no changes)
