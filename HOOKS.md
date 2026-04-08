# Hooks — Automate Workflows on Events

Hooks are shell commands or agents that execute automatically in response to Claude Code lifecycle events. Zero context cost — they run outside the model.

## Configuration

Hooks live in `settings.json` (global or project):

```json
// ~/.claude/settings.json (global)
// .claude/settings.json (project)
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "npx prettier --write $(jq -r '.tool_input.file_path')"
      }]
    }]
  }
}
```

## Lifecycle Events

| Event | When | Matcher |
|-------|------|---------|
| `SessionStart` | Session begins/resumes | `startup`, `resume`, `clear`, `compact` |
| `SessionEnd` | Session ends | `clear`, `resume`, `logout` |
| `UserPromptSubmit` | User sends prompt | — |
| `PreToolUse` | Before tool executes (can block) | tool name |
| `PostToolUse` | After tool executes | tool name |
| `PostToolUseFailure` | After tool error | tool name |
| `SubagentStart` | Subagent spawned | agent type |
| `SubagentStop` | Subagent finished | agent type |
| `Stop` | Claude finished responding | — |
| `PreCompact` | Before compaction | `manual`, `auto` |
| `PostCompact` | After compaction | `manual`, `auto` |
| `FileChanged` | File modified | filename |
| `CwdChanged` | Working directory changed | — |
| `TaskCreated` | Task added to todo | — |
| `TaskCompleted` | Task marked done | — |

## Handler Types

| Type | How it works |
|------|-------------|
| `command` | Shell command. Receives JSON on stdin. Exit 0 = proceed, exit 2 = block |
| `http` | POST to URL with event payload |
| `prompt` | Single-turn LLM evaluation (yes/no gating) |
| `agent` | Multi-turn subagent with tool access |

## Exit Codes (command type)

| Code | Behavior |
|------|----------|
| **0** | Proceed. stdout added to context (for SessionStart/UserPromptSubmit) |
| **2** | Block action. stderr shown to Claude as feedback |
| **other** | Proceed + error notice in context |

## `if` Filter (advanced matching)

Filter by tool name AND arguments:

```json
{
  "type": "command",
  "if": "Bash(git *)",
  "command": "./scripts/check-git-policy.sh"
}
```

Matches only `Bash` calls where the command starts with `git`.

## Practical Examples

### Auto-format on save

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
      }]
    }]
  }
}
```

### Block dangerous commands

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "if": "Bash(rm -rf *)",
        "command": "echo 'BLOCKED: rm -rf not allowed' >&2; exit 2"
      }]
    }]
  }
}
```

### Run tests after code changes

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.file_path' | grep -q '\\.py$' && python -m pytest --tb=short -q 2>&1 | tail -5 || true"
      }]
    }]
  }
}
```

### Inject context on session start

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "echo 'Current git branch:' $(git branch --show-current) && echo 'Last commit:' $(git log -1 --oneline)"
      }]
    }]
  }
}
```

stdout from exit-0 hooks on `SessionStart` and `UserPromptSubmit` is added to Claude's context.
