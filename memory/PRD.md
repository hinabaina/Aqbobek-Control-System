# Aqbobek ACS — Product Requirements Document

## Original problem statement
User provided `da.txt` (AIS Hack 3.0 / Aqbobek school tech spec) and asked to build a beautiful, simple-to-use dashboard connected to the same SQLite database (`school.db`) that the Telegram bot (`whatsappbot.py`) uses. Interface must be in Russian.

## Architecture
- **Backend:** FastAPI + stdlib `sqlite3` on a shared DB file (`/app/data/school.db`)
- **Frontend:** React 19 + Tailwind + Manrope font + Recharts + Lucide icons
- **AI:** Groq REST API (`llama-3.3-70b-versatile` + `whisper-large-v3-turbo`) using the user's own GROQ_API_KEY (same as bot)
- **Auth:** JWT Bearer tokens, bcrypt password hashing, role-based (director / teacher)
- **DB sync with bot:** both services read/write the same `school.db` — no sync job needed

## User personas
- **Director** — sees full dashboard (KPIs, heatmap, kanban, schedule, canteen, employees, AI tools, voice FAB)
- **Teacher / Staff** — sees personal cabinet (own schedule + own tasks pushed by director)

## Implemented modules (MVP — Jan 2026)
- [x] Login (director + teachers)
- [x] Dashboard KPIs + heatmap нагрузки учителей
- [x] Инциденты kanban (синхронно с ботом — подхватывает из `incidents` таблицы)
- [x] Задачи kanban (drag-and-drop, фильтры, создание)
- [x] Сотрудники (CRUD, Telegram-привязки видны)
- [x] Столовая (ввод + сводка + 14-дневный график)
- [x] Расписание (сетка, CRUD, фильтры teacher/class/room, детект конфликтов)
- [x] AI-замена (Smart Substitution — greedy + AI-refinement possible)
- [x] AI-генератор расписания (правила классов + предметов + кабинетов)
- [x] Voice-to-Task (Whisper транскрипция + Llama парсинг + автосоздание задач)
- [x] RAG-приказы (упрощение + генерация)
- [x] Личный кабинет учителя

## Key flows
- Teachers write in Telegram bot → bot writes to `incidents`/`tasks`/`canteen` → dashboard reads immediately
- Director creates task via voice → parsed → assigned to employee by name → teacher sees it in personal cabinet AND gets bot notification (bot does this, not the dashboard)

## Prioritized backlog (P1/P2)
- P1: Drag-and-drop (HTML5) для карточек расписания между слотами с конфликт-детекцией
- P1: "Ленты" (параллельное деление классов по уровням) в генераторе расписания
- P1: Push уведомление в Telegram при создании задачи директором (через bot token)
- P2: Sentiment-анализ чатов (таблица `sentiment_logs` уже есть)
- P2: Excel-экспорт расписания / свода столовой
- P2: WebSocket push обновлений инцидентов

## Sessions log
- **18.04.2026** — MVP build: shared SQLite, auth, all 9 modules, heatmap, kanban, voice-to-task, AI substitution, AI schedule generator, RAG orders, teacher cabinet.
