#!/bin/bash
set -euo pipefail

# memory-rotate.sh -- Archive COLD memory when it gets too large
# COLD (MEMORY.md) > 5KB -> archive/YYYY-MM.md

WS="${AGENT_WORKSPACE:-.claude}"
COLD="$WS/core/MEMORY.md"
ARCHIVE_DIR="$WS/core/archive"
LOG="/tmp/memory-rotate.log"

echo "=== memory-rotate.sh $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

[ ! -f "$COLD" ] && echo "No MEMORY.md" >> "$LOG" && exit 0

SIZE=$(wc -c < "$COLD")
echo "MEMORY.md: ${SIZE}b (rotate if >5000b)" >> "$LOG"

if [ "$SIZE" -lt 5000 ]; then
    echo "Too small, skip" >> "$LOG"
    exit 0
fi

MONTH=$(date -u -d "last month" +%Y-%m)
mkdir -p "$ARCHIVE_DIR"
cp "$COLD" "$ARCHIVE_DIR/${MONTH}.md"
echo "Archived to archive/${MONTH}.md" >> "$LOG"

# Keep only the header in MEMORY.md
head -5 "$COLD" > "${COLD}.tmp"
mv "${COLD}.tmp" "$COLD"
echo "MEMORY.md trimmed to header only" >> "$LOG"
