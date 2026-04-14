# End-to-End Setup Guide

Полный workflow ученика от нуля до работающего агента. Копируй команды, вставляй -- всё установится.

## Что получишь

- Claude Code агент с настроенной архитектурой памяти (4 слоя)
- 11 базовых скиллов (голос, канбан, git, YouTube, Twitter и др.)
- Superpowers: TDD, дебаг, планирование, code review
- (Опционально) Telegram-бот для работы с агентом
- (Опционально) Vibe Kanban -- визуальная доска задач

## Требования

- VPS (Ubuntu 22.04+) или Mac
- Node.js 18+ (`node --version`)
- Подписка Anthropic Max ($100-200/мес) или API key
- (Опционально) Telegram аккаунт

---

## Шаг 1: Установи Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude
# Внутри: Login with Anthropic -> следуй инструкциям в браузере
# После авторизации: /exit
```

---

## Шаг 2: Выбери модель Opus

```bash
claude
/model opus
```

Opus -- лучшая модель для архитектурных решений и длинного контекста. Sonnet подойдёт для рутинной работы.

---

## Шаг 3: Установи Superpowers

Скопируй этот промпт в Claude Code:

```
Установи плагин Superpowers. Выполни обе команды через Bash:

claude plugins marketplace add obra/superpowers-marketplace
claude plugins install superpowers@superpowers-marketplace

Проверь: claude plugins list
```

Superpowers добавит команды: `/plan`, `/tdd`, `/code-review`, `/brainstorm`, `/debug`, `/verify`.

---

## Шаг 4: Установи GitHub CLI

```
Проверь gh:
gh --version

Если не установлен:
sudo apt install gh   # Ubuntu
brew install gh       # Mac

Авторизуйся:
gh auth login
# GitHub.com -> HTTPS -> Login with a web browser
```

---

## Шаг 5: Разверни архитектуру (ONE-CLICK)

Это главный шаг. Скрипт спросит имя агента, роль, модель, твоё имя -- и создаст всё автоматически.

```bash
git clone https://github.com/qwwiwi/public-architecture-claude-code.git
cd public-architecture-claude-code
bash install.sh
```

### Что спросит install.sh

| Вопрос | Пример ответа | Что делает |
|--------|---------------|------------|
| Agent name | `homer` | Имя workspace: `~/.claude-lab/homer/` |
| Agent role | `Coder, architect` | Записывается в SOUL |
| Primary model | `Claude Opus 4.6` | В AGENTS.md |
| Your name | `Даши` | В USER.md |
| Your timezone | `UTC+3` | В USER.md |
| Language | `Russian` | Язык ответов |

### Что создаёт install.sh

```
~/.claude/
├── CLAUDE.md                    глобальные правила (код, git, безопасность)
└── rules/
    ├── bash.md                  set -euo pipefail, кавычки
    ├── python.md                type hints, pathlib, Google docstrings
    └── typescript.md            strict, no any, Zod

~/.claude-lab/
├── shared/
│   ├── secrets/                 одна папка для всех секретов (chmod 700)
│   └── skills/                  11 базовых скиллов (symlink в каждый агент)
│       ├── groq-voice/          транскрибация голосовых (Groq Whisper)
│       ├── superpowers/         TDD, дебаг, ревью
│       ├── vibe-kanban/         канбан-доска задач
│       ├── datawrapper/          графики и таблицы (Datawrapper API)
│       ├── gws/                 Google Workspace
│       ├── youtube-transcript/  транскрибация YouTube
│       ├── twitter/             чтение твитов
│       ├── quick-reminders/     напоминания
│       ├── markdown-new/        генерация markdown
│       ├── excalidraw/          диаграммы
│       └── perplexity-research/  веб-ресёрч (Perplexity API)
│
└── homer/.claude/               твой агент
    ├── CLAUDE.md                SOUL + @include (identity)
    ├── core/
    │   ├── AGENTS.md            модели, субагенты (on-demand)
    │   ├── USER.md              твой профиль (@include)
    │   ├── rules.md             границы, запреты (@include)
    │   ├── warm/decisions.md    решения, 14 дней (@include)
    │   ├── hot/handoff.md       последние 10 записей (@include)
    │   ├── hot/recent.md        полный журнал (24 часа)
    │   ├── MEMORY.md            архив
    │   └── LEARNINGS.md         уроки из ошибок
    ├── tools/TOOLS.md           серверы, порты, Docker (on-demand)
    ├── skills/ -> shared        скиллы (symlink)
    ├── agents/                  субагенты
    └── scripts/                 cron-скрипты памяти
