# End-to-End Setup Guide

Пошаговая инструкция. Копируй промпты, вставляй в Claude Code -- всё установится автоматически.

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

Конкретно:
1. Прочитай все файлы в репозитории (ARCHITECTURE.md, STRUCTURE.md, MEMORY.md, CHECKLIST.md, все examples/)
2. Создай структуру директорий по STRUCTURE.md
3. Создай все identity-файлы по шаблонам из examples/
4. Настрой глобальный ~/.claude/CLAUDE.md (добавь правила если не хватает)
5. Создай workspace для основного агента (claude-code)
6. В CLAUDE.md агента добавь @include для всех core-файлов
7. Создай пустые файлы памяти (hot/recent.md, warm/decisions.md, MEMORY.md)

Имя агента: claude-code
Workspace: ~/.claude-lab/claude-code/.claude/

После создания покажи дерево файлов и содержимое каждого созданного файла.
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
Проверь что архитектура работает:

1. Покажи дерево ~/.claude-lab/
2. Покажи содержимое CLAUDE.md агента (с @include)
3. Проверь что hot/recent.md, warm/decisions.md существуют
4. Проверь что Superpowers установлен: claude plugins list
5. Проверь что gh авторизован: gh auth status
6. Отправь тестовое сообщение в Telegram-бот
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
│   │   └── MEMORY.md            архив
│   ├── tools/TOOLS.md           серверы
│   └── skills/                  скиллы агента
│
└── jarvis/.claude/              автономный агент (если шаг 9)
    └── (та же структура)
```

## FAQ

**Q: Сколько токенов занимает архитектура?**
A: ~15,000-35,000 из 200,000 (8-18% окна Opus). Основной потребитель -- hot/recent.md.

**Q: Можно без Opus?**
A: Можно на Sonnet, но Opus лучше справляется с длинным контекстом и @includes.

**Q: Зачем два Telegram-бота?**
A: Первый (claude-code-telegram) -- интерактивный, работает как терминал. Второй (jarvis-gateway) -- автономный, с голосовыми, прогрессом, памятью.

**Q: Обязательно ли OpenViking?**
A: Нет. Без него работают 3 из 4 слоёв памяти. [OpenViking](https://github.com/volcengine/OpenViking) добавляет семантический поиск по старым диалогам. Установка: `pip install openviking --upgrade`.
