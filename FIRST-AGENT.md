# Your First Agent

Step-by-step guide to creating your first working agent. By the end, you'll have an agent that reviews your code through Telegram.

> **Prerequisites:** Complete steps 1-6 from [SETUP-GUIDE.md](SETUP-GUIDE.md) first.

## What You're Building

A **code reviewer** agent that:
- Lives in its own workspace
- Has its own SOUL (identity, style, rules)
- Connects to Telegram (you message it, it reviews your code)
- Remembers your conversations (HOT/WARM/COLD memory)

## Step 1: Create the Workspace

```bash
AGENT_NAME="reviewer"  # ← your agent name (any name you want)

mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/core/{warm,hot}
mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/tools
mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/agents
mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/scripts

# Symlink shared skills
ln -s ~/.claude-lab/shared/skills ~/.claude-lab/${AGENT_NAME}/.claude/skills

# Create empty memory files
echo "# WARM DECISIONS" > ~/.claude-lab/${AGENT_NAME}/.claude/core/warm/decisions.md
echo "# Hot memory -- last 24h rolling journal" > ~/.claude-lab/${AGENT_NAME}/.claude/core/hot/recent.md
echo "# MEMORY -- Cold Archive" > ~/.claude-lab/${AGENT_NAME}/.claude/core/MEMORY.md
echo "# LEARNINGS" > ~/.claude-lab/${AGENT_NAME}/.claude/core/LEARNINGS.md
```

## Step 2: Write the SOUL (CLAUDE.md)

This is the most important file. It defines WHO your agent is.

Create `~/.claude-lab/reviewer/.claude/CLAUDE.md`:

```markdown
# Code Reviewer -- Senior Engineer

## SOUL

**Role:** Senior code reviewer. Finds bugs, security issues, and architectural problems.

**Character:** Thorough, direct, constructive. Points out issues AND suggests fixes.

**Style:**
- Start with a summary: "3 issues found: 1 critical, 2 minor"
- Show the problem, then the fix
- No fluff, no praise for basic things
- Code examples over explanations

**Principles:**
1. Security first -- always check for injection, auth, secrets
2. Readability matters -- code is read 10x more than written
3. Tests are not optional -- no PR without tests
4. Simple > clever -- if it needs a comment, simplify it

## Memory Layers

@core/AGENTS.md
@core/USER.md
@core/rules.md
@tools/TOOLS.md
@core/warm/decisions.md
@core/hot/recent.md
```

> **Key:** The `@core/...` lines tell Claude Code to load those files into context every session.

## Step 3: Write AGENTS.md

Create `~/.claude-lab/reviewer/.claude/core/AGENTS.md`:

```markdown
# AGENTS.md

## Models

- **Primary:** Claude Sonnet 4.6 (fast, good for review)
- **Subagents:** Native Claude Code Agent tool

## Subagents

- Maximum 3 subagents simultaneously
- Use for: searching codebase, running tests, checking docs

## OpenViking (optional)

- URL: http://localhost:1933 (use Tailscale IP for multi-VPS: check `ss -tlnp | grep 1933`)
- Key: ~/.claude-lab/shared/secrets/openviking.key
- Search: POST /api/v1/search/find
- Sync: Stop hook + cron via ov-session-sync.sh (see MEMORY.md)
```

## Step 4: Write USER.md

Create `~/.claude-lab/reviewer/.claude/core/USER.md`:

```markdown
# USER.md

**Name:** [your name]
**Role:** [developer / student / entrepreneur]
**Language:** Russian
**Timezone:** UTC+3

## What I Need

- Honest code reviews (don't sugar-coat)
- Security-focused analysis
- Performance suggestions when relevant
- Keep it concise
```

## Step 5: Write rules.md

Create `~/.claude-lab/reviewer/.claude/core/rules.md`:

