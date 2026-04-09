# TOOLS.md — Available Tools and Servers

## My Workspace

- **CLAUDE.md**: identity
- **Core**: AGENTS, USER, rules, warm, hot, MEMORY
- **Skills**: shared + local
- **Secrets**: ~/.claude-lab/shared/secrets/ (chmod 700)

## Servers

| Server | IP | Role | SSH |
|--------|----|------|-----|
| Main VPS | (your IP) | Agent runtime | local |
| Frontend | (your IP) | Web hosting | ssh user@host |

## Services

| Service | Port | Description |
|---------|------|-------------|
| openviking | 1933 | Semantic memory |
| gateway | — | Telegram gateway |

## OpenViking

- URL: http://127.0.0.1:1933
- Account: myproject
- Key: ~/.claude-lab/shared/secrets/openviking.key

## GitHub

- Account: (your username)
- CLI: gh (authorized)
- Workflow: branches + PR, never push to main
