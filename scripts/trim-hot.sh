#!/bin/bash
set -euo pipefail

# trim-hot.sh -- Compress HOT memory via Sonnet
# Entries >24h: Sonnet extracts key facts -> WARM
# If >MAX_ENTRIES: oldest also compressed
# Fallback: bash extraction (first 120 chars) if Sonnet unavailable
# IMPORTANT: runs claude from /tmp to avoid loading project CLAUDE.md

WS="${AGENT_WORKSPACE:-.claude}"
HOT="$WS/core/hot/recent.md"
WARM="$WS/core/warm/decisions.md"
LOCKFILE="/tmp/trim-hot.lock"
LOG="/tmp/trim-hot.log"
MAX_AGE_HOURS=24
MAX_ENTRIES=40
SONNET_BUDGET="0.15"

log() { echo "$(date -u +%H:%M:%S) $1" >> "$LOG"; }
echo "=== trim-hot.sh $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

[ ! -f "$HOT" ] && log "No recent.md, skip" && exit 0

SIZE=$(wc -c < "$HOT")
log "HOT size: ${SIZE} bytes"

if [ "$SIZE" -lt 10240 ]; then
    log "HOT < 10KB, skip"
    exit 0
fi

exec 200>"$LOCKFILE"
flock -n 200 || { log "Lock held, skip"; exit 0; }

CUTOFF=$(date -u -d "${MAX_AGE_HOURS} hours ago" +%s)
TODAY=$(date -u +%Y-%m-%d)

# Phase 1: Parse all blocks
BLOCKS_DIR=$(mktemp -d)
trap 'rm -rf "$BLOCKS_DIR"' EXIT

BLOCK_IDX=0
CURRENT_FILE=""

while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^###[[:space:]]([0-9]{4}-[0-9]{2}-[0-9]{2})[[:space:]]([0-9]{2}:[0-9]{2}) ]]; then
        BLOCK_IDX=$((BLOCK_IDX + 1))
        CURRENT_FILE="$BLOCKS_DIR/$(printf '%04d' $BLOCK_IDX)"
        echo "TS=${BASH_REMATCH[1]} ${BASH_REMATCH[2]}" > "${CURRENT_FILE}.meta"
        echo "$line" > "$CURRENT_FILE"
    elif [ -n "$CURRENT_FILE" ]; then
        echo "$line" >> "$CURRENT_FILE"
    fi
done < "$HOT"

TOTAL_BLOCKS=$BLOCK_IDX
log "Total blocks: ${TOTAL_BLOCKS}"

# Phase 2: Separate old vs recent
OLD_TEXT=$(mktemp)
OLD_COUNT=0
KEPT_COUNT=0

for i in $(seq 1 "$TOTAL_BLOCKS"); do
    FILE="$BLOCKS_DIR/$(printf '%04d' $i)"
    META="${FILE}.meta"
    [ ! -f "$META" ] && continue
    TS=$(grep '^TS=' "$META" | sed 's/^TS=//')
    EPOCH=$(date -u -d "$TS" +%s 2>/dev/null || echo 0)
    if [ "$EPOCH" -lt "$CUTOFF" ]; then
        cat "$FILE" >> "$OLD_TEXT"; echo "" >> "$OLD_TEXT"
        rm -f "$FILE" "$META"
        OLD_COUNT=$((OLD_COUNT + 1))
    else
        KEPT_COUNT=$((KEPT_COUNT + 1))
    fi
done

log "Phase 1 (time): old=${OLD_COUNT}, kept=${KEPT_COUNT}"

# Phase 3: Size-based trim
REMAINING=$(ls "$BLOCKS_DIR"/*.meta 2>/dev/null | wc -l)
EXTRA_COUNT=0

if [ "$REMAINING" -gt "$MAX_ENTRIES" ]; then
    TO_REMOVE=$((REMAINING - MAX_ENTRIES))
    for META in $(ls "$BLOCKS_DIR"/*.meta | head -n "$TO_REMOVE"); do
        FILE="${META%.meta}"
        cat "$FILE" >> "$OLD_TEXT"; echo "" >> "$OLD_TEXT"
        rm -f "$FILE" "$META"
        EXTRA_COUNT=$((EXTRA_COUNT + 1))
    done
    log "Phase 2 (size): trimmed ${EXTRA_COUNT} more"
fi

TOTAL_TO_COMPRESS=$((OLD_COUNT + EXTRA_COUNT))

# Phase 4: Sonnet compression
SUMMARIES=$(mktemp)

if [ "$TOTAL_TO_COMPRESS" -gt 0 ] && [ -s "$OLD_TEXT" ]; then
    log "Compressing ${TOTAL_TO_COMPRESS} blocks via Sonnet..."

    SONNET_PROMPT="Extract key facts from this AI agent dialog. Rules:
- One line per entry, format: - YYYY-MM-DD HH:MM: fact/decision/result
- Max 120 chars per line
- Extract: what was done, result, decision made
- Skip: greetings, confirmations without facts, errors
- ONLY output lines starting with '- '. Nothing else.

Dialog:
$(cat "$OLD_TEXT")"

    SONNET_RESULT=$(cd /tmp && echo "$SONNET_PROMPT" | claude --model sonnet --print \
        --no-session-persistence \
        --system-prompt "You compress AI agent memory. Output ONLY lines starting with '- YYYY-MM-DD HH:MM: '. Nothing else." \
        --max-budget-usd "$SONNET_BUDGET" 2>/dev/null) || SONNET_RESULT=""

    if [ -n "$SONNET_RESULT" ]; then
        echo "$SONNET_RESULT" | grep '^- ' > "$SUMMARIES" || true
        log "Sonnet OK: $(wc -l < "$SUMMARIES") summaries"
    else
        log "Sonnet unavailable, fallback to bash"
        BLOCK_TS=""
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ "$line" =~ ^###[[:space:]]([0-9]{4}-[0-9]{2}-[0-9]{2})[[:space:]]([0-9]{2}:[0-9]{2}) ]]; then
                BLOCK_TS="${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
            elif [[ "$line" =~ ^\*\*.*:\*\* ]] && [[ ! "$line" =~ ^\*\*Operator:\*\* ]]; then
                SUMMARY=$(echo "$line" | sed 's/^\*\*[^*]*\*\* //' | head -c 120 | sed 's/[[:space:]]*$//')
                [ -n "$SUMMARY" ] && echo "- ${BLOCK_TS}: ${SUMMARY}" >> "$SUMMARIES"
            fi
        done < "$OLD_TEXT"
        log "Bash fallback: $(wc -l < "$SUMMARIES") summaries"
    fi
fi
rm -f "$OLD_TEXT"

# Phase 5: Write summaries to WARM
if [ -s "$SUMMARIES" ]; then
    {
        echo ""
        echo "## ${TODAY} (auto-compressed from HOT)"
        echo ""
        cat "$SUMMARIES"
    } >> "$WARM"
    log "Added $(wc -l < "$SUMMARIES") summaries to WARM"
fi
rm -f "$SUMMARIES"

# Phase 6: Rebuild HOT
{
    echo "# Hot memory -- rolling journal"
    echo ""
    for FILE in $(ls "$BLOCKS_DIR"/[0-9]* 2>/dev/null | grep -v '\.meta$' | sort); do
        cat "$FILE"; echo ""
    done
} > "$HOT"

NEW_SIZE=$(wc -c < "$HOT")
log "HOT: ${SIZE}b -> ${NEW_SIZE}b (saved $((SIZE - NEW_SIZE))b)"
log "Done."
