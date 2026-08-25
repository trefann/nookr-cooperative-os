"""Test fixtures.

Every test runs against a throwaway SQLite database seeded with the real seed
script, so the tests exercise the same data the demo does.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# Point the app at a scratch database *before* anything imports app.core.config,
# whose settings object is cached at import time.
_TEST_DB = Path(tempfile.gettempdir()) / "nookr_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret-not-used-anywhere-real"
os.environ["AI_API_KEY"] = ""
os.environ["DEMO_PASSWORD"] = "demo1234"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.seed import reset_database, seed_all  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_database() -> Iterator[None]:
    if _TEST_DB.exists():
        _TEST_DB.unlink()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        reset_database(db)
        seed_all(db, quiet=True)
    yield
    engine.dispose()
    if _TEST_DB.exists():
        _TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def _demo_token(client: TestClient, role: str) -> str:
    response = client.post("/api/auth/demo-login", json={"role": role})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def customer_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_demo_token(client, 'CUSTOMER')}"}


@pytest.fixture
def worker_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_demo_token(client, 'WORKER')}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_demo_token(client, 'ADMIN')}"}
