#!/bin/bash
set -euo pipefail

# rotate-warm.sh -- Move WARM entries >14 days to COLD
# Pure bash, no model calls

WS="${AGENT_WORKSPACE:-.claude}"
WARM="$WS/core/warm/decisions.md"
COLD="$WS/core/MEMORY.md"
LOG="/tmp/rotate-warm.log"
MAX_AGE_DAYS=14

log() { echo "$(date -u +%H:%M:%S) $1" >> "$LOG"; }
echo "=== rotate-warm.sh $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

[ ! -f "$WARM" ] && log "No decisions.md, skip" && exit 0

CUTOFF=$(date -u -d "${MAX_AGE_DAYS} days ago" +%Y-%m-%d)

KEEP=$(mktemp)
ARCHIVE=$(mktemp)
trap 'rm -f "$KEEP" "$ARCHIVE"' EXIT

CURRENT_SECTION=""
CURRENT_DATE=""
ROTATED=0
KEPT=0

while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^##[[:space:]]([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
        if [ -n "$CURRENT_DATE" ]; then
            if [[ "$CURRENT_DATE" < "$CUTOFF" ]]; then
                printf '%s\n' "$CURRENT_SECTION" >> "$ARCHIVE"
                ROTATED=$((ROTATED + 1))
            else
                printf '%s\n' "$CURRENT_SECTION" >> "$KEEP"
                KEPT=$((KEPT + 1))
            fi
        fi
        CURRENT_SECTION="$line"
        CURRENT_DATE="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^#[[:space:]] ]] || [[ "$line" =~ ^_ ]]; then
        echo "$line" >> "$KEEP"
    else
        if [ -n "$CURRENT_SECTION" ]; then
            CURRENT_SECTION="$CURRENT_SECTION
$line"
        else
            echo "$line" >> "$KEEP"
        fi
    fi
done < "$WARM"

if [ -n "$CURRENT_DATE" ]; then
    if [[ "$CURRENT_DATE" < "$CUTOFF" ]]; then
        printf '%s\n' "$CURRENT_SECTION" >> "$ARCHIVE"
        ROTATED=$((ROTATED + 1))
    else
        printf '%s\n' "$CURRENT_SECTION" >> "$KEEP"
        KEPT=$((KEPT + 1))
    fi
fi

if [ -s "$ARCHIVE" ]; then
    { echo ""; echo "## Archived from WARM ($(date -u +%Y-%m-%d))"; echo ""; cat "$ARCHIVE"; } >> "$COLD"
    log "Rotated ${ROTATED} sections to COLD"
fi

cp "$KEEP" "$WARM"
log "Kept: ${KEPT}, Rotated: ${ROTATED}"
log "Done."
