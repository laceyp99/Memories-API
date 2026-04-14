from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database
from helpers.memory_builders import expected_memory

from app import storage


def test_search_memories_returns_expanded_shape(client: TestClient, data_file: Path, monkeypatch):
	"""
	Testing if a GET request to the /search endpoint returns memories with
	the expanded shape.
	Including:
	- `created_at`
	- `updated_at`
	- `last_accessed_at`
	fields without modifying the `last_accessed_at` timestamp.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

	create_response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)
	assert create_response.status_code == 200

	response = client.get("/search", params={"query": "python"})

	expected = [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at=timestamp,
			updated_at=timestamp,
			last_accessed_at=None,
		)
	]

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == expected


def test_search_memories_returns_empty_list_when_no_matches(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a GET request to the /search endpoint returns an empty list when there are no matching memories.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

	create_response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)
	assert create_response.status_code == 200

	response = client.get("/search", params={"query": "javascript"})

	expected_database = [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at=timestamp,
			updated_at=timestamp,
			last_accessed_at=None,
		)
	]

	assert response.status_code == 200
	assert response.json() == []
	assert read_database(data_file) == expected_database


def test_search_memories_returns_empty_list_when_database_is_empty(client: TestClient):
	"""
	Testing if a GET request to the /search endpoint returns an empty list when the database is empty.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
	"""
	response = client.get("/search", params={"query": "python"})

	assert response.status_code == 200
	assert response.json() == []


def test_search_memories_is_case_insensitive(client: TestClient, data_file: Path, monkeypatch):
	"""
	Testing if a GET request to the /search endpoint is case-insensitive when searching for memories.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

	create_response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)
	assert create_response.status_code == 200

	response = client.get("/search", params={"query": "PYTHON"})

	expected = [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at=timestamp,
			updated_at=timestamp,
			last_accessed_at=None,
		)
	]

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == expected


def test_search_memories_does_not_modify_last_accessed_at(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a GET request to the /search endpoint does not modify the `last_accessed_at` timestamp of memories.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

	create_response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)
	assert create_response.status_code == 200

	response = client.get("/search", params={"query": "python"})

	expected = [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at=timestamp,
			updated_at=timestamp,
			last_accessed_at=None,
		)
	]

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == expected
