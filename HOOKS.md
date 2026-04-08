# Hooks — Automate Workflows on Events

Hooks are shell commands or agents that execute automatically in response to Claude Code lifecycle events. Zero context cost — they run outside the model.

> **Key insight:** CLAUDE.md is a *suggestion* (~80% compliance). Hooks are *enforcement* (100%).

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
        "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write 2>/dev/null; exit 0"
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

---

## Universal Hooks (recommended for any agent)

These three hooks work for any project — backend, scripts, infrastructure, anything.

### 1. Block dangerous commands

Intercepts every Bash command and checks against a list of dangerous patterns. Exit 2 = blocked, Claude gets feedback and must find a safer approach.

Create `.claude/hooks/block-dangerous.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cmd=$(jq -r '.tool_input.command // ""')

dangerous_patterns=(
  "rm -rf"
  "git reset --hard"
  "git push.*--force"
  "DROP TABLE"
  "DROP DATABASE"
  "curl.*|.*sh"
  "wget.*|.*bash"
)

for pattern in "${dangerous_patterns[@]}"; do
  if echo "$cmd" | grep -qiE "$pattern"; then
    echo "BLOCKED: '$cmd' matches dangerous pattern '$pattern'. Suggest a safer alternative." >&2
    exit 2
  fi
done
exit 0
```

### 2. Protect sensitive files

Intercepts every file edit (Edit/Write) and blocks modifications to secrets, lock files, and other protected paths.

Create `.claude/hooks/protect-files.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
file=$(jq -r '.tool_input.file_path // .tool_input.path // ""')

protected=(
  ".env*"
  ".git/*"
  "package-lock.json"
  "yarn.lock"
  "*.pem"
  "*.key"
  "secrets/*"
)

for pattern in "${protected[@]}"; do
  if echo "$file" | grep -qiE "^${pattern//\*/.*}$"; then
    echo "BLOCKED: '$file' is a protected file. Explain why this edit is needed." >&2
    exit 2
  fi
done
exit 0
```

### 3. Command logging (audit trail)

Logs every Bash command with timestamp. Does not block — only records. Invaluable for debugging when something goes wrong.

Create `.claude/hooks/log-commands.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cmd=$(jq -r '.tool_input.command // ""')
printf '%s %s\n' "$(date -Is)" "$cmd" >> .claude/command-log.txt
exit 0
```

Add `.claude/command-log.txt` to `.gitignore`.

### Universal settings.json

All three universal hooks combined:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/log-commands.sh" },
          { "type": "command", "command": ".claude/hooks/block-dangerous.sh" }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/protect-files.sh" }
        ]
      }
    ]
  }
}
```

Setup:
```bash
mkdir -p .claude/hooks
# create the 3 scripts above
chmod +x .claude/hooks/*.sh
echo ".claude/command-log.txt" >> .gitignore
```

---

## Project-Specific Hooks (add as needed)

### Auto-format on save (frontend: JS/TS/CSS)

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write 2>/dev/null; exit 0"
      }]
    }]
  }
}
```

Replace `npx prettier --write` with your formatter: `black` (Python), `gofmt` (Go), `rustfmt` (Rust).

### Auto-lint after edit (frontend: ESLint/Biome)

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "npx eslint --fix $(jq -r '.tool_input.file_path') 2>&1 | tail -10; exit 0"
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
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "npm run test --silent 2>&1 | tail -5; exit 0"
      }]
    }]
  }
}
```

`tail -5` keeps output short — Claude sees "3 tests failed", not 200 lines of test output. Feedback loops like this improve output quality 2-3x (per Boris Cherny, Claude Code creator).

### Require tests before PR

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "if": "Bash(gh pr create*)",
        "command": "npm run test --silent || (echo 'Tests failing. Fix all tests before creating PR.' >&2; exit 2)"
      }]
    }]
  }
}
```

### Auto-commit on Stop

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "git add -A && git diff --cached --quiet || git commit -m 'chore(ai): apply Claude edit'"
      }]
    }]
  }
}
```

Creates atomic commits after each Claude response. Combine with `claude -w feature-branch` (worktrees) for isolated auto-committed feature branches.

### Inject context on session start

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "echo 'Branch:' $(git branch --show-current) && echo 'Last commit:' $(git log -1 --oneline)"
      }]
    }]
  }
}
```

stdout from exit-0 hooks on `SessionStart` and `UserPromptSubmit` is added to Claude's context.

---

## Complete settings.json (all hooks)

Everything combined — universal + project-specific. Remove what you don't need:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/log-commands.sh" },
          { "type": "command", "command": ".claude/hooks/block-dangerous.sh" }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/protect-files.sh" },
          { "type": "command", "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write 2>/dev/null; exit 0" },
          { "type": "command", "command": "npx eslint --fix $(jq -r '.tool_input.file_path') 2>&1 | tail -10; exit 0" }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(gh pr create*)",
            "command": "npm run test --silent || (echo 'Tests failing. Fix before PR.' >&2; exit 2)"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "npm run test --silent 2>&1 | tail -5; exit 0" }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "echo 'Branch:' $(git branch --show-current) && echo 'Last commit:' $(git log -1 --oneline)" }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "git add -A && git diff --cached --quiet || git commit -m 'chore(ai): apply Claude edit'" }
        ]
      }
    ]
  }
}
```
