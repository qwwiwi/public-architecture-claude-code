# New Agent Checklist

## 1. Create Workspace

```bash
AGENT_NAME="jarvis"

mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/core/{warm,hot}
mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/tools
mkdir -p ~/.claude-lab/${AGENT_NAME}/.claude/agents
mkdir -p ~/.claude-lab/${AGENT_NAME}/secrets/telegram

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
      "telegram_bot_token_file": "~/.claude-lab/jarvis/secrets/telegram/bot-token",
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
OV_KEY=$(cat ~/.claude-lab/jarvis/secrets/openviking.key)
# OpenViking auto-creates namespace on first write
# Just ensure the key file exists
```

## 7. Setup Cron Jobs

```bash
# HOT memory trim (remove entries >72h)
0 */6 * * * /path/to/trim-hot.sh jarvis

# WARM rotation (move >14d to COLD)
0 3 * * * /path/to/rotate-warm.sh jarvis
```

## 8. Test

1. Send message to Telegram bot
2. Verify response arrives
3. Check `core/hot/recent.md` has the entry
4. Verify other agent can message via inbox
