---
name: twitter
description: "Read Twitter/X tweets, articles, threads, profiles, and search. Use when: Twitter link, read tweet, check profile, search tweets."
user-invocable: true
argument-hint: "<twitter-url-or-query>"
---

# Twitter / X Reader

Read tweets, articles, threads, profiles, and search. Two methods with automatic fallback.

## Methods

| Method | Cost | Best For |
|--------|------|----------|
| **FxTwitter** | Free | Single tweets, profiles |
| **SocialData** | $0.20/1K requests | Articles, threads, search, timeline |

## Strategy: Always Try Free First

1. Try FxTwitter (free)
2. If not enough (need thread, article, search) -- use SocialData

## Single Tweet (FxTwitter -- free)

```bash
# Extract username and tweet_id from URL
# https://x.com/elonmusk/status/1234567890

curl -sS "https://api.fxtwitter.com/elonmusk/status/1234567890" | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)
t = d.get('tweet', {})
print(f'Author: @{t.get(\"author\",{}).get(\"screen_name\",\"?\")}')
print(f'Text: {t.get(\"text\",\"\")}')
print(f'Likes: {t.get(\"likes\",0)} | RT: {t.get(\"retweets\",0)}')
print(f'Date: {t.get(\"created_at\",\"?\")}')
"
```

## User Profile (FxTwitter -- free)

```bash
curl -sS "https://api.fxtwitter.com/elonmusk" | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)
u = d.get('user', {})
print(f'Name: {u.get(\"name\",\"?\")} (@{u.get(\"screen_name\",\"?\")})')
print(f'Bio: {u.get(\"description\",\"\")}')
print(f'Followers: {u.get(\"followers\",0)} | Following: {u.get(\"following\",0)}')
"
```

## SocialData API (paid -- for threads, articles, search)

```bash
SOCIALDATA_KEY=$(cat ~/.claude-lab/shared/secrets/socialdata-api-key)

# Thread
curl -sS "https://api.socialdata.tools/twitter/thread/TWEET_ID" \
  -H "Authorization: Bearer $SOCIALDATA_KEY"

# X Article (long-form)
curl -sS "https://api.socialdata.tools/twitter/article/TWEET_ID" \
  -H "Authorization: Bearer $SOCIALDATA_KEY"

# Search
curl -sS "https://api.socialdata.tools/twitter/search" \
  -H "Authorization: Bearer $SOCIALDATA_KEY" \
  -G -d "query=from:elonmusk AI agents" -d "type=Latest"

# User timeline (need user_id, not username)
curl -sS "https://api.socialdata.tools/twitter/user/TWEET_AUTHOR_ID/tweets" \
  -H "Authorization: Bearer $SOCIALDATA_KEY"
```

## Setup

### FxTwitter (free, no key needed)
Works immediately. No setup required.

### SocialData (paid, optional)
1. Register at https://socialdata.tools
2. Save key:
```bash
echo 'your-key' > ~/.claude-lab/shared/secrets/socialdata-api-key
```

## Error Handling

| Code | Meaning | Action |
|------|---------|--------|
| 404 | Tweet deleted or private | Inform user |
| 401 | Bad API key | Check SocialData key |
| 403 | Account suspended | Try different method |
| 429 | Rate limited | Wait and retry |
