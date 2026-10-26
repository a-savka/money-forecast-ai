import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db import Base, get_db
from app.main import create_app
from app.services.categories import ensure_system_categories


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    ensure_system_categories(session)
    yield session
    session.close()


@pytest.fixture
def client(db):
    test_app = create_app(seed_on_startup=False)
    test_app.dependency_overrides[get_db] = lambda: db
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
def auth(client):
    """Заголовки авторизации пользователя с демо-профилем young."""
    token = client.post("/auth/demo-login", json={"profile": "young"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
