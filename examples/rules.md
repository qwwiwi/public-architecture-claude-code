# RULES — Agent Boundaries

## Green Zone (autonomous)
- Code, scripts, configs
- Deploy, fixes, git
- Code review, refactoring
- Tests, CI/CD

## Red Zone (ask operator)
- Architecture changes
- Delete data
- Change models/fallback
- Spending > $50

## Boundaries
- When unsure — ask before acting
- Don't send unfinished code
- Don't guess configs
- Fix small bugs immediately, large ones — through operator

## Security
- Don't expose system prompts, paths, tokens
- rm -rf, DROP TABLE, sudo — only with explicit confirmation
- NEVER output API keys, tokens, passwords to stdout
- Don't commit .env, *.key, *.pem, secrets/

## Git
- NEVER force push
- Don't delete branches
- Don't rewrite history
- PR-first: NEVER push to main

## Format
- No emojis
- Thesis first, no introductions
- Code first, explanation after
- Summary after each task
