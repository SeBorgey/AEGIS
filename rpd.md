# RPD — AEGIS (Autonomous Engineering and Generation Intelligence System)

## Назначение проекта

AEGIS — автономная мультиагентная система, которая по текстовому ТЗ (техническому заданию) генерирует готовое Python GUI-приложение на PySide6. Полный цикл: анализ требований → планирование → генерация кода → тестирование → упаковка в исполняемый файл → оценка качества.

## Стек технологий

| Компонент | Технология |
|---|---|
| Язык | Python 3.11+ |
| GUI генерируемых приложений | PySide6 |
| LLM | Gemini 3 Flash Preview (через OpenAI-совместимый API) |
| Веб-интерфейс | FastAPI + Uvicorn + статический HTML/JS |
| Упаковка | PyInstaller (onefile) |
| GUI-тестирование | pyautogui + pyatspi (AT-SPI accessibility) |
| Виртуальный дисплей | pyvirtualdisplay + Xvfb + fluxbox |
| Модели данных | Pydantic |

## Архитектура (мультиагентная система)

```
Пользователь (ТЗ)
        │
        ▼
  ManagerAgent (планировщик)
        │
        ├── создаёт RPD и чеклист
        ├── вызывает run_coder → CoderAgent
        ├── ревьюит код (open_file, get_all_symbols)
        ├── отправляет фидбэк кодеру
        └── вызывает finish_work → PyInstaller → exe
                │
                ▼
        JudgeAgent (тестировщик)
                │
                ├── запускает exe в виртуальном дисплее
                ├── делает скриншоты
                ├── кликает по виджетам (AT-SPI)
                └── выставляет оценку 1-10
```

### Агенты

