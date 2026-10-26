# MoneyForecast AI — правила для ИИ-агента

Учебный проект (дисциплина «Стартап-экосистемы»): приложение учёта расходов с ИИ-прогнозом
трат и предупреждением о кассовых разрывах. Полный план MVP: `docs/MVP_PLAN.md`
(раздел 12 — задачи с ID вида `W1-3`).

## Стек
- `backend/` — Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, uv.
- `frontend/` — React + TypeScript (Vite), Tailwind, TanStack Query, Zustand, Recharts, Capacitor (Android).
- Всё поднимается через `docker compose up --build`.

## Команды
```bash
docker compose up --build                     # db + api (:8000, /docs) + web (:5173)
cd backend && uv run pytest                   # тесты backend (SQLite in-memory)
docker compose exec api python -m scripts.train_ml_gbm   # обучить ML-модель H3 (~30 с; иначе обучится облегчённая при первом запросе)
cd backend && uv run python -m scripts.run_backtest   # бэктест H0–H3 → docs/backtest/report.md
cd backend && uv run ruff check . && uv run ruff format --check .
cd frontend && npm run lint && npm run typecheck && npm test
cd frontend && npm run gen:api                # TS-типы из OpenAPI (API должен быть запущен)
cd frontend && npm run android:build          # debug APK
```

## Правила
- Одна задача плана = один или несколько коммитов в формате Conventional Commits
  с ID задачи: `feat(backend): CRUD операций [W1-6]`.
- Все API принимают/возвращают Pydantic-схемы из `app/schemas`.
- Все вызовы LLM — только через `app/llm` (`LLMProvider`); по умолчанию `LLM_PROVIDER=mock`, тесты не ходят в сеть.
- Новые способы прогноза — только как реализация `ForecastStrategy` в `app/forecasting/strategies`.
- Моки помечаются комментарием `# MOCK` / `// MOCK` и описанием, что будет в реальной версии.
- Деньги — `Decimal` в backend, `number` (рубли) в API; расходы отрицательные, доходы положительные.
- Бизнес-логика backend покрывается pytest. Не коммитить `.env` и реальные выписки (`data/private/`).
- Тексты интерфейса — на русском.