```

---

## Шаг 6: Проверь тестами

```bash
git clone https://github.com/qwwiwi/architecture-brain-tests.git /tmp/architecture-brain-tests
cd /tmp/architecture-brain-tests
pip install pytest
python3 -m pytest tests/ -v
```

Должно пройти 460 тестов. Они проверяют: все скиллы на месте, шаблоны корректные, секреты не утекли, vibe-kanban прописан везде.

---

## Шаг 7: Заполни identity-файлы

Скопируй этот промпт в Claude Code (запусти из workspace агента):

```
cd ~/.claude-lab/homer/.claude

Помоги заполнить identity-файлы:

1. Открой core/USER.md и заполни:
   - Имя: [твоё имя]
   - Роль: [чем занимаешься -- разработчик, предприниматель, студент]
   - Часовой пояс: [UTC+X]
   - Что нужно от агента: [код, ревью, ресёрч, контент]

2. Открой core/AGENTS.md и настрой:
   - Основная модель: Opus (уже выбрана)
   - Субагенты: максимум 5
   - Команда агентов (если несколько): имена и роли

3. Открой core/rules.md и добавь свои правила:
   - Что агент может делать сам
   - Что требует твоего подтверждения
   - Красные линии (что запрещено)

4. Открой tools/TOOLS.md и добавь:
   - Серверы (IP, SSH)
   - Docker контейнеры
   - Systemd сервисы
   - GitHub аккаунт

5. Открой CLAUDE.md и проверь:
   - Имя и роль агента на месте
   - @include директивы указывают на правильные файлы
   - Стиль ответов соответствует твоим ожиданиям

Покажи результат каждого файла.
```

---

## Шаг 8: Настрой cron для памяти

Скопируй в Claude Code:

```
Настрой cron-скрипты для автоматической ротации памяти.

