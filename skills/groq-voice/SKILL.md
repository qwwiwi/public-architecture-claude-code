---
name: groq-voice
description: Transcribe voice messages (.ogg) via Groq Whisper API. When you see <media:audio> in a message, extract the file path and transcribe it using the included script.
user-invocable: false
---

# Groq Voice Transcription

When you receive a message containing `<media:audio>` tag, the user sent a voice message.

## MANDATORY: Transcribe BEFORE responding

When you see `<media:audio>`:

1. Extract the .ogg file path from the `[media attached: /path/to/file.ogg]` line
2. Run the transcription script:
```bash
bash $CLAUDE_SKILL_DIR/scripts/transcribe.sh "/path/to/file.ogg"
```
3. Use the transcript text to understand what the user said
4. Respond to the user's spoken message naturally
5. Do NOT mention the transcription process unless asked

## Important

- Always transcribe first, then respond to the content
- The script uses Groq Whisper API (fast, accurate, supports Russian and 50+ languages)
- If transcription fails, tell the user you couldn't process their voice message
- Do NOT say "I can't listen to audio" -- you CAN via this script

## Setup

1. Get a free API key at https://console.groq.com
2. Save it: `echo 'your-key' > ~/.claude-lab/shared/secrets/groq-api-key`
3. The script reads the key from that file automatically
