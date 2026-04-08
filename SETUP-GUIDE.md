# End-to-End Setup Guide

Пошаговая инструкция. Копируй промпты, вставляй в Claude Code -- всё установится автоматически.

**Важно:** Этот гайд читают агенты (Claude Code с Superpowers), не люди. Каждый шаг -- точная инструкция для агента. Ничего не пропускать.

## Что получишь

- Claude Code с настроенной архитектурой памяти (4 слоя)
- Telegram-бот для интерактивной работы с Claude Code
- (Опционально) Автономный агент JARVIS с Telegram gateway
- Superpowers: TDD, дебаг, планирование, code review

## Требования

- VPS (Ubuntu 22.04+) или Mac с SSH-доступом
- Подписка Anthropic Max ($100-200/мес) или API key
- Telegram аккаунт

---

## Шаг 1: Установи Claude Code

```bash
# Установи Claude Code (если ещё не установлен)
npm install -g @anthropic-ai/claude-code

# Авторизуйся
claude

# Внутри Claude Code выбери: Login with Anthropic
# Следуй инструкциям в браузере
```

После авторизации закрой сессию (`/exit`) и переходи к шагу 2.

---

## Шаг 2: Переключись на Opus

```bash
# Запусти Claude Code
claude

# Переключись на Opus (обязательно для архитектуры)
/model opus
```

---

## Шаг 3: Создай глобальный CLAUDE.md

Скопируй этот промпт и вставь в Claude Code:

```
Создай файл ~/.claude/CLAUDE.md со следующим содержанием:

# Global Rules

## Language
- Respond in Russian
- Code comments in English
- Commits in Russian

## Code Style
- Python: snake_case, type hints, Google docstrings, pathlib, f-strings
- TypeScript: strict, no any, interface > type, camelCase
- Bash: set -euo pipefail, quote variables
- Max line: 100 chars
- No magic numbers -- use constants
- Logging via logging module, not print

## Git
- Never push to main -- PR only
- Branches: feature/, fix/, refactor/
- Commits in Russian: «Добавил авторизацию»

## Security
- Never commit .env, secrets, keys
- No sudo, rm -rf without confirmation
- No var in JavaScript

## Format
- Code first, explanation after
- Be concise
- No emoji
```

---

## Шаг 4: Установи Superpowers

Скопируй этот промпт:

```
Установи плагин Superpowers:

1. Зарегистрируй маркетплейс:
claude plugins marketplace add obra/superpowers-marketplace

2. Установи плагин:
claude plugins install superpowers@superpowers-marketplace

Запусти обе команды через Bash.
```

---

## Шаг 5: Настрой GitHub CLI

```
Проверь, установлен ли gh (GitHub CLI):
gh --version

Если не установлен:
sudo apt install gh

Авторизуйся:
gh auth login

Выбери GitHub.com, HTTPS, Login with a web browser.
```

---

## Шаг 6: Разверни архитектуру

Это главный шаг. Скопируй этот промпт в Claude Code:

