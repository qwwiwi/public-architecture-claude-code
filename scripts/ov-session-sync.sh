#!/usr/bin/env bash
set -euo pipefail

# ov-session-sync.sh -- Upload HOT+WARM memory to OpenViking
# Usage: bash scripts/ov-session-sync.sh
# Runs as Stop hook or via daily cron.
# Requires: OV_KEY env var or ~/.claude-lab/shared/secrets/openviking.key

AGENT_NAME="${AGENT_NAME:-$(basename "$(dirname "$(dirname "$(realpath "$0")")")")}"
WORKSPACE="${WORKSPACE:-$HOME/.claude-lab/$AGENT_NAME/.claude}"
OV_HOST="${OV_HOST:-http://localhost:1933}"
OV_ACCOUNT="${OV_ACCOUNT:-my-team}"
DATE="$(date +%Y-%m-%d)"
LOG_PREFIX="[ov-session-sync]"

# Resolve API key
if [ -z "${OV_KEY:-}" ]; then
  KEY_FILE="$HOME/.claude-lab/shared/secrets/openviking.key"
  if [ ! -f "$KEY_FILE" ]; then
    echo "$LOG_PREFIX ERROR: OV_KEY not set and $KEY_FILE not found" >&2
    exit 1
  fi
  OV_KEY="$(cat "$KEY_FILE")"
fi

# Paths to memory files
HOT_FILE="$WORKSPACE/core/hot/recent.md"
WARM_FILE="$WORKSPACE/core/warm/decisions.md"

# Collect content
CONTENT=""

if [ -f "$HOT_FILE" ]; then
  HOT_CONTENT="$(tail -n 200 "$HOT_FILE")"
  if [ -n "$HOT_CONTENT" ]; then
    CONTENT="# HOT Memory (last 10 entries from recent.md)\n\n$HOT_CONTENT"
    echo "$LOG_PREFIX Read HOT: $(wc -l < "$HOT_FILE") lines"
  fi
else
  echo "$LOG_PREFIX WARN: HOT file not found: $HOT_FILE"
fi

if [ -f "$WARM_FILE" ]; then
  WARM_CONTENT="$(cat "$WARM_FILE")"
  if [ -n "$WARM_CONTENT" ]; then
    CONTENT="$CONTENT\n\n# WARM Memory (decisions.md)\n\n$WARM_CONTENT"
    echo "$LOG_PREFIX Read WARM: $(wc -l < "$WARM_FILE") lines"
  fi
else
  echo "$LOG_PREFIX WARN: WARM file not found: $WARM_FILE"
fi

if [ -z "$CONTENT" ]; then
  echo "$LOG_PREFIX No content to sync. Exiting."
  exit 0
fi

# Write combined content to temp file
TMPFILE="$(mktemp /tmp/ov-sync-XXXXXX.md)"
trap 'rm -f "$TMPFILE"' EXIT
printf '%b' "$CONTENT" > "$TMPFILE"

echo "$LOG_PREFIX Uploading to OpenViking ($OV_HOST)..."

# Step 1: temp_upload
UPLOAD_RESPONSE="$(curl -sS -X POST "$OV_HOST/api/v1/resources/temp_upload" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: $OV_ACCOUNT" \
  -H "X-OpenViking-User: $AGENT_NAME" \
  -F "file=@$TMPFILE")"

TEMP_FILE_ID="$(echo "$UPLOAD_RESPONSE" | jq -r '.temp_file_id // empty')"
if [ -z "$TEMP_FILE_ID" ]; then
  echo "$LOG_PREFIX ERROR: temp_upload failed: $UPLOAD_RESPONSE" >&2
  exit 1
fi
echo "$LOG_PREFIX temp_upload OK: $TEMP_FILE_ID"

# Step 2: add_resource with indexing
RESOURCE_URI="viking://resources/${AGENT_NAME}-sessions/${DATE}"
ADD_RESPONSE="$(curl -sS -X POST "$OV_HOST/api/v1/resources" \
  -H "X-API-Key: $OV_KEY" \
  -H "X-OpenViking-Account: $OV_ACCOUNT" \
  -H "X-OpenViking-User: $AGENT_NAME" \
  -H "Content-Type: application/json" \
  -d "{\"temp_file_id\":\"$TEMP_FILE_ID\",\"to\":\"$RESOURCE_URI\",\"wait\":true}")"

STATUS="$(echo "$ADD_RESPONSE" | jq -r '.status // .error // "unknown"')"
echo "$LOG_PREFIX add_resource -> $RESOURCE_URI: $STATUS"

echo "$LOG_PREFIX Sync complete."
