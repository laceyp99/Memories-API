import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MCP_BROWSER_CLIENTS_EXAMPLE_FILE = ROOT_DIR / "mcp_browser_clients.example.json"
MCP_BROWSER_CLIENTS_LOCAL_FILE = ROOT_DIR / "mcp_browser_clients.local.json"


@dataclass(frozen=True)
class BrowserClientConfig:
	allowed_origins: list[str]
	warnings: list[str]


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

	if warnings:
		return BrowserClientConfig(allowed_origins=[], warnings=warnings)

	return BrowserClientConfig(allowed_origins=allowed_origins, warnings=[])


def get_database_file_path() -> Path:
	configured_path = os.getenv("MEMORIES_DB_FILE")
	if configured_path:
		return Path(configured_path)
	return ROOT_DIR / "data.db"


def get_data_file_path() -> Path:
	return get_database_file_path()
