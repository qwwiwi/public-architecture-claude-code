# Learnings Feedback Loop -- Self-Improvement System

Agents learn from mistakes by recording structured lessons, tracking recurrence, and strengthening rules.

Inspired by [autoresearch](https://github.com/karpathy/autoresearch) (Karpathy) -- greedy hill climbing with effectiveness metric.

## How It Works

```
Correction / error / new tool
    │
    ▼
Classify: tool / behavior / workflow / architecture
    │
    ▼
Record in {agent}/LEARNINGS.md (structured table)
    │
    ▼
git commit -m "[agent] Learning #N: description"
    │
    ├── Repeats = 0 after 7 days → rule works (merge to main)
    └── Repeats > 0 → strengthen rule, update YELLOW zone
```

## Format

Each agent maintains a LEARNINGS.md with this table:

```markdown
| # | Date | Type | Context | Error | Rule | Repeats | Applied to | Commit |
|---|------|------|---------|-------|------|---------|------------|--------|
| 1 | 2026-04-06 | workflow | Deploy | Broke prod | Backup first | 0 | rules.md | abc123 |
```

### Columns

| Column | Description |
|--------|-------------|
| **#** | Sequential number |
| **Date** | Event date (YYYY-MM-DD) |
| **Type** | `tool` / `behavior` / `workflow` / `architecture` / `communication` |
| **Context** | What was happening (1-2 sentences) |
| **Error** | What went wrong |
| **Rule** | Preventive rule (one sentence) |
| **Repeats** | Recurrence counter. 0 = working. >0 = strengthen |
| **Applied to** | File where rule is enforced |
| **Commit** | Git commit hash with the change |

### Types and Actions

| Type | When | Action |
|------|------|--------|
| tool | New/broken tool | Update TOOLS.md |
| behavior | Behavioral correction | Create feedback_*.md in auto-memory |
| workflow | Process/ordering fix | Update AGENTS.md |
| architecture | Design decision | Record in warm/decisions.md |
| communication | Interaction pattern | Update rules.md (via operator) |

## Triggers

| Trigger | Example | How to detect |
|---------|---------|---------------|
| **Operator corrects** | "No, not like that" | Operator rejects your result |
| **Error pattern** | Same mistake 2+ times | Repeats counter > 0 |
| **New tool** | Installed agent-browser | New capability available |
| **Architecture decision** | "Only via task-board" | Operator sets boundary |
| **Self-diagnosis** | Crash, timeout, wrong output | Agent detects own failure |

## Access Zones

Not all files can be self-modified. Zones prevent agents from accidentally breaking their own identity.

| Zone | Files | Who changes |
|------|-------|------------|
| **RED (read-only)** | CLAUDE.md, rules.md | Operator only |
| **YELLOW (self-edit)** | USER.md, AGENTS.md, TOOLS.md, warm/decisions.md, hot/recent.md | Agent on trigger |
| **GREEN (full autonomy)** | LEARNINGS.md, MEMORY.md, skills/*, agents/*.md, feedback_*.md | Agent freely |

**Key principle:** Agent never modifies its own SOUL (CLAUDE.md). Operator iterates high-level instructions, agent optimizes within those constraints -- like Karpathy's `prepare.py` (read-only) vs `train.py` (agent-modifiable).

## Git-as-Database

Learnings are stored in a shared git repository. Each agent has its own branch.

### Repository structure

```
learnings/              # shared repo (private)
├── README.md           # format, rules, examples
├── thrall/
│   └── LEARNINGS.md    # agent 1 learnings
├── arthas/
│   └── LEARNINGS.md    # agent 2 learnings
├── silvana/
│   └── LEARNINGS.md    # agent 3 learnings
└── templates/
    └── LEARNINGS.template.md
```

### Branch strategy

```
main                    # verified rules (Repeats = 0 for 7+ days)
├── thrall/learnings    # working branch
├── arthas/learnings    # working branch
└── silvana/learnings   # working branch
```

### Commit format

```
[thrall] Learning #4: don't copy keys between servers
[arthas] Learning #1: save raw data without asking
```

### Workflow

```bash
cd /path/to/learnings
git checkout {agent}/learnings
git pull origin {agent}/learnings

# Add new entry to {agent}/LEARNINGS.md
git commit -m "[{agent}] Learning #N: description"
git push origin {agent}/learnings
```

## Effectiveness Metric

The **Repeats** column is the core metric (inspired by Karpathy's `val_bpb`):

| Repeats | Meaning | Action |
|---------|---------|--------|
| 0 | Rule works | Keep. After 7 days, merge to main |
| 1 | Rule didn't prevent recurrence | Strengthen: rewrite rule, add to AGENTS.md |
| 2+ | Critical pattern | Escalate to operator |

## Integration with CLAUDE.md

Add this to the agent's Workflow Orchestration section:

```markdown
**Self-Improvement Loop**
- After ANY correction from operator: record in core/LEARNINGS.md
- Classify: tool / behavior / workflow / architecture
- If behavioral -- create feedback_*.md in auto-memory
- If tool/service -- update TOOLS.md (yellow zone)
- If pattern (2+ repeats) -- strengthen rule in AGENTS.md
- At session start -- review core/LEARNINGS.md (last 10 entries)
- Metric: Repeats column. >0 = rule not working, strengthen
- RED zone (CLAUDE.md, rules.md) -- only operator changes
- YELLOW zone (USER.md, AGENTS.md, TOOLS.md, warm/, hot/) -- agent on trigger
```

## Integration with AGENTS.md

Add this section to the agent's AGENTS.md:

```markdown
## Self-Learning

Local-only learning system. No external databases.

### Access Zones

| Zone | Files | Who changes |
|------|-------|------------|
| **RED (read-only)** | CLAUDE.md, rules.md | Operator only |
| **YELLOW (self-edit)** | USER.md, AGENTS.md, TOOLS.md, warm/, hot/ | Agent on trigger |
| **GREEN (autonomy)** | LEARNINGS.md, MEMORY.md, skills/*, feedback_*.md | Agent freely |

### Flow

1. Event -> classify type (tool / behavior / workflow / architecture)
2. Record in core/LEARNINGS.md (structured log)
3. Record in auto-memory feedback_*.md if behavioral
4. If stable pattern -> update YELLOW zone

### Metric

Repeats column in LEARNINGS.md -- recurrence counter. >0 = rule not working, strengthen.
```

## How to Ensure Agents Don't Forget

| Mechanism | How it works |
|-----------|-------------|
| **CLAUDE.md trigger** | "After ANY correction -- record learning" in Workflow Orchestration |
| **Boot sequence** | Session start: read last 10 LEARNINGS.md entries |
| **Gateway hook** | Gateway detects correction pattern ("no", "wrong", "stop") and adds `[LEARNING TRIGGER]` reminder |
| **Weekly audit** | Cron: if agent worked but 0 learnings this week -> alert operator |
| **Post-task check** | After task completion: were there corrections? If yes -- learning recorded? |

## Learnings v2 (Engine-based)

Advanced learnings system using `learnings-engine.mjs` for automated capture, scoring, promotion, and maintenance.

### Commands

| Command | What it does |
|---------|-------------|
| `capture` | Record a new learning from correction or self-diagnosis |
| `score` | Calculate relevance score for a learning (recency, frequency, severity) |
| `promote` | Move high-scoring learning up the reliability pyramid |
| `lint` | Audit all learnings -- find stale, duplicate, or ineffective rules |
| `archive` | Move old/resolved learnings to archive |
| `bump` | Increment repeat counter for a recurring mistake |
| `report` | Generate summary of learnings stats (counts, scores, promotion candidates) |
| `sync` | Push learnings to git repo (branch per agent) |

### Storage: episodes.jsonl

Each learning is stored as a JSON line in `episodes.jsonl`:

```json
{"ts":"2026-04-14T12:00:00Z","type":"workflow","context":"Deploy without backup","error":"Lost .next","rule":"Always backup before deploy","score":0.92,"freq":2,"agent":"sa-claude"}
```

### Scoring and Promotion

- **Score > 0.8** or **frequency 3+** triggers automatic promotion
- Scoring factors: recency (newer = higher), frequency (more repeats = higher), severity (prod impact = higher)

### Promotion Pyramid (weak to strong)

| Level | Target | Durability | Who changes |
|-------|--------|-----------|-------------|
| 1 | Session memory | Lost on compact/reset | Agent |
| 2 | episodes.jsonl | Scored top-5 injected at startup, fades after 30 days | Agent |
| 3 | TOOLS.md / SKILL.md | Found by local-recall grep on request | Agent (GREEN zone) |
| 4 | CLAUDE.md / rules.md | Always in context | Operator only (RED zone) |
| 5 | Scripts / Hooks | Runs automatically, no agent involvement needed | Operator or agent (with approval) |

The more critical the mistake, the higher up the pyramid it should be promoted. Critical production issues go straight to hooks/scripts.

### Integration with Hooks

- **correction-detector.sh** (UserPromptSubmit hook): detects operator corrections ("no", "wrong", "not like that") and triggers `capture` automatically
- **review-reminder.sh** (PostToolUse hook): reminds agent to self-review after N tool calls without a review
- **SessionStart hook**: injects scored top-5 learnings from episodes.jsonl into context

### Auto-sync to Git

Learnings are synced to a shared git repository with one branch per agent:

```bash
echo '{"context":"...","error":"...","rule":"..."}' | node scripts/learnings-engine.mjs capture
node scripts/learnings-engine.mjs sync   # pushes to {agent}/learnings branch
```

## LEARNINGS.md Template

```markdown
# LEARNINGS -- {Agent Name}

_Structured log of lessons learned. Append new entries at the bottom._
_Review at session start. Metric: Repeats column. >0 = rule not working._

## Triggers

| Trigger | Action |
|---------|--------|
| Operator corrects | Record learning |
| Error pattern (2+ times) | Strengthen rule |
| New tool/skill | Update TOOLS.md |
| Self-diagnosis (crash/timeout) | Record with root cause |

## Log

| # | Date | Type | Context | Error | Rule | Repeats | Applied to | Commit |
|---|------|------|---------|-------|------|---------|------------|--------|
```
