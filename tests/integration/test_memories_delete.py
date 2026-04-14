from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database
from helpers.memory_builders import expected_memory

from app import storage


def test_delete_memory_by_id_returns_deleted_memory_with_full_shape(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a DELETE request to the /memories/{id} endpoint returns the
	deleted memory with the full shape.
	Including:
	- `created_at`
	- `updated_at`
	- `last_accessed_at`
	fields and removes it from the database.

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

	response = client.delete("/memories/1")

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
	assert read_database(data_file) == []


def test_delete_memory_by_id_not_found_returns_404(client: TestClient, data_file: Path):
	"""
	Testing if a DELETE request to the /memories/{id} endpoint returns a 404 status
	code when the memory is not found.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""
	response = client.delete("/memories/1")

	assert response.status_code == 404
	assert response.json() == {"detail": "Memory not found"}
	assert read_database(data_file) == []
