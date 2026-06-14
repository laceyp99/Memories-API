import json
from pathlib import Path

from app.config import (
	DEFAULT_RATE_LIMIT_BATCH_PER_MINUTE,
	DEFAULT_RATE_LIMIT_MCP_PER_MINUTE,
	DEFAULT_RATE_LIMIT_READS_PER_MINUTE,
	DEFAULT_RATE_LIMIT_WRITES_PER_MINUTE,
	DEFAULT_RATE_LIMITING_ENABLED,
	DEFAULT_REQUEST_BODY_MAX_BYTES,
	ROOT_DIR,
	get_database_file_path,
	load_browser_client_config,
	load_safety_config,
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


def test_load_browser_client_config_preserves_valid_origins_when_entries_are_invalid(
	monkeypatch, tmp_path: Path
):
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
						"name": "missing-origin",
					},
				],
			}
		),
		encoding="utf-8",
	)
	monkeypatch.setattr("app.config.MCP_BROWSER_CLIENTS_LOCAL_FILE", config_path)

	config = load_browser_client_config()

	assert config.allowed_origins == ["http://localhost:3000"]
	assert len(config.warnings) == 1
	assert "browser_clients[1]" in config.warnings[0]


def test_load_safety_config_uses_conservative_defaults(monkeypatch):
	monkeypatch.delenv("MEMORIES_RATE_LIMITING_ENABLED", raising=False)
	monkeypatch.delenv("MEMORIES_RATE_LIMIT_READS_PER_MINUTE", raising=False)
	monkeypatch.delenv("MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE", raising=False)
	monkeypatch.delenv("MEMORIES_RATE_LIMIT_BATCH_PER_MINUTE", raising=False)
	monkeypatch.delenv("MEMORIES_RATE_LIMIT_MCP_PER_MINUTE", raising=False)
	monkeypatch.delenv("MEMORIES_REQUEST_BODY_MAX_BYTES", raising=False)

	config = load_safety_config()

	assert config.rate_limiting_enabled is DEFAULT_RATE_LIMITING_ENABLED
	assert config.rate_limit_reads_per_minute == DEFAULT_RATE_LIMIT_READS_PER_MINUTE
	assert config.rate_limit_writes_per_minute == DEFAULT_RATE_LIMIT_WRITES_PER_MINUTE
	assert config.rate_limit_batch_per_minute == DEFAULT_RATE_LIMIT_BATCH_PER_MINUTE
	assert config.rate_limit_mcp_per_minute == DEFAULT_RATE_LIMIT_MCP_PER_MINUTE
	assert config.request_body_max_bytes == DEFAULT_REQUEST_BODY_MAX_BYTES
	assert config.warnings == []


def test_load_safety_config_uses_env_overrides(monkeypatch):
	monkeypatch.setenv("MEMORIES_RATE_LIMITING_ENABLED", "false")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_READS_PER_MINUTE", "5")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE", "6")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_BATCH_PER_MINUTE", "7")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_MCP_PER_MINUTE", "8")
	monkeypatch.setenv("MEMORIES_REQUEST_BODY_MAX_BYTES", "9")

	config = load_safety_config()

	assert config.rate_limiting_enabled is False
	assert config.rate_limit_reads_per_minute == 5
	assert config.rate_limit_writes_per_minute == 6
	assert config.rate_limit_batch_per_minute == 7
	assert config.rate_limit_mcp_per_minute == 8
	assert config.request_body_max_bytes == 9
	assert config.warnings == []


def test_load_safety_config_warns_and_uses_defaults_for_invalid_values(monkeypatch):
	monkeypatch.setenv("MEMORIES_RATE_LIMITING_ENABLED", "maybe")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_READS_PER_MINUTE", "0")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE", "-1")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_BATCH_PER_MINUTE", "ten")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_MCP_PER_MINUTE", "")
	monkeypatch.setenv("MEMORIES_REQUEST_BODY_MAX_BYTES", "0")

	config = load_safety_config()

	assert config.rate_limiting_enabled is DEFAULT_RATE_LIMITING_ENABLED
	assert config.rate_limit_reads_per_minute == DEFAULT_RATE_LIMIT_READS_PER_MINUTE
	assert config.rate_limit_writes_per_minute == DEFAULT_RATE_LIMIT_WRITES_PER_MINUTE
	assert config.rate_limit_batch_per_minute == DEFAULT_RATE_LIMIT_BATCH_PER_MINUTE
	assert config.rate_limit_mcp_per_minute == DEFAULT_RATE_LIMIT_MCP_PER_MINUTE
	assert config.request_body_max_bytes == DEFAULT_REQUEST_BODY_MAX_BYTES
	assert len(config.warnings) == 6