```
Изучи архитектуру по ссылке https://github.com/qwwiwi/public-architecture-claude-code и разверни её на этом сервере.

ВАЖНО: Прочитай ВСЕ файлы в репозитории. Ни один файл не пропускай. Список обязательных для чтения:
- README.md
- ARCHITECTURE.md -- точки входа, загрузка контекста, gateway flow, session management
- STRUCTURE.md -- дерево директорий, что изолировано vs shared
- MEMORY.md -- 4 слоя памяти, flush, compaction, rotation, cron, OpenViking, token budget
- CHECKLIST.md -- чеклист создания агента
- SKILLS.md -- как создавать скиллы, формат, frontmatter
- SUBAGENTS.md -- как создавать субагентов, agents/*.md, built-in типы
- HOOKS.md -- lifecycle hooks, universal (block dangerous, protect files, command logging) + project-specific
- examples/global-claude.md -- шаблон глобального CLAUDE.md
- examples/agent-claude.md -- шаблон CLAUDE.md агента
- examples/agents.md -- шаблон AGENTS.md
- examples/rules.md -- шаблон rules.md
- examples/tools.md -- шаблон TOOLS.md
- skills/super-power.md -- документация Superpowers

После прочтения ВСЕХ файлов:

1. Создай структуру директорий по STRUCTURE.md:
   ~/.claude-lab/shared/skills/
   ~/.claude-lab/shared/gateway/
   ~/.claude-lab/claude-code/.claude/
   ~/.claude-lab/claude-code/.claude/core/
   ~/.claude-lab/claude-code/.claude/core/warm/
   ~/.claude-lab/claude-code/.claude/core/hot/
   ~/.claude-lab/claude-code/.claude/tools/
   ~/.claude-lab/claude-code/.claude/skills/
   ~/.claude-lab/claude-code/.claude/agents/
   ~/.claude-lab/claude-code/.claude/scripts/
   ~/.claude-lab/claude-code/secrets/ (chmod 700)

2. Создай identity-файлы по шаблонам из examples/:
   - ~/.claude-lab/claude-code/.claude/CLAUDE.md (из examples/agent-claude.md) с @include для всех core-файлов
   - ~/.claude-lab/claude-code/.claude/core/AGENTS.md (из examples/agents.md)
   - ~/.claude-lab/claude-code/.claude/core/USER.md (пустой шаблон, заполнится на шаге 7)
   - ~/.claude-lab/claude-code/.claude/core/rules.md (из examples/rules.md)
   - ~/.claude-lab/claude-code/.claude/tools/TOOLS.md (из examples/tools.md)

3. Создай пустые файлы памяти:
   - core/warm/decisions.md (заголовок: "# WARM DECISIONS")
   - core/hot/recent.md (заголовок: "# Hot memory -- last 72h rolling journal")
   - core/MEMORY.md (заголовок: "# MEMORY -- Cold Archive")
   - core/LEARNINGS.md (заголовок: "# LEARNINGS")

4. Настрой universal hooks по HOOKS.md:
   - Создай .claude/hooks/block-dangerous.sh (block rm -rf, force push, DROP)
   - Создай .claude/hooks/protect-files.sh (block .env, .key, secrets)
   - Создай .claude/hooks/log-commands.sh (audit trail)
   - chmod +x .claude/hooks/*.sh
   - Добавь hooks в .claude/settings.json (universal settings из HOOKS.md)

5. Создай скрипты ротации памяти:
   - scripts/trim-hot.sh -- удаляет записи >72h из hot/recent.md
   - scripts/rotate-warm.sh -- переносит записи >14d из warm/decisions.md в MEMORY.md
   - chmod +x scripts/*.sh

6. Добавь cron jobs:
   - 0 5 * * * trim-hot.sh
   - 0 4 * * * rotate-warm.sh

   IMPORTANT: Memory compression is the most important operational feature.
   Without it, HOT memory grows to 80KB+ per day and degrades agent quality.
   The 4 cron scripts keep memory clean and focused. If cron is not running,
   the agent will accumulate raw conversation logs that consume 70%+ of
   startup context and cause instruction-following degradation.
   See MEMORY.md "Token Budget" section for detailed calculations.

Имя агента: claude-code
Workspace: ~/.claude-lab/claude-code/.claude/

После создания покажи:
1. Полное дерево файлов (tree)
2. Содержимое CLAUDE.md агента (с @include)
3. Содержимое settings.json (hooks)
4. Список cron jobs
```

---

## Шаг 7: Заполни identity-файлы

После создания архитектуры настрой файлы под себя:

```
Помоги заполнить identity-файлы для моего агента:

1. core/USER.md -- мой профиль:
   - Имя: [ваше имя]
   - Роль: [чем занимаетесь]
   - Язык: русский
   - Часовой пояс: [UTC+X]

2. core/AGENTS.md -- настройки:
   - Основная модель: Opus
   - Субагенты: Sonnet (через Agent tool)
   - Максимум 5 субагентов одновременно

3. core/rules.md -- границы:
   - Не удалять код без причины
   - Не менять то, о чём не просили
   - Спрашивать перед масштабными изменениями
   - Не коммитить секреты

4. tools/TOOLS.md -- мои серверы и инструменты:
   [опиши свои серверы, Docker, сервисы]

Покажи результат каждого файла.
```

---

## Шаг 8: Подключи Telegram (интерактивный режим)

Для интерактивной работы с Claude Code через Telegram:

```
Установи Telegram-плагин для Claude Code:
https://github.com/RichardAtCT/claude-code-telegram

Следуй инструкциям из README:
1. Создай бота через @BotFather в Telegram
2. Установи пакет через uv tool install
3. Настрой переменные окружения (токен, user ID, рабочая директория)
4. Запусти
```

---

