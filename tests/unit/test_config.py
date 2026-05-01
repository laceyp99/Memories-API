import json
from pathlib import Path

from app.config import (
	ROOT_DIR,
	get_database_file_path,
	load_browser_client_config,
)


def test_get_database_file_path_uses_env_override(monkeypatch):
	configured_path = Path("C:/tmp/custom-memories.db")
	monkeypatch.setenv("MEMORIES_DB_FILE", str(configured_path))

	assert get_database_file_path() == configured_path


def test_get_database_file_path_uses_default_repo_path(monkeypatch):
	monkeypatch.delenv("MEMORIES_DB_FILE", raising=False)

	assert get_database_file_path() == ROOT_DIR / "data.db"


def test_load_browser_client_config_denies_browser_access_when_local_file_is_missing(
	monkeypatch, tmp_path: Path
):
	missing_config_path = tmp_path / "mcp_browser_clients.local.json"
	monkeypatch.setattr("app.config.MCP_BROWSER_CLIENTS_LOCAL_FILE", missing_config_path)

	config = load_browser_client_config()

	assert config.allowed_origins == []
	assert config.warnings == []


def test_load_browser_client_config_warns_and_denies_when_json_is_invalid(
	monkeypatch, tmp_path: Path
):
	config_path = tmp_path / "mcp_browser_clients.local.json"
	config_path.write_text("{invalid json", encoding="utf-8")
	monkeypatch.setattr("app.config.MCP_BROWSER_CLIENTS_LOCAL_FILE", config_path)

	config = load_browser_client_config()

	assert config.allowed_origins == []
	assert len(config.warnings) == 1
	assert str(config_path) in config.warnings[0]


def test_load_browser_client_config_returns_exact_allowed_origins(monkeypatch, tmp_path: Path):
	config_path = tmp_path / "mcp_browser_clients.local.json"
	config_path.write_text(
		json.dumps(
			{
				"browser_clients": [
					{
						"name": "open-webui-local",
						"origin": "http://localhost:3000",
					},
					{
						"name": "other-local-app",
						"origin": "http://127.0.0.1:8080",
					},
				],
			}
		),
		encoding="utf-8",
	)
	monkeypatch.setattr("app.config.MCP_BROWSER_CLIENTS_LOCAL_FILE", config_path)

	config = load_browser_client_config()

	assert config.allowed_origins == ["http://localhost:3000", "http://127.0.0.1:8080"]
	assert config.warnings == []