```markdown
# Rules

## Boundaries

- Don't modify code without asking -- review only
- Don't commit anything
- Ask before large-scale suggestions
- Flag security issues as CRITICAL

## Review Checklist

Every review must check:
1. Security (injection, auth, secrets in code)
2. Error handling (edge cases, error messages)
3. Tests (exist? cover edge cases?)
4. Naming (clear, consistent)
5. Complexity (can it be simpler?)

## Format

- Summary first, details after
- Use severity labels: CRITICAL, WARNING, NOTE
- Include line numbers
- Show fix examples
```

## Step 6: Write TOOLS.md

Create `~/.claude-lab/reviewer/.claude/tools/TOOLS.md`:

```markdown
# TOOLS.md

## My Workspace

- **CLAUDE.md**: identity
- **Core**: AGENTS, USER, rules, warm, hot, MEMORY
- **Skills**: shared (symlinked)
- **Secrets**: ~/.claude-lab/shared/secrets/

## GitHub

- CLI: gh (authorized)
- Workflow: branches + PR, never push to main
```

## Step 7: Connect to Telegram

### Option A: Interactive (claude-code-telegram plugin)

Quick setup, works like a terminal in Telegram:

```bash
# Install plugin
pip install claude-code-telegram  # or: uv tool install claude-code-telegram

# Create bot via @BotFather in Telegram
# Set env vars:
export CLAUDE_CODE_TELEGRAM_BOT_TOKEN="your-token"
export CLAUDE_CODE_TELEGRAM_ALLOWED_USERS="your-user-id"
export CLAUDE_CODE_TELEGRAM_WORKDIR="$HOME/.claude-lab/reviewer/.claude"

# Run
claude-code-telegram
```

### Option B: Autonomous (Telegram Gateway)

Full-featured: voice messages, progress display, memory:

```bash
# Clone gateway
git clone https://github.com/qwwiwi/jarvis-telegram-gateway.git
cd jarvis-telegram-gateway

# Configure
cp config.example.json config.json
# Edit config.json: set bot token, workspace, user ID

# Run
python3 gateway.py
```

See [jarvis-telegram-gateway](https://github.com/qwwiwi/jarvis-telegram-gateway) for details.

## Step 8: Test It

1. Send your bot a message: "Review this code: [paste code]"
2. Or send a GitHub PR link: "Review this PR"
3. Check that `core/hot/recent.md` has the conversation entry

## What You Built

```
~/.claude-lab/reviewer/
└── .claude/
    ├── CLAUDE.md              ← SOUL (identity)
    ├── core/
    │   ├── AGENTS.md          ← models, subagents
    │   ├── USER.md            ← your profile
    │   ├── rules.md           ← review rules
    │   ├── warm/decisions.md  ← recent decisions (auto)
    │   ├── hot/recent.md      ← conversation log (auto)
    │   ├── MEMORY.md          ← archive (auto)
    │   └── LEARNINGS.md       ← lessons from mistakes
    ├── tools/TOOLS.md         ← available tools
    ├── skills/ → shared       ← shared skills (symlink)
    ├── agents/                ← subagent definitions
    └── scripts/               ← memory compression (cron)
```

## What's Next

1. **Add more agents** -- see [MULTI-AGENT.md](MULTI-AGENT.md) for 3-agent setup
2. **Set up memory compression** -- see [MEMORY.md](MEMORY.md) for cron scripts
3. **Create custom skills** -- see [SKILLS.md](SKILLS.md)
4. **Try different SOUL** -- change personality, add domain expertise
5. **Install Superpowers** -- `/plan`, `/tdd`, `/code-review` workflows

## Agent Ideas

| Agent | SOUL Focus | Model |
|-------|-----------|-------|
| **Code Reviewer** | Security, quality, architecture | Sonnet |
| **Coder** | Write code, tests, deploy | Opus |
| **Researcher** | Web search, summarize, organize | Sonnet |
| **Writer** | Content, posts, documentation | Sonnet |
| **DevOps** | Servers, deploy, monitoring | Opus |
| **Inbox** | Receive links, organize knowledge | Sonnet |

Each agent = its own workspace + its own SOUL + its own Telegram bot.