## Шаг 9 (опционально): Автономный агент с JARVIS Gateway

Для автономного агента с голосовыми, прогрессом, памятью:

```
Разверни JARVIS Telegram Gateway по инструкции:
https://github.com/qwwiwi/jarvis-telegram-gateway

1. Склонируй репозиторий
2. Скопируй config.example.json в config.json
3. Создай второго бота через @BotFather
4. Заполни config.json (токен, user ID, workspace)
5. Получи Groq API key на https://console.groq.com (для голосовых)
6. Запусти: python3 gateway.py
7. (Опционально) Настрой как systemd-сервис для автозапуска

Workspace для JARVIS: ~/.claude-lab/jarvis/.claude/
Создай отдельные identity-файлы для JARVIS (другой SOUL, другой характер).
```

---

## Шаг 10: Проверь

```
Проверь что архитектура работает. Пройди по каждому пункту:

1. Покажи дерево ~/.claude-lab/ (tree -L 4)
2. Покажи содержимое CLAUDE.md агента -- проверь что все @include на месте:
   @core/AGENTS.md
   @core/USER.md
   @core/rules.md
   @tools/TOOLS.md
   @core/warm/decisions.md
   @core/hot/recent.md
3. Проверь что файлы памяти существуют и не пустые:
   core/hot/recent.md
   core/warm/decisions.md
   core/MEMORY.md
   core/LEARNINGS.md
4. Проверь hooks:
   ls -la .claude/hooks/
   cat .claude/settings.json
5. Проверь cron:
   crontab -l | grep -E "trim|rotate"
6. Проверь Superpowers: claude plugins list
7. Проверь gh: gh auth status
8. (Если Telegram) Отправь тестовое сообщение боту

Для каждого пункта покажи результат. Если что-то не настроено -- исправь.
```

---

## Базовые скиллы

После настройки архитектуры, добавь базовые скиллы. Скопируй этот промпт:

```
Создай базовые скиллы для агента в ~/.claude-lab/claude-code/.claude/skills/:

1. groq-voice/ -- транскрибация голосовых через [Groq](https://groq.com) Whisper API
   SKILL.md с инструкциями + transcribe.sh скрипт
   Нужен Groq API key (https://console.groq.com)

2. web-research/ -- веб-ресёрч через WebSearch/WebFetch
   SKILL.md с инструкциями по поиску информации
   Бесплатный (через встроенные инструменты Claude Code)

3. learnings/ -- уроки из ошибок
   SKILL.md с форматом записи уроков
   Хранит в core/LEARNINGS.md

4. git-workflows/ -- продвинутый git
   SKILL.md с инструкциями по rebase, worktrees, cherry-pick
```

---

## Итоговая структура

После всех шагов у тебя будет:

```
~/.claude/
├── CLAUDE.md                    глобальные правила
├── rules/*.md                   конвенции языков
├── settings.json                universal hooks
├── hooks/
│   ├── block-dangerous.sh       блокирует rm -rf, force push
│   ├── protect-files.sh         блокирует .env, .key, secrets
│   └── log-commands.sh          audit trail
└── plugins/superpowers          TDD, дебаг, ревью

~/.claude-lab/
├── shared/
│   ├── skills/                  общие скиллы
│   └── gateway/                 Telegram gateway (если шаг 9)
│
├── claude-code/.claude/         основной агент
│   ├── CLAUDE.md                SOUL + @includes
│   ├── core/
│   │   ├── AGENTS.md            модели
│   │   ├── USER.md              твой профиль
│   │   ├── rules.md             границы
│   │   ├── warm/decisions.md    решения 14 дней
│   │   ├── hot/recent.md        журнал 72 часа
│   │   ├── MEMORY.md            архив (холодная память)
│   │   └── LEARNINGS.md         уроки из ошибок
│   ├── tools/TOOLS.md           серверы
│   ├── skills/                  скиллы агента
│   ├── agents/                  конфиги субагентов
│   ├── scripts/
│   │   ├── trim-hot.sh          cron: удаляет >72h из hot
│   │   └── rotate-warm.sh       cron: переносит >14d в COLD
│   └── secrets/                 ключи (chmod 700)
│
└── jarvis/.claude/              автономный агент (если шаг 9)
    └── (та же структура)
```

## Advanced: Memory Flush (OpenClaw approach)

