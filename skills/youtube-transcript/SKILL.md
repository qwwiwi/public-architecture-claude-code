---
name: youtube-transcript
description: "Fetch YouTube video transcripts via TranscriptAPI. Use when: YouTube link, transcript, summarize video, what's in the video."
user-invocable: true
argument-hint: "<youtube-url>"
---

# YouTube Transcript

Fetches YouTube video transcripts with timestamps and metadata.

## Setup

1. Register at https://transcriptapi.com (100 free credits)
2. Save API key:
```bash
echo 'your-api-key' > ~/.claude-lab/shared/secrets/transcript-api-key
```

Or use the auth script:
```bash
node $CLAUDE_SKILL_DIR/scripts/tapi-auth.js register --email your@email.com
# Check email for OTP code
node $CLAUDE_SKILL_DIR/scripts/tapi-auth.js verify --token TOKEN --otp CODE
```

## Usage

```bash
TAPI_KEY=$(cat ~/.claude-lab/shared/secrets/transcript-api-key)

curl -sS "https://transcriptapi.com/api/v2/youtube/transcript?video_url=VIDEO_URL&format=text&include_timestamp=true&send_metadata=true" \
  -H "Authorization: Bearer $TAPI_KEY"
```

## Accepted URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/shorts/VIDEO_ID`
- Bare 11-character video ID

## Parameters

| Parameter | Value | Required |
|-----------|-------|----------|
| `video_url` | YouTube URL or ID | Yes |
| `format` | `text` (recommended) or `json` | Yes |
| `include_timestamp` | `true` | Recommended |
| `send_metadata` | `true` (title, author, thumbnail) | Recommended |

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 401 | Invalid API key | Check key file |
| 402 | No credits left | Buy more or new account |
| 404 | No transcript available | Video has no captions |
| 408 | Timeout | Retry once |
| 429 | Rate limited (300 req/min) | Wait and retry |

## Pricing

- Free tier: 100 credits
- 1 credit = 1 successful transcript request
- Rate limit: 300 requests/minute
