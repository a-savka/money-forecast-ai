# MoneyForecast AI

ИИ-прогнозирование расходов, которое заранее предупреждает о кассовых разрывах.
Учебный проект по дисциплине «Стартап-экосистемы».

Команда: Савка Андрей, Баранов Кирилл, Хрисфанова Виктория, Максименко Алексей.

## Структура

| Папка | Что внутри |
|---|---|
| `backend/` | API на FastAPI: операции, импорт, категоризация, прогнозный движок, LLM-слой, моки |
| `frontend/` | React-приложение (web) + Capacitor-проект для Android |
| `docs/` | План MVP и материалы |

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

- Web-приложение: http://localhost:5173
- API и Swagger: http://localhost:8000/docs

Демо-данные загружаются автоматически при входе под демо-профилем.

## Разработка без Docker

```bash
# backend
cd backend
uv sync
DATABASE_URL=sqlite:///./dev.db uv run alembic upgrade head
DATABASE_URL=sqlite:///./dev.db uv run uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

## Мобильное приложение (Android)

Нужны JDK 21 и Android SDK (путь в `frontend/android/local.properties`: `sdk.dir=...`).

```bash
cd frontend
npm run android:build
# APK: frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

Телефон и компьютер должны быть в одной сети. Адрес API (`http://<IP-компьютера>:8000`)
задаётся на экране входа → «Настройки сервера»; пересобирать APK не нужно.

Подробный план и статус задач — `docs/MVP_PLAN.md`.
