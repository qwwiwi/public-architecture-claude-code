#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# install.sh -- One-click agent workspace setup
# Creates full Claude Code agent workspace from templates
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"
SCRIPTS_DIR="${SCRIPT_DIR}/scripts"
LAB_DIR="${HOME}/.claude-lab"
GLOBAL_DIR="${HOME}/.claude"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[x]${NC} $1"; }
ask()   { echo -en "${CYAN}[?]${NC} $1: "; }

# ============================================================
# Step 1: Check prerequisites
# ============================================================

echo ""
echo "============================================"
echo "  Claude Code Agent -- Workspace Installer"
echo "============================================"
echo ""

if ! command -v claude &>/dev/null; then
    warn "Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code"
    warn "Continuing anyway (workspace will be ready when you install CLI)."
fi

if [ ! -d "$TEMPLATES_DIR" ]; then
    err "Templates directory not found: $TEMPLATES_DIR"
    err "Run this script from the cloned repository root."
    exit 1
fi

# ============================================================
# Step 2: Gather parameters
# ============================================================

echo "Answer a few questions to set up your agent."
echo ""

# Agent name
ask "Agent name (e.g. Homer, Jarvis, Friday)"
read -r AGENT_NAME
AGENT_NAME="${AGENT_NAME:-MyAgent}"
AGENT_ID=$(echo "$AGENT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

# Agent role
ask "Agent role (e.g. Coder, Coordinator, Research assistant)"
read -r AGENT_ROLE
AGENT_ROLE="${AGENT_ROLE:-Coder}"

# Agent role description (1 sentence)
ask "One-sentence role description"
read -r AGENT_ROLE_DESCRIPTION
AGENT_ROLE_DESCRIPTION="${AGENT_ROLE_DESCRIPTION:-Autonomous coding assistant. Writes code, reviews architecture, runs tests.}"

# Character traits
ask "Character traits (e.g. Pragmatic, calm, precise)"
read -r CHARACTER_TRAITS
CHARACTER_TRAITS="${CHARACTER_TRAITS:-Efficient, precise, proactive. Reports results, not process.}"

# Primary model
echo ""
echo "  Models: opus (best), sonnet (fast+cheap), haiku (fastest+cheapest)"
ask "Primary model [opus]"
read -r PRIMARY_MODEL
PRIMARY_MODEL="${PRIMARY_MODEL:-opus}"

# Research model
ask "Research model [perplexity]"
read -r RESEARCH_MODEL
RESEARCH_MODEL="${RESEARCH_MODEL:-Perplexity Sonar (web search only, no code)}"

# Max subagents
ask "Max simultaneous subagents [5]"
read -r MAX_SUBAGENTS
MAX_SUBAGENTS="${MAX_SUBAGENTS:-5}"

# Operator info
echo ""
echo "--- Operator (you) ---"
ask "Your name"
read -r OPERATOR_NAME
OPERATOR_NAME="${OPERATOR_NAME:-Operator}"

ask "How agent should address you (e.g. Boss, Chief)"
read -r OPERATOR_ADDRESS
OPERATOR_ADDRESS="${OPERATOR_ADDRESS:-Boss}"

ask "Your timezone (e.g. UTC+3, America/New_York)"
read -r TIMEZONE
TIMEZONE="${TIMEZONE:-UTC}"

ask "Response language (e.g. Russian, English)"
read -r LANGUAGE
LANGUAGE="${LANGUAGE:-English}"

ask "Commit language (e.g. Russian, English)"
read -r COMMIT_LANGUAGE
COMMIT_LANGUAGE="${COMMIT_LANGUAGE:-English}"

# Budget limit
ask "Red zone budget limit in USD [50]"
read -r BUDGET_LIMIT
BUDGET_LIMIT="${BUDGET_LIMIT:-50}"

# GitHub
ask "GitHub username (or skip)"
read -r GITHUB_USERNAME
GITHUB_USERNAME="${GITHUB_USERNAME:-your-username}"

# OpenViking account
ask "OpenViking account name (or skip)"
read -r OPENVIKING_ACCOUNT
OPENVIKING_ACCOUNT="${OPENVIKING_ACCOUNT:-myproject}"

# ============================================================
# Step 3: Confirm
# ============================================================

echo ""
echo "============================================"
echo "  Setup Summary"
echo "============================================"
echo ""
echo "  Agent:    ${AGENT_NAME} (${AGENT_ID})"
echo "  Role:     ${AGENT_ROLE}"
echo "  Model:    ${PRIMARY_MODEL}"
echo "  Operator: ${OPERATOR_NAME}"
echo "  Language: ${LANGUAGE}"
echo "  Path:     ${LAB_DIR}/${AGENT_ID}/.claude/"
echo ""
ask "Proceed? [Y/n]"
read -r CONFIRM
if [[ "${CONFIRM,,}" == "n" ]]; then
    echo "Cancelled."
    exit 0
fi

# ============================================================
# Step 4: Create directory structure
# ============================================================

WORKSPACE="${LAB_DIR}/${AGENT_ID}/.claude"
SHARED="${LAB_DIR}/shared"

log "Creating directory structure..."

mkdir -p "${WORKSPACE}/core/warm"
mkdir -p "${WORKSPACE}/core/hot"
mkdir -p "${WORKSPACE}/core/archive"
mkdir -p "${WORKSPACE}/tools"
mkdir -p "${WORKSPACE}/agents"
mkdir -p "${WORKSPACE}/scripts"
mkdir -p "${SHARED}/secrets/telegram"
mkdir -p "${SHARED}/skills"
mkdir -p "${SHARED}/gateway/state"
mkdir -p "${SHARED}/gateway/media-inbound"
mkdir -p "${SHARED}/scripts"
mkdir -p "${GLOBAL_DIR}/rules"

# ============================================================
# Step 5: Fill templates
# ============================================================

fill_template() {
    local src="$1"
    local dst="$2"

    if [ -f "$dst" ]; then
        warn "Skipping (exists): $dst"
        return
    fi

    cp "$src" "$dst"

    # Replace all placeholders
    sed -i "s|{{AGENT_NAME}}|${AGENT_NAME}|g" "$dst"
    sed -i "s|{{AGENT_ID}}|${AGENT_ID}|g" "$dst"
    sed -i "s|{{AGENT_ROLE}}|${AGENT_ROLE}|g" "$dst"
    sed -i "s|{{AGENT_ROLE_DESCRIPTION}}|${AGENT_ROLE_DESCRIPTION}|g" "$dst"
    sed -i "s|{{CHARACTER_TRAITS}}|${CHARACTER_TRAITS}|g" "$dst"
    sed -i "s|{{PRIMARY_MODEL}}|${PRIMARY_MODEL}|g" "$dst"
    sed -i "s|{{RESEARCH_MODEL}}|${RESEARCH_MODEL}|g" "$dst"
    sed -i "s|{{MAX_SUBAGENTS}}|${MAX_SUBAGENTS}|g" "$dst"
    sed -i "s|{{OPERATOR_NAME}}|${OPERATOR_NAME}|g" "$dst"
    sed -i "s|{{OPERATOR_ADDRESS}}|${OPERATOR_ADDRESS}|g" "$dst"
    sed -i "s|{{TIMEZONE}}|${TIMEZONE}|g" "$dst"
    sed -i "s|{{LANGUAGE}}|${LANGUAGE}|g" "$dst"
    sed -i "s|{{COMMIT_LANGUAGE}}|${COMMIT_LANGUAGE}|g" "$dst"
    sed -i "s|{{BUDGET_LIMIT}}|${BUDGET_LIMIT}|g" "$dst"
    sed -i "s|{{GITHUB_USERNAME}}|${GITHUB_USERNAME}|g" "$dst"
    sed -i "s|{{OPENVIKING_ACCOUNT}}|${OPENVIKING_ACCOUNT}|g" "$dst"
    sed -i "s|{{INSTALL_DATE}}|$(date -u +%Y-%m-%d)|g" "$dst"

    # Clean remaining placeholders (team, channels, etc.)
    sed -i 's|{{[A-Z_0-9]*}}|TODO: fill in|g' "$dst"

    log "Created: $dst"
}

log "Filling templates..."

# Identity files
fill_template "${TEMPLATES_DIR}/CLAUDE.md.template"    "${WORKSPACE}/CLAUDE.md"
fill_template "${TEMPLATES_DIR}/AGENTS.md.template"    "${WORKSPACE}/core/AGENTS.md"
fill_template "${TEMPLATES_DIR}/USER.md.template"      "${WORKSPACE}/core/USER.md"
fill_template "${TEMPLATES_DIR}/rules.md.template"     "${WORKSPACE}/core/rules.md"
fill_template "${TEMPLATES_DIR}/TOOLS.md.template"     "${WORKSPACE}/tools/TOOLS.md"

# Memory files
fill_template "${TEMPLATES_DIR}/decisions.md.template" "${WORKSPACE}/core/warm/decisions.md"
fill_template "${TEMPLATES_DIR}/recent.md.template"    "${WORKSPACE}/core/hot/recent.md"
fill_template "${TEMPLATES_DIR}/MEMORY.md.template"    "${WORKSPACE}/core/MEMORY.md"
fill_template "${TEMPLATES_DIR}/LEARNINGS.md.template" "${WORKSPACE}/core/LEARNINGS.md"

# Global files (only if not exist)
fill_template "${TEMPLATES_DIR}/global-CLAUDE.md.template" "${GLOBAL_DIR}/CLAUDE.md"

# Settings (only if not exist)
if [ ! -f "${WORKSPACE}/settings.json" ]; then
    cp "${TEMPLATES_DIR}/settings.json.template" "${WORKSPACE}/settings.json"
    log "Created: ${WORKSPACE}/settings.json"
fi

# ============================================================
# Step 6: Copy scripts
# ============================================================

log "Copying memory management scripts..."

for script in trim-hot.sh compress-warm.sh rotate-warm.sh memory-rotate.sh; do
    if [ -f "${SCRIPTS_DIR}/${script}" ]; then
        if [ ! -f "${WORKSPACE}/scripts/${script}" ]; then
            cp "${SCRIPTS_DIR}/${script}" "${WORKSPACE}/scripts/${script}"
            chmod +x "${WORKSPACE}/scripts/${script}"
            log "Copied: scripts/${script}"
        else
            warn "Skipping (exists): scripts/${script}"
        fi
    else
        warn "Script not found in repo: ${script} (create manually later)"
    fi
done

# ============================================================
# Step 7: Install shared skills (11 base skills)
# ============================================================

SKILLS_SRC="${SCRIPT_DIR}/skills"
SKILLS_DST="${SHARED}/skills"

log "Installing base skills..."

SKILL_LIST="groq-voice superpowers markdown-new excalidraw datawrapper perplexity-research gws youtube-transcript twitter quick-reminders vibe-kanban"

for skill in $SKILL_LIST; do
    if [ -d "${SKILLS_SRC}/${skill}" ]; then
        if [ ! -d "${SKILLS_DST}/${skill}" ]; then
            cp -r "${SKILLS_SRC}/${skill}" "${SKILLS_DST}/${skill}"
            # Make scripts executable
            find "${SKILLS_DST}/${skill}" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
            find "${SKILLS_DST}/${skill}" -name "*.py" -exec chmod +x {} \; 2>/dev/null || true
            log "Installed skill: ${skill}"
        else
            warn "Skipping (exists): skill ${skill}"
        fi
    else
        warn "Skill not found in repo: ${skill}"
    fi
done

# ============================================================
# Step 8: Create symlinks
# ============================================================

log "Creating symlinks..."

if [ ! -L "${WORKSPACE}/skills" ]; then
    ln -sf "${SHARED}/skills" "${WORKSPACE}/skills"
    log "Symlinked: skills/ -> shared/skills/"
else
    warn "Symlink exists: skills/"
fi

# ============================================================
# Step 9: Language rules
# ============================================================

log "Setting up language rules..."

for rule_file in bash.md python.md typescript.md; do
    if [ ! -f "${GLOBAL_DIR}/rules/${rule_file}" ]; then
        case "$rule_file" in
            bash.md)
                cat > "${GLOBAL_DIR}/rules/${rule_file}" << 'RULE'
