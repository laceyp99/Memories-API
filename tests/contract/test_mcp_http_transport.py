import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module
import app.mcp_server as mcp_server_module
from app import config as config_module


def build_client_with_fresh_mcp():
	importlib.reload(mcp_server_module)
	reloaded_main = importlib.reload(main_module)
	return TestClient(reloaded_main.app)


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
	expose_headers = response.headers["access-control-expose-headers"]
	assert "X-RateLimit-Limit" in expose_headers
	assert "X-Request-Body-Limit" in expose_headers


def test_mcp_http_rejects_oversized_body_before_transport_parsing(monkeypatch):
	monkeypatch.setenv("MEMORIES_REQUEST_BODY_MAX_BYTES", "10")
	client = TestClient(main_module.create_app())

	response = client.post(
		"/mcp",
		content="x" * 11,
		headers={"Content-Type": "application/json"},
	)

	assert response.status_code == 413
	assert response.json() == {"detail": "Request body too large"}
	assert response.headers["X-Request-Body-Limit"] == "10"


def test_mcp_http_rate_limit_returns_stable_429(monkeypatch):
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_MCP_PER_MINUTE", "1")

	with build_client_with_fresh_mcp() as client:
		first_response = client.post("/mcp/", json={})
		second_response = client.post("/mcp/", json={})

	assert first_response.status_code != 429
	assert second_response.status_code == 429
	assert second_response.json() == {"detail": "Rate limit exceeded"}
	assert second_response.headers["Retry-After"].isdigit()
	assert second_response.headers["X-RateLimit-Limit"] == "1"
	assert second_response.headers["X-RateLimit-Remaining"] == "0"
	assert second_response.headers["X-RateLimit-Reset"].isdigit()


def test_mcp_http_allows_valid_origin_when_another_browser_client_is_invalid(
	monkeypatch, tmp_path: Path
):
	with build_client_with_browser_config(
		monkeypatch,
		tmp_path,
		[
			{"name": "open-webui-local", "origin": "http://localhost:3000"},
			{"name": "missing-origin"},
		],
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
				"Access-Control-Request-Headers": "MCP-Protocol-Version,Mcp-Session-Id,X-Client-Id",
			},
		)

	assert response.status_code == 200
	assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
	assert "MCP-Protocol-Version" in response.headers["access-control-allow-headers"]
	assert "Mcp-Session-Id" in response.headers["access-control-allow-headers"]
	assert "X-Client-Id" in response.headers["access-control-allow-headers"]
