import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database

from app import main as app_main
from app import storage


def assert_rate_limited(response, limit: int):
	assert response.status_code == 429
	assert response.json() == {"detail": "Rate limit exceeded"}
	assert response.headers["Retry-After"].isdigit()
	assert response.headers["X-RateLimit-Limit"] == str(limit)
	assert response.headers["X-RateLimit-Remaining"] == "0"
	assert response.headers["X-RateLimit-Reset"].isdigit()


def test_health_check_returns_ping_without_initializing_database(
	client: TestClient, data_file: Path
):
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {"status": "ok"}
	assert not data_file.exists()


def test_readiness_check_initializes_schema_without_memory_rows(
	client: TestClient, data_file: Path
):
	response = client.get("/ready")

	assert response.status_code == 200
	assert response.json() == {
		"status": "ready",
		"checks": {
			"database": "ok",
			"memories_table": "ok",
		},
	}
	with sqlite3.connect(data_file) as connection:
		table = connection.execute(
			"""
			SELECT 1
			FROM sqlite_master
			WHERE type = 'table' AND name = 'memories'
			"""
		).fetchone()
	assert table is not None
	assert read_database(data_file) == []


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


def test_post_memory_rate_limit_uses_client_id_identity(monkeypatch, data_file: Path):
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE", "1")
	test_client = TestClient(app_main.create_app())

	first_response = test_client.post(
		"/memories",
		headers={"X-Client-Id": "agent-a"},
		json={"content": "First write", "tags": ["rate-limit"]},
	)
	second_response = test_client.post(
		"/memories",
		headers={"X-Client-Id": " agent-a "},
		json={"content": "Second write", "tags": ["rate-limit"]},
	)
	other_client_response = test_client.post(
		"/memories",
		headers={"X-Client-Id": "agent-b"},
		json={"content": "Other client write", "tags": ["rate-limit"]},
	)

	assert first_response.status_code == 200
	assert "X-RateLimit-Limit" not in first_response.headers
	assert_rate_limited(second_response, 1)
	assert other_client_response.status_code == 200
	assert len(read_database(data_file)) == 2


def test_read_rate_limit_counts_validation_failures(monkeypatch, data_file: Path):
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_READS_PER_MINUTE", "1")
	test_client = TestClient(app_main.create_app())

	validation_response = test_client.get(
		"/memories/not-an-int",
		headers={"X-Client-Id": "reader"},
	)
	limited_response = test_client.get(
		"/memories",
		headers={"X-Client-Id": "reader"},
	)

	assert validation_response.status_code == 422
	assert_rate_limited(limited_response, 1)
	assert read_database(data_file) == []


def test_batch_create_uses_separate_rate_limit_bucket(monkeypatch, data_file: Path):
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_BATCH_PER_MINUTE", "1")
	test_client = TestClient(app_main.create_app())

	first_response = test_client.post(
		"/memories/batch",
		json=[{"content": "First batch", "tags": ["batch"]}],
	)
	second_response = test_client.post(
		"/memories/batch",
		json=[{"content": "Second batch", "tags": ["batch"]}],
	)

	assert first_response.status_code == 200
	assert_rate_limited(second_response, 1)
	assert len(read_database(data_file)) == 1


def test_rate_limiting_can_be_disabled(monkeypatch, data_file: Path):
	monkeypatch.setenv("MEMORIES_RATE_LIMITING_ENABLED", "false")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE", "1")
	test_client = TestClient(app_main.create_app())

	first_response = test_client.post(
		"/memories",
		json={"content": "First write", "tags": ["rate-limit"]},
	)
	second_response = test_client.post(
		"/memories",
		json={"content": "Second write", "tags": ["rate-limit"]},
	)

	assert first_response.status_code == 200
	assert second_response.status_code == 200
	assert len(read_database(data_file)) == 2


def test_body_size_limit_runs_before_rate_limit(monkeypatch, data_file: Path):
	monkeypatch.setenv("MEMORIES_REQUEST_BODY_MAX_BYTES", "10")
	monkeypatch.setenv("MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE", "1")
	test_client = TestClient(app_main.create_app())

	oversized_response = test_client.post(
		"/memories",
		content="x" * 11,
		headers={"Content-Type": "application/json"},
	)
	first_counted_response = test_client.post("/memories", json={})
	second_counted_response = test_client.post("/memories", json={})

	assert oversized_response.status_code == 413
	assert first_counted_response.status_code == 422
	assert_rate_limited(second_counted_response, 1)
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
