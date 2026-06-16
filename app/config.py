import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MCP_BROWSER_CLIENTS_EXAMPLE_FILE = ROOT_DIR / "mcp_browser_clients.example.json"
MCP_BROWSER_CLIENTS_LOCAL_FILE = ROOT_DIR / "mcp_browser_clients.local.json"
DEFAULT_RATE_LIMITING_ENABLED = True
DEFAULT_RATE_LIMIT_READS_PER_MINUTE = 120
DEFAULT_RATE_LIMIT_WRITES_PER_MINUTE = 30
DEFAULT_RATE_LIMIT_BATCH_PER_MINUTE = 10
DEFAULT_RATE_LIMIT_MCP_PER_MINUTE = 240
DEFAULT_REQUEST_BODY_MAX_BYTES = 1_048_576


@dataclass(frozen=True)
class BrowserClientConfig:
	allowed_origins: list[str]
	warnings: list[str]


@dataclass(frozen=True)
class SafetyConfig:
	rate_limiting_enabled: bool
	rate_limit_reads_per_minute: int
	rate_limit_writes_per_minute: int
	rate_limit_batch_per_minute: int
	rate_limit_mcp_per_minute: int
	request_body_max_bytes: int
	warnings: list[str]


def _parse_bool_env(name: str, default: bool, warnings: list[str]) -> bool:
	value = os.getenv(name)
	if value is None:
		return default

	normalized_value = value.strip().lower()
	if normalized_value in {"1", "true", "yes", "on"}:
		return True
	if normalized_value in {"0", "false", "no", "off"}:
		return False

	warnings.append(f"{name} must be a boolean value. Using default {default}.")
	return default


def _parse_positive_int_env(name: str, default: int, warnings: list[str]) -> int:
	value = os.getenv(name)
	if value is None:
		return default

	try:
		parsed_value = int(value)
	except ValueError:
		warnings.append(f"{name} must be a positive integer. Using default {default}.")
		return default

	if parsed_value <= 0:
		warnings.append(f"{name} must be a positive integer. Using default {default}.")
		return default

	return parsed_value


def load_browser_client_config() -> BrowserClientConfig:
	if not MCP_BROWSER_CLIENTS_LOCAL_FILE.exists():
		return BrowserClientConfig(allowed_origins=[], warnings=[])

	warnings: list[str] = []

	try:
		config_data = json.loads(MCP_BROWSER_CLIENTS_LOCAL_FILE.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as exc:
		warnings.append(
			f"Failed to load browser client config from {MCP_BROWSER_CLIENTS_LOCAL_FILE}: {exc}"
		)
		return BrowserClientConfig(allowed_origins=[], warnings=warnings)

	if not isinstance(config_data, dict):
		warnings.append(
			f"Browser client config at {MCP_BROWSER_CLIENTS_LOCAL_FILE} must be a JSON object."
		)
		return BrowserClientConfig(allowed_origins=[], warnings=warnings)

	browser_clients = config_data.get("browser_clients", [])
	if not isinstance(browser_clients, list):
		warnings.append(
			f"Browser client config at {MCP_BROWSER_CLIENTS_LOCAL_FILE} must define browser_clients as a list."
		)
		return BrowserClientConfig(allowed_origins=[], warnings=warnings)

	allowed_origins: list[str] = []
	for index, browser_client in enumerate(browser_clients):
		if not isinstance(browser_client, dict):
			warnings.append(
				f"Ignoring browser_clients[{index}] in {MCP_BROWSER_CLIENTS_LOCAL_FILE} because it is not an object."
			)
			continue

		origin = browser_client.get("origin")
		if not isinstance(origin, str) or not origin:
			warnings.append(
				f"Ignoring browser_clients[{index}] in {MCP_BROWSER_CLIENTS_LOCAL_FILE} because origin is missing or invalid."
			)
			continue

		allowed_origins.append(origin)

	return BrowserClientConfig(allowed_origins=allowed_origins, warnings=warnings)


def load_safety_config() -> SafetyConfig:
	warnings: list[str] = []

	return SafetyConfig(
		rate_limiting_enabled=_parse_bool_env(
			"MEMORIES_RATE_LIMITING_ENABLED",
			DEFAULT_RATE_LIMITING_ENABLED,
			warnings,
		),
		rate_limit_reads_per_minute=_parse_positive_int_env(
			"MEMORIES_RATE_LIMIT_READS_PER_MINUTE",
			DEFAULT_RATE_LIMIT_READS_PER_MINUTE,
			warnings,
		),
		rate_limit_writes_per_minute=_parse_positive_int_env(
			"MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE",
			DEFAULT_RATE_LIMIT_WRITES_PER_MINUTE,
			warnings,
		),
		rate_limit_batch_per_minute=_parse_positive_int_env(
			"MEMORIES_RATE_LIMIT_BATCH_PER_MINUTE",
			DEFAULT_RATE_LIMIT_BATCH_PER_MINUTE,
			warnings,
		),
		rate_limit_mcp_per_minute=_parse_positive_int_env(
			"MEMORIES_RATE_LIMIT_MCP_PER_MINUTE",
			DEFAULT_RATE_LIMIT_MCP_PER_MINUTE,
			warnings,
		),
		request_body_max_bytes=_parse_positive_int_env(
			"MEMORIES_REQUEST_BODY_MAX_BYTES",
			DEFAULT_REQUEST_BODY_MAX_BYTES,
			warnings,
		),
		warnings=warnings,
	)


def get_database_file_path() -> Path:
	configured_path = os.getenv("MEMORIES_DB_FILE")
	if configured_path:
		return Path(configured_path)
	return ROOT_DIR / "data.db"


def get_data_file_path() -> Path:
	return get_database_file_path()
