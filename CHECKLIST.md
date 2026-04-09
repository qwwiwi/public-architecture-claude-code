# New Agent Checklist

> **NOTE:** `jarvis` is an example name. Replace with your own agent name.

## 1. Create Workspace

```bash
AGENT_NAME="jarvis"  # ← replace with your agent name

mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/core/{warm,hot}
mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/tools
mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/agents
mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/scripts

# Symlink shared skills
ln -s ~/.claude-lab/shared/skills ~/.claude-lab/${AGENT_NAME}/.claude/skills

# Create empty memory files
touch ~/.claude-lab/${AGENT_NAME}/.claude/core/warm/decisions.md
touch ~/.claude-lab/${AGENT_NAME}/.claude/core/hot/recent.md
touch ~/.claude-lab/${AGENT_NAME}/.claude/core/MEMORY.md
touch ~/.claude-lab/${AGENT_NAME}/.claude/core/LEARNINGS.md
```

## 2. Write Identity Files

| File | What to write |
|------|--------------|
| `.claude/CLAUDE.md` | SOUL: role, character, style, @includes |
| `core/AGENTS.md` | Models, subagents config, pipelines |
| `core/USER.md` | Operator profile, preferences |
| `core/rules.md` | Boundaries, permissions, red lines |
| `tools/TOOLS.md` | Available servers, Docker, services |

## 3. Create Telegram Bot

1. Open @BotFather in Telegram
2. `/newbot` → choose name and username
3. Copy token to `secrets/telegram/bot-token`

## 4. Configure Gateway

Edit `~/.claude-lab/shared/gateway/config.json`:

```json
{
  "agents": {
    "jarvis": {
      "enabled": true,
      "telegram_bot_token_file": "~/.claude-lab/shared/secrets/telegram/bot-token-jarvis",
      "workspace": "~/.claude-lab/jarvis/.claude",
      "model": "opus",
      "timeout_sec": 300
    }
  }
}
```

## 5. Create Systemd Service

```bash
sudo cat > /etc/systemd/system/jarvis-gateway.service << 'EOF'
[Unit]
Description=JARVIS Telegram Gateway
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/.claude-lab/jarvis
ExecStart=/usr/bin/python3 /home/YOUR_USER/.claude-lab/shared/gateway/gateway.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jarvis-gateway
sudo systemctl start jarvis-gateway
```

## 6. Setup OpenViking Namespace

```bash
OV_KEY=$(cat ~/.claude-lab/shared/secrets/openviking.key)
# OpenViking auto-creates namespace on first write
# Just ensure the key file exists
```

## 7. Setup Cron Jobs

```bash
# Order matters! rotate-warm first, then trim-hot, then compress-warm
30 4 * * * /path/to/scripts/rotate-warm.sh      # 04:30 -- move WARM >14d to COLD
0 5 * * * /path/to/scripts/trim-hot.sh           # 05:00 -- compress HOT >24h -> WARM (Sonnet)
0 6 * * * /path/to/scripts/compress-warm.sh      # 06:00 -- re-compress WARM >10KB (Sonnet)
0 21 * * * /path/to/scripts/memory-rotate.sh     # 21:00 -- archive COLD >5KB
```

## 8. Test

1. Send message to Telegram bot
2. Verify response arrives
3. Check `core/hot/recent.md` has the entry
4. Verify other agent can message via inbox
