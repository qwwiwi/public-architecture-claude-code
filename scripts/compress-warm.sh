#!/bin/bash
set -euo pipefail

# compress-warm.sh -- Sonnet compression of WARM memory (decisions.md)
# Triggers: cron daily, only runs if WARM > 10KB or > 50 summary lines
# Groups related events into topic-based key facts
# Fallback: skip if Sonnet unavailable (WARM stays as-is until next run)
# IMPORTANT: runs claude from /tmp to avoid loading project CLAUDE.md context

WS="/home/openclaw/.claude-lab/thrall/.claude"
WARM="$WS/core/warm/decisions.md"
LOCKFILE="/tmp/compress-warm.lock"
LOGDIR="/home/openclaw/.claude-lab/thrall/logs"
LOG="$LOGDIR/compress-warm.log"
MIN_SIZE=4096
MIN_LINES=30
SONNET_BUDGET="0.15"

mkdir -p "$LOGDIR"

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" >> "$LOG"; }

log "=== compress-warm.sh START ==="

[ ! -f "$WARM" ] && log "No decisions.md, skip" && exit 0

SIZE=$(wc -c < "$WARM")
LINES=$(grep -c "^- " "$WARM" 2>/dev/null || echo 0)

log "WARM: ${SIZE} bytes, ${LINES} summary lines"

if [ "$SIZE" -lt "$MIN_SIZE" ] && [ "$LINES" -lt "$MIN_LINES" ]; then
    log "WARM too small (${SIZE}b, ${LINES} lines), skip"
    exit 0
fi

exec 200>"$LOCKFILE"
flock -n 200 || { log "Lock held, skip"; exit 0; }

# --- Phase 1: Separate static header from auto-compressed sections ---
HEADER=$(mktemp)
BODY=$(mktemp)
cleanup_warm() { rm -f "$HEADER" "$BODY"; }; trap cleanup_warm EXIT

IN_STATIC=1

while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^##.*auto-compressed ]] || [[ "$line" =~ ^##.*Sonnet-compressed ]]; then
        IN_STATIC=0
        echo "$line" >> "$BODY"
    elif [[ "$line" =~ ^##[[:space:]]([0-9]{4}-[0-9]{2}-[0-9]{2}) ]] && [ "$IN_STATIC" -eq 0 ]; then
        echo "$line" >> "$BODY"
    elif [ "$IN_STATIC" -eq 1 ]; then
        echo "$line" >> "$HEADER"
    else
        echo "$line" >> "$BODY"
    fi
done < "$WARM"

BODY_LINES=$(grep -c "^- " "$BODY" 2>/dev/null || echo 0)
log "Static header kept, body has ${BODY_LINES} lines to compress"

if [ "$BODY_LINES" -lt 20 ]; then
    log "Body too small (${BODY_LINES} lines), skip compression"
    exit 0
fi

# --- Phase 2: Sonnet compression ---
BODY_CONTENT=$(grep "^- " "$BODY")

PROMPT="You are a memory compressor for an AI agent. Compress these ${BODY_LINES} event entries into 15-20 KEY FACTS grouped by topic.

Rules:
- Group related events into one line (e.g. 10 backup entries = 1 line about backups)
- Format: - TOPIC: key fact/decision/result
- Max 120 chars per line
- Extract: what was done, final result, important decisions
- Remove: duplicates, gateway errors, status updates without substance, intermediate steps
- Language: Russian
- No emoji, no timestamps (just the facts)
- ONLY output lines starting with - . Nothing else.

Event entries:
${BODY_CONTENT}"

log "Sending ${BODY_LINES} lines to Sonnet..."

SONNET_RESULT=$(cd /tmp && echo "$PROMPT" | claude --model sonnet --print \
    --no-session-persistence \
    --system-prompt "You compress AI agent memory logs into key facts. Output ONLY lines starting with - . Nothing else. Group by topic, not chronology." \
    --max-budget-usd "$SONNET_BUDGET" 2>/dev/null) || SONNET_RESULT=""

if [ -z "$SONNET_RESULT" ]; then
    log "Sonnet unavailable, skip (will retry next run)"
    exit 0
fi

COMPRESSED=$(echo "$SONNET_RESULT" | grep "^- " || true)
COMPRESSED_COUNT=$(echo "$COMPRESSED" | wc -l)

if [ "$COMPRESSED_COUNT" -lt 3 ]; then
    log "Sonnet returned too few lines (${COMPRESSED_COUNT}), skip"
    exit 0
fi

log "Sonnet OK: ${BODY_LINES} lines -> ${COMPRESSED_COUNT} facts"

# --- Phase 3: Find date range ---
TODAY=$(date -u +%Y-%m-%d)
FIRST_DATE=$(grep -oP "^\- \K[0-9]{4}-[0-9]{2}-[0-9]{2}" "$BODY" | head -1 || echo "$TODAY")

# --- Phase 4: Rebuild WARM ---
{
    cat "$HEADER"
    echo ""
    echo "## ${FIRST_DATE} -- ${TODAY} (Sonnet-compressed)"
    echo ""
    echo "$COMPRESSED"
    echo ""
} > "$WARM"

NEW_SIZE=$(wc -c < "$WARM")
log "WARM: ${SIZE}b -> ${NEW_SIZE}b (saved $((SIZE - NEW_SIZE))b)"
log "=== compress-warm.sh DONE ==="
