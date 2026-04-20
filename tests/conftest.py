from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
	return TestClient(app)


@pytest.fixture(autouse=True)
def data_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
	file_path = tmp_path / "data.db"
	monkeypatch.setenv("MEMORIES_DB_FILE", str(file_path))
	return file_path
