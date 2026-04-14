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

### Sync session to OpenViking on Stop

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "bash scripts/ov-session-sync.sh >> /tmp/ov-session-sync.log 2>&1 &",
        "timeout": 10
      }]
    }]
  }
}
```

Uploads HOT+WARM memory to OpenViking for semantic search across sessions. The script (`ov-session-sync.sh`) uses `temp_upload` + `add_resource` to create indexed resources at `viking://resources/{agent}-sessions/{date}`. Runs in background (`&`) so it doesn't block the session exit. Combine with a daily cron (`30 6 * * *`) for redundancy. See MEMORY.md for full details.

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

## Production Hooks (multi-agent pattern)

These hooks form the production memory and safety pipeline for agents running via Telegram gateway.

### All production hooks

| Hook | Event | Description |
|------|-------|-------------|
| block-dangerous.sh | PreToolUse (Bash) | Blocks rm -rf, push --force, DROP TABLE |
| protect-files.sh | PreToolUse (Edit/Write) | Protects .env, .pem, .key, secrets/ |
| log-commands.sh | PostToolUse (Bash) | Logs every command |
| session-bootstrap.sh | SessionStart | Loads top-5 learnings, checks inbox, heartbeat |
| auto-recall.mjs | UserPromptSubmit | Semantic search in OpenViking |
| local-recall.sh | UserPromptSubmit | Local grep in LEARNINGS/TOOLS |
| correction-detector.sh | UserPromptSubmit | Catches correction phrases, triggers learning |
| bash-firewall.sh | PreToolUse (Bash) | Additional bash command filtering |
| review-reminder.sh | PostToolUse | After 10+ edits, reminds code review |
| audit-log.sh | PostToolUse | Audit trail |
| auto-capture.mjs | Stop | Captures conversation to OpenViking |
| write-handoff.sh | Stop | Generates handoff.md (last 10 entries) |
| flush-to-openviking.sh | PreCompact | Saves HOT+WARM to OV before compaction |
| compact-notify.sh | PreCompact | Notifies about compaction |
| close-heartbeat.sh | Stop | Sets agent status offline |

### SessionStart

| Hook | Purpose |
|------|---------|
| **session-bootstrap.sh** | Loads top-scored learnings from `episodes.jsonl`, checks inbox for pending messages, sets agent heartbeat to `online`. First thing that runs — ensures the agent starts with full context. |

### UserPromptSubmit

| Hook | Purpose |
|------|---------|
| **auto-recall.mjs** | Sends user prompt to OpenViking semantic search, returns relevant memories as injected context. Adds long-term memory without consuming CLAUDE.md space. |
| **local-recall.sh** | Grep-searches local reference files (TOOLS.md, AGENTS.md, LEARNINGS.md) for keywords extracted from user prompt. Fast fallback when OpenViking is unavailable. |
| **correction-detector.sh** | Pattern-matches correction phrases in user messages ("not like that", "wrong", "I said"). When detected, injects a reminder to capture a learning via `learnings-engine.mjs capture`. |

### PreToolUse

| Hook | Purpose |
|------|---------|
| **block-dangerous.sh** | Blocks dangerous Bash commands (`rm -rf`, `push --force`, `DROP TABLE`) with exit 2. First line of defense. |
| **protect-files.sh** | Blocks edits to `.env`, `.pem`, `.key`, `secrets/` files. Protects sensitive paths from accidental modification. |
| **bash-firewall.sh** | Additional Bash command filtering beyond block-dangerous. Configurable pattern list. Non-negotiable safety layer. |

### PostToolUse

| Hook | Purpose |
|------|---------|
| **log-commands.sh** | Logs every Bash command with timestamp. Silent — never blocks. Essential for post-incident analysis. |
| **audit-log.sh** | Appends every tool call (tool name, arguments, timestamp) to a local log file. Broader than log-commands — covers all tools. |
| **review-reminder.sh** | Tracks cumulative Edit/Write count in the session. After 10+ edits, injects a reminder to spawn a `code-reviewer` subagent before marking the task complete. |

### PreCompact

| Hook | Purpose |
|------|---------|
| **flush-to-openviking.sh** | Pushes current HOT+WARM memory to OpenViking before compaction destroys context. Ensures no knowledge is lost during long sessions. |
| **compact-notify.sh** | Alerts about upcoming compaction — logs a warning and optionally notifies the coordinator. |

### Stop

| Hook | Purpose |
|------|---------|
| **auto-capture.mjs** | Captures incremental conversation content to OpenViking for semantic indexing. Runs on every response completion — builds the agent's long-term memory automatically. |
| **write-handoff.sh** | Generates deterministic `handoff.md` from `recent.md` — extracts last 10 entries, active topics, modified files, and pending messages. Next session starts where this one left off. |
| **close-heartbeat.sh** | Updates agent status to `offline`. Coordinator uses this to know which agents are available. |

### Production settings.json

All 12 hooks wired together. Replace `{agent}` with your agent directory name (e.g., `silvana`):

```json
{
  "hooks": {
    "SessionStart": [{"matcher": "", "hooks": [
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/session-bootstrap.sh", "timeout": 10}
    ]}],
    "UserPromptSubmit": [{"matcher": "", "hooks": [
      {"type": "command", "command": "node $HOME/.openviking/claude-code-memory-plugin/scripts/auto-recall.mjs", "timeout": 5},
      {"type": "command", "command": "node $HOME/.openviking/claude-code-memory-plugin/scripts/local-recall.mjs", "timeout": 5},
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/correction-detector.sh", "timeout": 3}
    ]}],
    "PreToolUse": [{"matcher": "Bash", "hooks": [
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/bash-firewall.sh", "timeout": 5}
    ]}],
    "PostToolUse": [{"matcher": "", "hooks": [
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/audit-log.sh", "timeout": 5},
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/review-reminder.sh", "timeout": 3}
    ]}],
    "PreCompact": [{"matcher": "", "hooks": [
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/flush-to-openviking.sh", "timeout": 5},
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/compact-notify.sh", "timeout": 5}
    ]}],
    "Stop": [{"matcher": "", "hooks": [
      {"type": "command", "command": "node $HOME/.openviking/claude-code-memory-plugin/scripts/auto-capture.mjs", "timeout": 10},
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/close-heartbeat.sh", "timeout": 5},
      {"type": "command", "command": "$HOME/.claude-lab/{agent}/hooks/write-handoff.sh", "timeout": 5}
    ]}]
  }
}
```

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
