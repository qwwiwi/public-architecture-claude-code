#!/usr/bin/env bash
set -euo pipefail

# Groq Whisper voice transcription
# Usage: bash transcribe.sh /path/to/audio.ogg

FILE_PATH="${1:?Usage: transcribe.sh <audio-file>}"

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: file not found: $FILE_PATH" >&2
    exit 1
fi

# Read API key from shared secrets
KEY_FILE="${HOME}/.claude-lab/shared/secrets/groq-api-key"
if [ ! -f "$KEY_FILE" ]; then
    echo "Error: Groq API key not found at $KEY_FILE" >&2
    echo "Get a free key at https://console.groq.com" >&2
    echo "Then: echo 'your-key' > $KEY_FILE" >&2
    exit 1
fi

GROQ_API_KEY="$(cat "$KEY_FILE")"

RESPONSE=$(curl -sS --max-time 30 \
    "https://api.groq.com/openai/v1/audio/transcriptions" \
    -H "Authorization: Bearer ${GROQ_API_KEY}" \
    -F "file=@${FILE_PATH}" \
    -F "model=whisper-large-v3-turbo" \
    -F "response_format=text")

if [ -z "$RESPONSE" ]; then
    echo "Error: empty response from Groq API" >&2
    exit 1
fi

echo "Transcript: $RESPONSE"