# Bash rules
- set -euo pipefail at the start
- Quote variables: "$VAR"
- Check file existence before operations
- Log actions with echo
RULE
                ;;
            python.md)
                cat > "${GLOBAL_DIR}/rules/${rule_file}" << 'RULE'
# Python rules
- Type hints required for all functions
- Docstrings in Google style
- pathlib instead of os.path
- f-strings instead of .format()
- dataclasses or pydantic instead of dict
- Imports: stdlib, blank line, third-party, blank line, local
- Logging via logging module, not print
RULE
                ;;
            typescript.md)
                cat > "${GLOBAL_DIR}/rules/${rule_file}" << 'RULE'
# TypeScript rules
- strict: true always
- Never any, use unknown + type guard
- interface over type for objects
- Zod for runtime validation
- Barrel exports (index.ts) for modules
RULE
                ;;
        esac
        log "Created: ~/.claude/rules/${rule_file}"
    else
        warn "Skipping (exists): ~/.claude/rules/${rule_file}"
    fi
done

# ============================================================
# Step 10: Set permissions on secrets
# ============================================================

chmod 700 "${SHARED}/secrets" 2>/dev/null || true

# ============================================================
# Step 11: Summary
# ============================================================

echo ""
echo "============================================"
echo "  Setup Complete"
echo "============================================"
echo ""
echo "  Workspace: ${WORKSPACE}/"
echo "  Shared:    ${SHARED}/"
echo "  Global:    ${GLOBAL_DIR}/"
echo ""
echo "  Files created:"

