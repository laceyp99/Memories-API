from pathlib import Path

from app.config import ROOT_DIR, get_data_file_path


def test_get_data_file_path_uses_env_override(monkeypatch):
	configured_path = Path("C:/tmp/custom-memories.json")
	monkeypatch.setenv("MEMORIES_DATA_FILE", str(configured_path))

	assert get_data_file_path() == configured_path


def test_get_data_file_path_uses_default_repo_path(monkeypatch):
	monkeypatch.delenv("MEMORIES_DATA_FILE", raising=False)

	assert get_data_file_path() == ROOT_DIR / "data.json"
