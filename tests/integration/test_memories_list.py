from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database
from helpers.memory_builders import expected_memory

from app import storage


def test_get_memories_empty_returns_empty_list(client: TestClient, data_file: Path):
	"""
	Testing if a GET request to the /memories endpoint returns an empty list
	when there are no memories in the database.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""
	response = client.get("/memories")

	assert response.status_code == 200
	assert response.json() == []
	assert read_database(data_file) == []


def test_get_memories_returns_expanded_shape_without_updating_access_time(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a GET request to the /memories endpoint returns memories
	with the expanded shape.
	Including
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

	response = client.get("/memories")

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