Продвинутый подход к управлению памятью, вдохновлённый [OpenClaw](https://github.com/openclaw/openclaw).

### Проблема

HOT memory (`recent.md`) растёт бесконтрольно. За активный день может достичь 80+ KB, потребляя 70% стартового контекста. Cron-based trim -- грубый инструмент, удаляющий по времени, а не по ценности.

### Решение: Event-driven flush

Вместо cron-based ротации -- **автоматический flush перед компакцией:**

```
Сессия Claude Code приближается к лимиту контекста
    │
    ▼
АВТОМАТИЧЕСКИЙ silent turn (перед /compact или auto-compact):
    │
    ├── Прочитать core/hot/recent.md
    ├── Извлечь ключевые факты (решения, preferences, pending actions)
    ├── APPEND в memory/YYYY-MM-DD.md (daily файл, НЕ перезаписывать)
    ├── MEMORY.md, LEARNINGS.md -- read-only (не трогать)
    │
    ▼
Обычная компакция (суммаризация старых сообщений)
```

### Ключевые safety-правила для flush

- **APPEND-only** -- daily файлы только дополняются, не перезаписываются
- **Bootstrap файлы read-only** -- MEMORY.md, LEARNINGS.md, CLAUDE.md не трогать при flush
- **Дедупликация** -- маркеры в записях предотвращают дубли при повторном flush
- **Если нечего сохранять** -- пропустить (не создавать пустых записей)

### Dreaming: продвинутая консолидация памяти

OpenClaw реализует 3-фазную систему «сна» для автоматической promotion записей из short-term в long-term:

| Фаза | Частота | Что делает | Пишет в MEMORY.md? |
|------|---------|------------|-------------------|
| **Light Sleep** | Каждые 6ч | Инджест daily файлов, дедупликация | Нет |
| **Deep Sleep** | 1 раз/сутки | Ранжирует кандидатов по 6 сигналам, promotion | **Да** |
| **REM Sleep** | 1 раз/неделю | Паттерны, рефлексия, усиление сигналов | Нет |

**6 сигналов для scoring:**
```
frequency:     0.24  -- сколько раз вызывалось из памяти
relevance:     0.30  -- средний score при поиске
diversity:     0.15  -- из скольких разных контекстов
recency:       0.15  -- полураспад 14 дней
consolidation: 0.10  -- повторяемость по разным дням
conceptual:    0.06  -- плотность тематических тегов
```

**Порог для promotion в MEMORY.md:** minScore 0.8, минимум 3 recall, минимум 3 уникальных контекста, не старше 30 дней.

### Сравнение подходов

| Аспект | Базовая архитектура (наша) | OpenClaw |
|--------|---------------------------|----------|
| Flush | Cron-based (по времени) | Event-driven (перед компакцией) |
| Promotion | Ручная ротация | Weighted scoring, 6 сигналов |
| Recall tracking | Нет | Каждый search = signal |
| Dreaming | Нет | 3 фазы (light/deep/REM) |
| Сложность | Низкая (bash скрипты) | Высокая (TypeScript + SQLite) |

Базовая архитектура достаточна для начала. Dreaming -- для продвинутых пользователей с высокой нагрузкой.

## FAQ

**Q: Сколько токенов занимает архитектура?**
A: ~15,000-35,000 из 1,000,000 (2-4% окна Opus 4.6). Основной потребитель -- hot/recent.md. Используй `/compact` если HOT вырос.

**Q: Можно без Opus?**
A: Можно на Sonnet, но Opus лучше справляется с длинным контекстом и @includes.

**Q: Зачем два Telegram-бота?**
A: Первый (claude-code-telegram) -- интерактивный, работает как терминал. Второй (jarvis-gateway) -- автономный, с голосовыми, прогрессом, памятью.

**Q: Обязательно ли OpenViking?**
A: Нет. Без него работают 3 из 4 слоёв памяти. [OpenViking](https://github.com/volcengine/OpenViking) добавляет семантический поиск по старым диалогам. Установка: `pip install openviking --upgrade`.

**Q: Мой агент правильно всё установил?**
A: Пройди шаг 10 -- там полный чеклист проверки. Агент проверит каждый файл, hook, cron, и исправит если что-то пропустил.

**Q: CLAUDE.md больше 200 строк -- это нормально?**
A: Нет. Anthropic рекомендует до 200 строк. Больше -- Claude начинает игнорировать инструкции. Выноси reference-материалы в скиллы (SKILLS.md -- как).