1. Скопируй скрипты из public-architecture-claude-code/scripts/ в ~/.claude-lab/homer/.claude/scripts/
2. Сделай их исполняемыми: chmod +x scripts/*.sh
3. Добавь в crontab:
   30 4 * * * ~/.claude-lab/homer/.claude/scripts/rotate-warm.sh
   0 5 * * * ~/.claude-lab/homer/.claude/scripts/trim-hot.sh
   0 6 * * * ~/.claude-lab/homer/.claude/scripts/compress-warm.sh
   30 6 * * * ~/.claude-lab/homer/.claude/scripts/ov-session-sync.sh
   0 21 * * * ~/.claude-lab/homer/.claude/scripts/memory-rotate.sh

ВАЖНО: Без этих скриптов hot/recent.md вырастет до 80KB+ за день
и займёт 70% контекстного окна. Cron -- обязательно.

Покажи: crontab -l | grep -E "trim|rotate|compress|ov-session"
```

---

## Шаг 9: Запусти Vibe Kanban (канбан-доска)

```bash
# Запусти доску (откроется в браузере)
npx vibe-kanban

# Агенты подключаются автоматически через MCP (уже настроен в settings.json)
```

Ты видишь задачи в браузере (drag & drop). Агенты видят задачи через MCP tools (`list_workspaces`, `create_session`). Данные локальные (SQLite), без облака.

---

## Шаг 10: Подключи Telegram (опционально)

### Вариант A: Интерактивный (быстрый старт)

```
Установи Telegram-плагин для Claude Code:
https://github.com/RichardAtCT/claude-code-telegram

1. Создай бота через @BotFather в Telegram
2. Установи: uv tool install claude-code-telegram
3. Настрой переменные:
   export CLAUDE_CODE_TELEGRAM_BOT_TOKEN="токен-от-BotFather"
   export CLAUDE_CODE_TELEGRAM_ALLOWED_USERS="твой-user-id"
   export CLAUDE_CODE_TELEGRAM_WORKDIR="$HOME/.claude-lab/homer/.claude"
4. Запусти: claude-code-telegram
```

### Вариант B: Автономный (gateway, голосовые, память)

```
Разверни Telegram Gateway:
https://github.com/qwwiwi/jarvis-telegram-gateway

1. git clone репозиторий
2. cp config.example.json config.json
3. Создай бота через @BotFather
4. Заполни config.json (токен, user ID, workspace)
5. Получи Groq API key: https://console.groq.com (для голосовых)
6. Запусти: python3 gateway.py
```

---

## Шаг 11: Первый разговор с агентом

Скопируй этот промпт -- он «активирует» агента:

```
Прочитай все файлы в своём workspace (~/.claude-lab/homer/.claude/):
- CLAUDE.md (твой SOUL)
- core/AGENTS.md (модели, субагенты)
- core/USER.md (мой профиль)
- core/rules.md (границы)
- tools/TOOLS.md (инфраструктура)

Теперь:
1. Расскажи кто ты (из SOUL)
2. Расскажи кто я (из USER.md)
3. Покажи свои навыки: какие скиллы тебе доступны (ls skills/)
4. Покажи какие команды Superpowers ты знаешь
5. Проверь что vibe-kanban доступен через MCP
6. Запиши в core/hot/recent.md свою первую запись:
   ### [текущая дата] [own_text]
   **Оператор:** Первый запуск агента
   **Агент:** [краткое описание себя и готовности]

Если чего-то не хватает -- скажи что нужно доустановить.
```

---

## Шаг 12: Финальная проверка

Скопируй в Claude Code:

```
Проверь что всё работает. Пройди по каждому пункту:

1. tree ~/.claude-lab/ -L 4 -- структура на месте?
2. cat ~/.claude-lab/homer/.claude/CLAUDE.md -- @include на месте?
3. ls ~/.claude-lab/shared/skills/ -- 11 скиллов?
4. cat ~/.claude/CLAUDE.md -- глобальные правила?
5. cat ~/.claude/rules/*.md -- языковые конвенции?
6. crontab -l | grep -E "trim|rotate|compress|ov-session" -- 5 cron-задач?
7. claude plugins list -- Superpowers установлен?
8. gh auth status -- GitHub авторизован?
9. npx vibe-kanban --help -- Vibe Kanban доступен?
10. (Если Telegram) отправь тестовое сообщение боту

Для каждого пункта покажи результат. Если что-то не настроено -- исправь.
```

---

## Что дальше

| Шаг | Что делать | Документация |
|-----|-----------|--------------|
| Добавить агента | `bash install.sh` (повтори для каждого агента) | [MULTI-AGENT.md](MULTI-AGENT.md) |
| Написать свой скилл | `/skill-creator` или вручную | [SKILLS.md](SKILLS.md) |
| Настроить субагентов | Создать `agents/*.md` | [SUBAGENTS.md](SUBAGENTS.md) |
| Hooks безопасности | `settings.json` + `hooks/*.sh` | [HOOKS.md](HOOKS.md) |
| OpenViking (L4 memory) | `pip install openviking` | [MEMORY.md](MEMORY.md) |
| Оптимизация токенов | Контроль размера контекста | [TOKEN-OPTIMIZATION.md](TOKEN-OPTIMIZATION.md) |

## FAQ

**Q: Сколько токенов занимает архитектура?**
A: ~10,000-25,000 токенов (~3-6% от 400К рабочего окна). Базовое окно 1М, но мы ставим CLAUDE_CODE_AUTO_COMPACT_WINDOW=400000 для лучшего качества. CLAUDE.md загружает 4 файла через @include (USER.md, rules.md, decisions.md, handoff.md). AGENTS.md и TOOLS.md загружаются по запросу через Read tool, что экономит ~18KB. Cron скрипты держат hot/recent.md в пределах 10-20 KB.

**Q: Можно без Opus?**
A: Можно на Sonnet, но Opus лучше справляется с длинным контекстом и @includes.

**Q: Зачем 4 cron-скрипта?**
A: Без них hot/recent.md вырастает до 80+ KB за день и занимает 70% стартового контекста. Агент начинает игнорировать инструкции. Cron -- обязательно.

**Q: Обязательно ли OpenViking?**
A: Нет. Без него работают 3 из 4 слоёв памяти. [OpenViking](https://github.com/volcengine/OpenViking) добавляет семантический поиск по старым диалогам.

**Q: Обязательно ли Telegram?**
A: Нет. Claude Code работает из терминала. Telegram -- удобство (голосовые, мобильный доступ).

**Q: Сколько стоит?**
A: Anthropic Max $100-200/мес. Всё остальное (архитектура, скиллы, канбан, gateway) -- бесплатное open-source.
