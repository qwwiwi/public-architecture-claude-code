# Skills — Extend Claude with On-Demand Knowledge

Skills are markdown files that Claude loads on demand via the `/skill-name` command or automatically by path match.

## Where Skills Live

| Location | Scope |
|----------|-------|
| `.claude/skills/` (project) | Per-project, shared via git |
| `~/.claude/skills/` (user) | Personal, all projects |
| Plugin-provided | Via marketplace plugins |

## SKILL.md Format

```yaml
---
name: my-skill
description: What this skill does (max 250 chars, shown in /list)
user-invocable: true
disable-model-invocation: true
allowed-tools: Read Grep Bash(npm *)
model: sonnet
effort: high
context: fork
agent: Explore
argument-hint: "[file-or-topic]"
paths:
  - "src/api/**/*.ts"
hooks:
  PostToolUse:
    - matcher: "Edit"
      hooks:
        - type: command
          command: "npx prettier --write"
---

Instructions for Claude when this skill is activated.
Use $ARGUMENTS for passed args, $ARGUMENTS[0] for first arg.
${CLAUDE_SKILL_DIR} for skill directory path.
${CLAUDE_SESSION_ID} for session ID.
```

## Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase + hyphens, max 64 chars |
| `description` | Recommended | Max 250 chars, visible in skill list |
| `user-invocable` | No | `true` = appears in `/` menu. Default: true |
| `disable-model-invocation` | No | `true` = only manual `/name` call, Claude won't auto-trigger |
| `allowed-tools` | No | Tools that skip permission prompts. Supports glob: `Bash(npm *)` |
| `model` | No | Override model: `sonnet`, `opus`, or full model ID |
| `effort` | No | `low`, `medium`, `high`, `max` |
| `context` | No | `fork` = runs in isolated subagent (protects main context) |
| `agent` | No | Subagent type for `context: fork` (e.g., `Explore`) |
| `paths` | No | Glob patterns for auto-activation when Claude works with matching files |
| `hooks` | No | Lifecycle hooks scoped to this skill |
| `argument-hint` | No | Autocomplete hint shown after `/name` |
| `shell` | No | `bash` (default) or `powershell` |

## Dynamic Context

Execute commands before sending to Claude with `` !`command` ``:

```markdown
## Current PR context
- PR diff: !`gh pr diff`
- Changed files: !`gh pr diff --name-only`
- Test results: !`npm test 2>&1 | tail -20`
```

The command output replaces the `` !`...` `` block at invocation time.

## Context Budget

- Skill descriptions (shown in autocomplete) use ~1% of context window (~8,000 chars total)
- Full skill content loads only when invoked
- Content persists in context until session end or `/compact`
- After `/compact`, last invoked skill re-attaches automatically

## Key Patterns

### Reference skill (on-demand docs)

```yaml
---
name: api-docs
description: API conventions and endpoint patterns
disable-model-invocation: true
user-invocable: true
---
## Endpoints follow REST convention...
```

Use `disable-model-invocation: true` for heavy reference material — saves context until you need it.

### Workflow skill (automated steps)

```yaml
---
name: deploy
description: Deploy to production
allowed-tools: Bash(rsync *) Bash(ssh *)
argument-hint: "[service-name]"
---
Deploy $ARGUMENTS to production:
1. Run tests
2. Build
3. rsync to server
4. Verify health endpoint
```

### Auto-activated skill (path match)

```yaml
---
name: api-conventions
paths:
  - "src/api/**/*.ts"
---
When editing API files, follow these conventions...
```

Activates automatically when Claude reads/edits files matching the glob.

### Isolated skill (context: fork)

```yaml
---
name: deep-research
description: Research a topic without polluting main context
context: fork
agent: general-purpose
model: sonnet
---
Research $ARGUMENTS thoroughly. Return findings as bullet points.
```

Runs in a subagent — results return to main context, but the research exploration stays isolated.

## Built-in Skills

| Skill | What it does |
|-------|-------------|
| `/batch <instruction>` | Apply changes across codebase in parallel (worktrees) |
| `/claude-api` | Claude API documentation |
| `/debug [description]` | Debug logging and investigation |
| `/loop [interval] <prompt>` | Recurring prompt on interval |
| `/simplify [focus]` | Code review + fix issues |