#### ManagerAgent (`manager_agent.py`)
- **Роль**: Менеджер проекта. Получает ТЗ, создаёт RPD, управляет кодером.
- **Паттерн**: ReAct (Thought → Action → Observation).
- **Формат ответов LLM**: JSON в блоке ` ```json `.
- **Доступные экшены**: `run_coder`, `finish_work`, `get_project_tree`, `get_all_symbols`, `open_file`, `terminal_command`.
- **Лимит итераций**: 300 (по умолчанию в `main.py`).
- **Процесс**: анализ запроса → RPD → чеклист → вызов кодера → ревью кода → фикс → `finish_work` (сборка PyInstaller).

#### CoderAgent (ReActAgent) (`react_agent.py`)
- **Роль**: Программист. Пишет код Python/PySide6.
- **Паттерн**: ReAct.
- **Доступные экшены**: `read_file`, `create_file`, `edit_file`, `get_file_tree`, `run_command`, `run_ipython`, `finish_task`.
- **Лимит итераций**: 500 (по умолчанию в `main.py`).
- **Главный файл**: всегда `app.py`.
- **Тестирование**: при `finish_task` запускается `app.py` через `CodeExecutor.test_app()` — если приложение работает 3 секунды без крашей, тест пройден. Если нет — ошибка передаётся обратно, кодер исправляет.

#### JudgeAgent (`judge_agent.py`)
- **Роль**: QA-тестировщик. Запускает собранный exe, взаимодействует с GUI, оценивает.
- **Паттерн**: ReAct (мультимодальный — получает скриншоты).
- **Доступные экшены**: `start`, `click`, `type_text`, `run_command`, `finish`.
- **Результат**: оценка (1-10) + комментарий → сохраняется в `runs/judge_results.csv`.
- **Поиск exe**: `{run_path}/code/dist/app`.
- **Запускается отдельно**: через `run_judge.py` / `judge.sh`.

## Модули (описание файлов)

### Точки входа

| Файл | Назначение |
|---|---|
| `main.py` | CLI-точка входа. Читает задачи из JSON-датасета или использует хардкод-задачу. Собирает пайплайн: LLMClient → Coder → Manager → запуск. |
| `run_judge.py` | Запуск JudgeAgent для всех ранов в `runs/`, у которых есть `code/dist/app`. |
| `web_interface/server.py` | FastAPI-сервер (порт 8000). Принимает ТЗ через POST `/api/start`, запускает генерацию в фоне, отдаёт статус/логи/скачивание. |

### Shell-скрипты (все устанавливают `OPENAI_API_KEY`)

| Скрипт | Команда |
|---|---|
| `run.sh` | `python -u main.py 2>&1 \| tee output.log` |
| `judge.sh` | `python -u run_judge.py 2>&1 \| tee output.log` |
| `web_interface.sh` | `python web_interface/server.py` |

### Ядро системы

| Файл | Класс/Функция | Назначение |
|---|---|---|
| `llm_client.py` | `LLMClient` | Обёртка над OpenAI SDK. base_url = Gemini API. Модель: `gemini-3-flash-preview`. Retry 3 раза при пустом ответе или API-ошибке. |
| `react_agent.py` | `ReActAgent` | Базовый ReAct-агент (используется как Coder). Цикл: prompt → LLM → parse JSON → execute action → observation. |
| `manager_agent.py` | `ManagerAgent` | Менеджер-агент. Похожий цикл, но с другим набором экшенов. |
| `judge_agent.py` | `JudgeAgent` | Судья-агент. Мультимодальный (скриншоты в base64). |
| `code_executor.py` | `CodeExecutor` | `test_app()` — запуск `app.py` в offscreen-режиме Qt, проверка 3 сек. `package_to_exe()` — PyInstaller. |
| `app_tester.py` | `AppTester` | GUI-тестер для судьи. Запускает exe в виртуальном дисплее (Xvfb + fluxbox). Скриншоты через pyautogui. Клики по виджетам через AT-SPI (pyatspi). |
| `log_manager.py` | `LogManager` | Управление логами. Создаёт директорию рана `runs/run_{timestamp}_{pid}/`. Подкаталоги: `logs/` (program.log, chat.md, metadata.json) и `code/` (рабочая директория кодера). Авто-очистка старых ранов. |

### Пакет `action_api/`

Инфраструктура экшенов для агентов.

| Файл | Назначение |
|---|---|
| `models.py` | `ActionCall` (name + params) и `ActionResult` (success, data, error, logs, duration_ms). Pydantic-модели. |
| `policy.py` | `PolicyConfig` — конфиг ограничений (root_dir, allowed_commands, timeout, max_bytes). `ActionPolicy` — валидация: резолв путей (не выйти за root_dir), проверка параметров. |
| `executor.py` | `ActionExecutor` — принимает `ActionCall`, проверяет через policy, вызывает функцию из registry, возвращает `ActionResult`. |
| `registry.py` | `build_registry()` — реестр экшенов кодера. `build_manager_registry()` — реестр экшенов менеджера (включая `run_coder` и `finish_work`). |
| `actions/file.py` | `read_file`, `create_file`, `edit_file`, `get_file_tree` — файловые операции. |
| `actions/terminal.py` | `run_command` — выполнение shell-команд через subprocess. |
| `actions/python.py` | `run_ipython` — выполнение Python-кода через `exec()` с сохранением состояния (глобальные переменные). |
| `actions/control.py` | `finish_task` — заглушка, возвращает `{status: "finished"}`. |
| `actions/manager.py` | `run_coder` — делегирует задачу CoderAgent. `finish_work` — вызывает PyInstaller. `get_all_symbols` — парсит AST файла. `open_file` — чтение файла с нумерацией строк. |

### Веб-интерфейс (`web_interface/`)

| Файл | Назначение |
|---|---|
| `server.py` | FastAPI-приложение. Эндпоинты: `POST /api/start`, `GET /api/status/{run_id}`, `GET /api/download_app/{run_id}`, `GET /api/download_code/{run_id}`, `GET /`. |
| `static/` | HTML/CSS/JS фронтенд. |

### Датасеты (`datasets/`)

JSON-массивы с текстовыми описаниями задач разной сложности:
- `easy.json` — 16 простых задач (калькулятор, таймер, тетрис, змейка и т.д.)
- `middle.json` — 20 задач средней сложности (markdown-редактор, шахматы с ИИ, торрент-клиент и т.д.)
- `hard.json` — сложные задачи

### Вспомогательное

| Путь | Назначение |
|---|---|
| `dataset_collector/` | Утилиты для сбора датасетов: `collector.py`, `parser.py`, `selector.py`, `embeddings.py`, `models.py`. |
| `genered_datasets/` | Сгенерированные датасеты: `coder_dataset.json` (~553KB), `manager_dataset.json` (~165KB). |
| `notes/` | Заметки и отчёты: `draft.md`, `идеи.md`, `easy_report/`, `middle_report/`. |
| `gradebook.db` | SQLite-база (возможно, для хранения результатов). |
| `draft.md` | Черновик/заметки (~16KB). |
| `runs/` | Директория с результатами запусков (gitignored). |

## Структура директории рана (`runs/run_{timestamp}_{pid}/`)

```
run_YYYYMMDD_HHMMSS_PID/
├── logs/
│   ├── program.log          # Лог работы программы
│   ├── program_judge.log    # Лог работы судьи (если запущен)
│   ├── manager_chat.md      # Переписка менеджера с LLM
│   ├── coder_chat.md        # Переписка кодера с LLM
│   ├── judge_chat.md        # Переписка судьи с LLM
│   ├── metadata.json        # {original_task: "..."}
│   └── *.png                # Скриншоты от судьи
└── code/
    ├── app.py               # Главный файл приложения
    ├── *.py                  # Другие файлы проекта
    └── dist/
        └── app              # Собранный исполняемый файл
