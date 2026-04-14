from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database
from helpers.memory_builders import expected_memory

from app import storage


def test_post_memory_returns_created_memory_with_defaults(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a POST request creates a memory with default values for
	- `created_at`
	- `updated_at`
	- `last_accessed_at`
	fields because they are server-managed fields.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

	response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)

	expected = expected_memory(
		1,
		"Learning FastAPI testing",
		["python", "api"],
		created_at=timestamp,
		updated_at=timestamp,
		last_accessed_at=None,
	)

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == [expected]


def test_post_memory_accepts_optional_memory_type_and_status(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a POST request creates a memory with optional
	- `memory_type`
	- `status`
	fields included within the request.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

	response = client.post(
		"/memories",
		json={
			"content": "User prefers concise responses",
			"tags": ["preference", "writing-style"],
			"memory_type": "preference",
			"status": "archived",
		},
	)

	expected = expected_memory(
		1,
		"User prefers concise responses",
		["preference", "writing-style"],
		created_at=timestamp,
		updated_at=timestamp,
		last_accessed_at=None,
		memory_type="preference",
		status="archived",
	)

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == [expected]


def test_post_memory_handles_memory_missing_tags(client: TestClient, data_file: Path):
	"""
	Testing if a POST request with missing `tags` field returns a 422 error
	with the correct validation message.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""
	response = client.post("/memories", json={"content": "Learning FastAPI testing"})

	assert response.status_code == 422
	body = response.json()
	assert any(
		error["loc"] == ["body", "tags"] and error["type"] == "missing" for error in body["detail"]
	)
	assert read_database(data_file) == []


def test_post_memory_handles_memory_missing_content(client: TestClient, data_file: Path):
	"""
	Testing if a POST request with missing `content` field returns a 422 error
	with the correct validation message.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""
	response = client.post("/memories", json={"tags": ["python", "api"]})

	assert response.status_code == 422
	body = response.json()
	assert any(
		error["loc"] == ["body", "content"] and error["type"] == "missing"
		for error in body["detail"]
	)
	assert read_database(data_file) == []


def test_post_memory_rejects_invalid_memory_type(client: TestClient, data_file: Path):
	"""
	Testing if a POST request with an invalid `memory_type` field returns a 422 error
	with the correct validation message.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""

	response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
			"memory_type": "unknown",
		},
	)

	assert response.status_code == 422
	body = response.json()
	assert any(
		error["loc"] == ["body", "memory_type"] and "memory_type must be one of" in error["msg"]
		for error in body["detail"]
	)
	assert read_database(data_file) == []


def test_post_memory_rejects_invalid_status(client: TestClient, data_file: Path):
	"""
	Testing if a POST request with an invalid `status` field returns a 422 error
	with the correct validation message.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""
	response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
			"status": "pending",
		},
	)

	assert response.status_code == 422
	body = response.json()
	assert any(
		error["loc"] == ["body", "status"] and "status must be one of" in error["msg"]
		for error in body["detail"]
	)
	assert read_database(data_file) == []


def test_post_memory_rejects_server_managed_fields(client: TestClient, data_file: Path):
	"""
	Testing if a POST request with server-managed fields returns a 422 error
	with the correct validation message.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""
	response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
			"created_at": "2026-04-06T14:12:00.000000Z",
			"updated_at": "2026-04-06T14:12:00.000000Z",
			"last_accessed_at": "2026-04-06T14:12:00.000000Z",
			"version": 99,
		},
	)

	assert response.status_code == 422
	body = response.json()
	assert any(
		error["loc"] == ["body", "created_at"] and error["type"] == "extra_forbidden"
		for error in body["detail"]
	)
	assert any(
		error["loc"] == ["body", "version"] and error["type"] == "extra_forbidden"
		for error in body["detail"]
	)
	assert read_database(data_file) == []
