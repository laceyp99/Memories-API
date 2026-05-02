import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module
import app.mcp_server as mcp_server_module
from app import config as config_module


def build_client_with_browser_config(monkeypatch, tmp_path: Path, browser_clients: list[dict]):
	config_path = tmp_path / "mcp_browser_clients.local.json"
	config_path.write_text(json.dumps({"browser_clients": browser_clients}), encoding="utf-8")
	monkeypatch.setattr(config_module, "MCP_BROWSER_CLIENTS_LOCAL_FILE", config_path)
	importlib.reload(mcp_server_module)
	reloaded_main = importlib.reload(main_module)
	return TestClient(reloaded_main.app)


def build_client_without_browser_config(monkeypatch, tmp_path: Path):
	config_path = tmp_path / "missing_mcp_browser_clients.local.json"
	monkeypatch.setattr(config_module, "MCP_BROWSER_CLIENTS_LOCAL_FILE", config_path)
	importlib.reload(mcp_server_module)
	reloaded_main = importlib.reload(main_module)
	return TestClient(reloaded_main.app)


def test_mcp_http_rejects_browser_requests_when_no_local_allowlist_exists(
	monkeypatch, tmp_path: Path
):
	with build_client_without_browser_config(monkeypatch, tmp_path) as client:
		response = client.post(
			"/mcp",
			headers={"Origin": "http://localhost:3000"},
			json={},
		)

	assert response.status_code == 403
	assert response.json() == {"detail": "Origin not allowed"}


def test_mcp_http_allows_configured_browser_origin(monkeypatch, tmp_path: Path):
	with build_client_with_browser_config(
		monkeypatch,
		tmp_path,
		[{"name": "open-webui-local", "origin": "http://localhost:3000"}],
	) as client:
		response = client.post(
			"/mcp",
			headers={"Origin": "http://localhost:3000"},
			json={},
		)

	assert response.status_code != 403
	assert response.status_code != 404


def test_mcp_http_allows_mcp_request_headers_for_allowed_origin(monkeypatch, tmp_path: Path):
	with build_client_with_browser_config(
		monkeypatch,
		tmp_path,
		[{"name": "open-webui-local", "origin": "http://localhost:3000"}],
	) as client:
		response = client.options(
			"/mcp",
			headers={
				"Origin": "http://localhost:3000",
				"Access-Control-Request-Method": "POST",
				"Access-Control-Request-Headers": "MCP-Protocol-Version,Mcp-Session-Id",
			},
		)

	assert response.status_code == 200
	assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
	assert "MCP-Protocol-Version" in response.headers["access-control-allow-headers"]
	assert "Mcp-Session-Id" in response.headers["access-control-allow-headers"]
