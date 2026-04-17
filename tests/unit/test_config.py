from pathlib import Path

from app.config import ROOT_DIR, get_database_file_path


def test_get_database_file_path_uses_env_override(monkeypatch):
	configured_path = Path("C:/tmp/custom-memories.db")
	monkeypatch.setenv("MEMORIES_DB_FILE", str(configured_path))

	assert get_database_file_path() == configured_path


def test_get_database_file_path_uses_legacy_env_override(monkeypatch):
	configured_path = Path("C:/tmp/legacy-memories.db")
	monkeypatch.delenv("MEMORIES_DB_FILE", raising=False)
	monkeypatch.setenv("MEMORIES_DATA_FILE", str(configured_path))

	assert get_database_file_path() == configured_path


def test_get_database_file_path_uses_default_repo_path(monkeypatch):
	monkeypatch.delenv("MEMORIES_DB_FILE", raising=False)
	monkeypatch.delenv("MEMORIES_DATA_FILE", raising=False)

	assert get_database_file_path() == ROOT_DIR / "data.db"