```

## Поток выполнения (основной сценарий)

1. Пользователь вводит ТЗ (через CLI `main.py` или веб-интерфейс).
2. `LogManager` создаёт директорию рана `runs/run_*`.
3. Создаются `PolicyConfig`, `ActionPolicy`, реестры экшенов.
4. `LLMClient` инициализируется с API-ключом Gemini.
5. `CoderAgent` (ReActAgent) создаётся с набором файловых/терминальных экшенов.
6. `ManagerAgent` создаётся с набором менеджерских экшенов (включая `run_coder`).
7. `ManagerAgent.run(task)` запускает цикл:
   - LLM генерирует RPD, отправляет его кодеру через `run_coder`.
   - `CoderAgent.run(instruction)` пишет код, тестирует через `finish_task`.
   - Менеджер ревьюит код (`get_all_symbols`, `open_file`), может вызвать кодера снова.
   - `finish_work` запускает PyInstaller → `code/dist/app`.
8. (Отдельно) `run_judge.py` запускает `JudgeAgent` для оценки готового приложения.

## Ключевые переменные среды

| Переменная | Назначение |
|---|---|
| `OPENAI_API_KEY` | API-ключ для Gemini (обязательно) |
| `QT_QPA_PLATFORM=offscreen` | Используется в `CodeExecutor.test_app()` для headless-тестирования |
| `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1` | Включает AT-SPI для `AppTester` |

## Команды запуска

```bash
# Генерация приложения (CLI)
./run.sh

# Оценка готовых приложений судьёй
./judge.sh

# Веб-интерфейс (http://localhost:8000)
./web_interface.sh
```

## Ограничения и особенности

- Все пути ограничены `root_dir` (sandbox) через `ActionPolicy`.
- `run_ipython` сохраняет состояние между вызовами (глобальные переменные).
- Тест приложения: если `app.py` работает 3 секунды без крашей — тест пройден.
- При пустом ответе LLM — до 3 ретраев с задержкой 5 секунд.
- Логи автоматически очищаются через `retention_days` (по умолчанию 7 дней).
- Менеджер специально инструктирован не разбивать проект на фазы, а разрабатывать всё за один вызов кодера.
