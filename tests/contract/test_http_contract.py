from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database

from app import storage


def test_post_memory_response_matches_public_contract(
	client: TestClient, data_file: Path, monkeypatch
):
	timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

	response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)

	body = response.json()

	assert response.status_code == 200
	assert set(body) == {
		"id",
		"content",
		"tags",
		"created_at",
		"updated_at",
		"last_accessed_at",
		"memory_type",
		"status",
		"version",
	}
	assert body["created_at"].endswith("Z")
	assert body["updated_at"].endswith("Z")
	assert body["last_accessed_at"] is None
	assert read_database(data_file) == [body]


def test_missing_memory_returns_documented_404_shape(client: TestClient, data_file: Path):
	response = client.get("/memories/999")

	assert response.status_code == 404
	assert response.json() == {"detail": "Memory not found"}
	assert read_database(data_file) == []


def test_non_integer_memory_id_returns_validation_error_shape(client: TestClient, data_file: Path):
	response = client.get("/memories/abc")

	body = response.json()

	assert response.status_code == 422
	assert "detail" in body
	assert any(
		error["loc"] == ["path", "memory_id"] and error["type"] == "int_parsing"
		for error in body["detail"]
	)
	assert read_database(data_file) == []