FILE_COUNT=$(find "${WORKSPACE}" -type f | wc -l)
echo "    ${FILE_COUNT} files in workspace"
echo ""
echo "  Directory tree:"
echo ""

if command -v tree &>/dev/null; then
    tree -L 3 "${WORKSPACE}" 2>/dev/null || find "${WORKSPACE}" -maxdepth 3 -type f | sort
else
    find "${WORKSPACE}" -maxdepth 3 -type f | sed "s|${WORKSPACE}/|    |" | sort
fi

echo ""
echo "  Next steps:"
echo ""
echo "    1. Review and customize identity files:"
echo "       - ${WORKSPACE}/CLAUDE.md (SOUL)"
echo "       - ${WORKSPACE}/core/AGENTS.md (models, team)"
echo "       - ${WORKSPACE}/core/USER.md (your profile)"
echo "       - ${WORKSPACE}/tools/TOOLS.md (servers, services)"
echo ""
echo "    2. Add API keys for skills:"
echo "       echo 'your-key' > ${SHARED}/secrets/groq-api-key          # groq-voice (free)"
echo "       echo 'your-key' > ${SHARED}/secrets/transcript-api-key    # youtube (free 100)"
echo "       echo 'your-key' > ${SHARED}/secrets/socialdata-api-key    # twitter (optional)"
echo "       echo 'your-key' > ${SHARED}/secrets/datawrapper.env       # datawrapper (free)"
echo "       echo 'your-key' > ${SHARED}/secrets/perplexity.env        # perplexity (paid)"
echo "       echo 'your-key' > ${SHARED}/secrets/openviking.key        # semantic memory"
echo "       echo 'bot-token' > ${SHARED}/secrets/telegram/bot-token-${AGENT_ID}"
echo ""
echo "    3. Launch agent:"
echo "       claude --project ${WORKSPACE}"
echo ""
echo "    4. (Optional) Set up cron for memory management:"
echo "       crontab -e"
echo "       30 4 * * * bash ${WORKSPACE}/scripts/rotate-warm.sh"
echo "       0  5 * * * bash ${WORKSPACE}/scripts/trim-hot.sh"
echo "       0  6 * * * bash ${WORKSPACE}/scripts/compress-warm.sh"
echo "       0 21 * * * bash ${WORKSPACE}/scripts/memory-rotate.sh"
echo ""
echo "    5. (Optional) Add more agents:"
echo "       bash install.sh  (run again with different agent name)"
echo ""
echo "============================================"
echo "  Done. Happy coding!"
echo "============================================"
