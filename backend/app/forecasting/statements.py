"""Датасеты для бэктеста из реальных выписок — через тот же конвейер, что импорт в приложении.

Выписка разбирается, категоризируется и сохраняется во временную SQLite-базу в памяти,
затем строится History. Сами операции никуда не записываются и не покидают компьютер.
"""

from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — регистрирует таблицы
from app.db import Base
from app.forecasting.backtest import Dataset
from app.forecasting.data import history_from_db
from app.importers.statement import StatementError
from app.models import ImportJob, Transaction, User
from app.services.categories import ensure_system_categories
from app.services.imports import confirm_import, preview_statement


def dataset_from_statements(name: str, paths: list[Path]) -> Dataset:
    """Одна или несколько выписок одного человека (например, карты разных банков)."""
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        ensure_system_categories(db)
        user = User(email=f"{name}@backtest.local", name=name)
        db.add(user)
        db.commit()
        for path in paths:
            preview = preview_statement(db, user, path.read_bytes(), path.name, None)
            if preview.job_id is None:
                raise StatementError(f"{path.name}: не удалось распознать формат выписки")
            job = db.get(ImportJob, preview.job_id)
            assert job is not None
            confirm_import(db, user, job, None, path.stem)
        last = db.scalar(select(func.max(Transaction.date)).where(Transaction.user_id == user.id))
        if last is None:
            raise StatementError(f"{name}: в выписках нет операций")
        return Dataset(name, history_from_db(db, user, last))
    finally:
        db.close()
        engine.dispose()
