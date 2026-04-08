#!/bin/bash
set -euo pipefail

# compress-warm.sh -- Sonnet re-compression of WARM memory
# Groups related events into topic-based key facts
# Conditions: WARM > 10KB or > 50 summary lines
# IMPORTANT: runs claude from /tmp to avoid loading project CLAUDE.md

WS="${AGENT_WORKSPACE:-.claude}"
WARM="$WS/core/warm/decisions.md"
LOCKFILE="/tmp/compress-warm.lock"
LOG="/tmp/compress-warm.log"
MIN_SIZE=10240
MIN_LINES=50
SONNET_BUDGET="0.15"

log() { echo "$(date -u +%H:%M:%S) $1" >> "$LOG"; }
echo "=== compress-warm.sh $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

[ ! -f "$WARM" ] && log "No decisions.md, skip" && exit 0

SIZE=$(wc -c < "$WARM")
LINES=$(grep -c '^- ' "$WARM" 2>/dev/null || echo 0)
log "WARM: ${SIZE} bytes, ${LINES} summary lines"

if [ "$SIZE" -lt "$MIN_SIZE" ] && [ "$LINES" -lt "$MIN_LINES" ]; then
    log "WARM too small, skip"
    exit 0
fi

exec 200>"$LOCKFILE"
flock -n 200 || { log "Lock held, skip"; exit 0; }

# Separate static header from auto-compressed sections
HEADER=$(mktemp)
BODY=$(mktemp)
trap 'rm -f "$HEADER" "$BODY"' EXIT

IN_STATIC=1
while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ auto-compressed ]] || [[ "$line" =~ Sonnet-compressed ]]; then
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

BODY_LINES=$(grep -c '^- ' "$BODY" 2>/dev/null || echo 0)
log "Body has ${BODY_LINES} lines to compress"

if [ "$BODY_LINES" -lt 20 ]; then
    log "Body too small, skip"
    exit 0
fi

BODY_CONTENT=$(grep '^- ' "$BODY")

PROMPT="Compress these ${BODY_LINES} event entries into 15-20 KEY FACTS grouped by topic.
Rules:
- Group related events (e.g. 10 backup entries = 1 line)
- Format: - TOPIC: key fact/decision/result
- Max 120 chars per line
- Remove: duplicates, errors, intermediate steps
- ONLY output lines starting with '- '. Nothing else.

Entries:
${BODY_CONTENT}"

log "Sending to Sonnet..."

RESULT=$(cd /tmp && echo "$PROMPT" | claude --model sonnet --print \
    --no-session-persistence \
    --system-prompt "Compress memory logs into key facts. Output ONLY lines starting with '- '. Group by topic." \
    --max-budget-usd "$SONNET_BUDGET" 2>/dev/null) || RESULT=""

if [ -z "$RESULT" ]; then
    log "Sonnet unavailable, skip"
    exit 0
fi

COMPRESSED=$(echo "$RESULT" | grep '^- ' || true)
COMPRESSED_COUNT=$(echo "$COMPRESSED" | wc -l)

if [ "$COMPRESSED_COUNT" -lt 3 ]; then
    log "Too few lines (${COMPRESSED_COUNT}), skip"
    exit 0
fi

log "Sonnet OK: ${BODY_LINES} -> ${COMPRESSED_COUNT} facts"

TODAY=$(date -u +%Y-%m-%d)
{
    cat "$HEADER"
    echo ""
    echo "## ${TODAY} (Sonnet-compressed)"
    echo ""
    echo "$COMPRESSED"
    echo ""
} > "$WARM"

NEW_SIZE=$(wc -c < "$WARM")
log "WARM: ${SIZE}b -> ${NEW_SIZE}b"
log "Done."
