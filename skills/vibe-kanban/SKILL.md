---
name: vibe-kanban
description: "Local kanban board for AI agents. Agents create/update/complete tasks, track status visually. Use when: manage tasks, kanban, create task, update status, task board."
user-invocable: true
argument-hint: "[action] [task-description]"
---

# Vibe Kanban -- Task Board for Agents

Local kanban board with browser UI. Agents create tasks, change statuses, manage workspaces.
Each task gets its own git worktree and branch.

## Setup

```bash
npx vibe-kanban
```

Opens in browser. No database, no cloud -- runs locally with SQLite.

## How Agents Use It

### Through MCP (recommended)

Vibe Kanban has a built-in MCP server. Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "vibe-kanban": {
      "command": "npx",
      "args": ["-y", "vibe-kanban", "mcp"]
    }
  }
}
```

Agent gets these tools:
- `list_workspaces` -- see all tasks and their statuses
- `create_session` -- start working on a task
- `run_session_prompt` -- execute work in a task's workspace
- `get_execution` -- check execution status

### Through CLI

```bash
# Start the board
npx vibe-kanban

# Open in browser
# http://localhost:<port> (auto-assigned)
```

## Task Lifecycle

```
Todo  -->  InProgress  -->  InReview  -->  Done
                |
                v
           Cancelled
```

| Status | Meaning |
|--------|---------|
| **Todo** | Task created, waiting to start |
| **InProgress** | Agent is working on it |
| **InReview** | Work done, needs review |
| **Done** | Completed and merged |
| **Cancelled** | Abandoned |

## Multi-Agent Workflow

Multiple agents can share the same kanban board:

1. **One board per project** -- all agents see the same tasks
2. **Each task = git worktree** -- agents work in isolation
3. **Status updates in real-time** -- visible in browser UI
4. **Code review built-in** -- inline comments on diffs

### Example: 3-agent team

| Agent | Role | How they use kanban |
|-------|------|-------------------|
| **Coordinator** | Assigns tasks | Creates tasks, sets priorities |
| **Coder** | Implements | Picks tasks, moves to InProgress, submits to InReview |
| **Reviewer** | Reviews code | Reviews InReview tasks, approves or requests changes |

## Features

| Feature | Description |
|---------|-------------|
| Git worktrees | Each task gets isolated worktree + branch |
| Browser UI | Drag-and-drop kanban board |
| Code review | Inline diff comments |
| PR creation | Create GitHub PR from completed task |
| Auto-cleanup | Worktrees deleted 72h after completion |
| MCP integration | AI agents manage tasks programmatically |

## Supported AI Agents

Claude Code, Codex, Gemini CLI, Amp, Cursor, OpenCode, QwenCode, Copilot, Droid.

## Reference

- Repo: https://github.com/BloopAI/vibe-kanban
- License: Apache 2.0
- Stars: 24.7K
