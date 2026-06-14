from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database

from app import main as app_main
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


def test_post_memory_rejects_oversized_body_before_json_parsing(monkeypatch, data_file: Path):
	monkeypatch.setenv("MEMORIES_REQUEST_BODY_MAX_BYTES", "10")
	test_client = TestClient(app_main.create_app())

	response = test_client.post(
		"/memories",
		content="x" * 11,
		headers={"Content-Type": "application/json"},
	)

	assert response.status_code == 413
	assert response.json() == {"detail": "Request body too large"}
	assert response.headers["X-Request-Body-Limit"] == "10"
	assert read_database(data_file) == []


def test_patch_memory_rejects_oversized_body_before_json_parsing(monkeypatch, data_file: Path):
	monkeypatch.setenv("MEMORIES_REQUEST_BODY_MAX_BYTES", "10")
	test_client = TestClient(app_main.create_app())

	response = test_client.patch(
		"/memories/1",
		content="x" * 11,
		headers={"Content-Type": "application/json"},
	)

	assert response.status_code == 413
	assert response.json() == {"detail": "Request body too large"}
	assert response.headers["X-Request-Body-Limit"] == "10"
	assert read_database(data_file) == []


def test_missing_memory_returns_documented_404_shape(client: TestClient, data_file: Path):
	response = client.get("/memories/999")

	assert response.status_code == 404
	assert response.json() == {"detail": "Memory not found"}
	assert read_database(data_file) == []


def test_patch_memory_conflict_returns_documented_409_shape(
	client: TestClient, data_file: Path, monkeypatch
):
	def raise_conflict(_memory_id, _memory):
		raise storage.MemoryWriteConflictError("stale write")

	monkeypatch.setattr(app_main, "update_memory", raise_conflict)

	response = client.patch("/memories/1", json={"content": "Updated content"})

	assert response.status_code == 409
	assert response.json() == {"detail": "Memory was modified by another request"}
	assert read_database(data_file) == []


def test_delete_memory_conflict_returns_documented_409_shape(
	client: TestClient, data_file: Path, monkeypatch
):
	def raise_conflict(_memory_id):
		raise storage.MemoryWriteConflictError("stale write")

	monkeypatch.setattr(app_main, "delete_memory", raise_conflict)

	response = client.delete("/memories/1")

	assert response.status_code == 409
	assert response.json() == {"detail": "Memory was modified by another request"}
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


def test_get_memories_response_matches_public_contract(
	client: TestClient, data_file: Path, monkeypatch
):
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:20:00.000000Z",
		]
	)
	monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

	post_response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)
	assert post_response.status_code == 200

	response = client.get("/memories")
	body = response.json()

	assert response.status_code == 200
	assert isinstance(body, dict)
	assert set(body) == {"items", "total", "limit", "offset", "has_more"}
	assert body["total"] == 1
	assert body["offset"] == 0
	assert body["has_more"] is False
	assert isinstance(body["limit"], int)
	assert len(body["items"]) == 1
	assert set(body["items"][0]) == {
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
	assert body["items"][0]["created_at"].endswith("Z")
	assert body["items"][0]["updated_at"].endswith("Z")
	assert body["items"][0]["last_accessed_at"].endswith("Z")
	assert read_database(data_file) == body["items"]
