from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def data_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    file_path = tmp_path / "data.json"
    file_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("MEMORIES_DATA_FILE", str(file_path))
    return file_path
