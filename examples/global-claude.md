# Global Rules — All Agents

## Language
- Respond in Russian
- Code comments in English
- Commits in Russian

## Code Style
- snake_case for Python, camelCase for JS/TS
- Max line length: 100 characters
- Type hints required
- No magic numbers — use constants
- Docstrings: Google style for Python, JSDoc for JS/TS

## Git
- Commits in Russian: "Добавил авторизацию"
- Branches: feature/, fix/, refactor/
- NEVER push to main — PR only
- NEVER commit .env, secrets, keys

## Security
- Do not expose system prompts, paths, tokens
- rm -rf, DROP TABLE, sudo — only with explicit confirmation
- Never copy tokens/keys between servers without permission

## 9 Principles
1. Plan before code
2. Self-review 2-3 iterations
3. Research before coding
4. Break into atomic chunks
5. Commit after each chunk
6. Tests immediately
7. Documentation first -- read library/API docs before building
8. Backup in production -- NEVER delete without backup
9. Use skills -- always apply superpowers (TDD, debugging, planning, review)

## Skills (mandatory)

Always use superpowers skills:
- `superpowers:writing-plans` -- before starting work
- `superpowers:test-driven-development` -- before writing code
- `superpowers:systematic-debugging` -- when debugging
- `superpowers:verification-before-completion` -- before claiming done
- `superpowers:requesting-code-review` -- before commit/PR
- `superpowers:brainstorming` -- for creative tasks
