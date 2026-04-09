---
name: perplexity-research
description: Web research via Perplexity Sonar API -- search, fact-check, analyze trends
---

# Perplexity Research -- Web Search

Search the web, fact-check claims, analyze trends, and find best practices using the Perplexity Sonar API.

## Usage

When the user asks to research a topic, fact-check, or find current information:

1. Get API key from `~/.claude-lab/shared/secrets/perplexity.env`
2. Query Perplexity Sonar API
3. Return structured results with sources

## API Key

- Paid: perplexity.ai (API access required)
- Store key in: `~/.claude-lab/shared/secrets/perplexity.env`

## Example

```bash
PPLX_KEY=$(cat ~/.claude-lab/shared/secrets/perplexity.env)
curl -X POST "https://api.perplexity.ai/chat/completions" \
  -H "Authorization: Bearer $PPLX_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sonar",
    "messages": [
      {"role": "user", "content": "What are the best practices for Claude Code agent architecture in 2026?"}
    ]
  }'
```

## When to Use

- Current events, news, trends
- Best practices and recommendations
- Fact-checking claims
- Competitor analysis
- Technology comparisons
- Market research
