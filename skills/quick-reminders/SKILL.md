---
name: quick-reminders
description: "One-shot reminders up to 48 hours. Zero LLM tokens at fire time. Use when: remind me, set reminder, don't forget, напомни."
user-invocable: true
argument-hint: "<text> -t <time>"
---

# Quick Reminders

Zero-LLM one-shot reminders for events within 48 hours.

At creation time: agent composes the final message.
At fire time: background process delivers it without consuming any LLM tokens.

## Usage

```bash
# Add reminder
bash $CLAUDE_SKILL_DIR/scripts/nohup-reminder.sh add "Call John about the project" \
  --target CHAT_ID -t 2h

# List active reminders
bash $CLAUDE_SKILL_DIR/scripts/nohup-reminder.sh list

# Remove by ID
bash $CLAUDE_SKILL_DIR/scripts/nohup-reminder.sh remove ID

# Remove all
bash $CLAUDE_SKILL_DIR/scripts/nohup-reminder.sh remove --all
```

## Time Formats

| Format | Example | Meaning |
|--------|---------|---------|
| Relative | `30m`, `2h`, `1d`, `1h30m` | From now |
| Absolute | `2026-01-02T15:00:00+03:00` | ISO-8601 |

**Limit:** Maximum 48 hours. For longer -- use calendar.

## Delivery

The script uses `nohup sleep` + delivery command in the background.
Configure delivery in the script or use the `--channel` flag:

| Channel | Flag |
|---------|------|
| Telegram (default) | `--channel telegram` |
| Discord | `--channel discord` |
| Slack | `--channel slack` |

## Message Style

- Sound human: "Hey, you wanted to call John about the project"
- NOT robotic: "Reminder: Call John about the project"
- Compose the message at creation time in future tense
- Confirm with one short phrase: "Will remind you in 2 hours"

## Setup

Requires: `jq` (install: `apt install jq` or `brew install jq`)

Configure delivery target (Telegram chat ID, Discord webhook, etc.) in the script or pass via `--target`.

## How It Works

1. Agent composes final message text
2. Script starts `nohup sleep SECONDS && deliver` in background
3. Process is detached from terminal (`disown`)
4. At fire time: message delivered, reminder auto-removed
5. Zero LLM tokens consumed at delivery
