# AGENTS.md — Agent Configuration

## Models

- **Primary:** Claude Opus 4.6 (Anthropic Max subscription)
- **Subagents:** Native Claude Code Agent tool (inherit parent model)
- **Research:** Perplexity Sonar (web search only, no code)

## Subagents

- Native Claude Code Agent tool only
- Maximum 5 subagents simultaneously
- Heavy work → subagents. Architecture and review → main agent.

## Task Acceptance

1. Task unclear? → ask clarifying questions
2. Task not mine? → reject with reasoning
3. Task clear? → execute or delegate to subagent

## OpenViking (L4 Semantic)

- URL: http://127.0.0.1:1933
- Account: myproject
- Key: ~/secrets/openviking.key
- Search: POST /api/v1/search/find
