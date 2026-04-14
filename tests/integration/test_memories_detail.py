from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database
from helpers.memory_builders import expected_memory

from app import storage


def test_get_memory_by_id_updates_last_accessed_at(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a GET request to the /memories/{id} endpoint updates
	the `last_accessed_at` timestamp.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:20:00.000000Z",
		]
	)
	monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

	create_response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)
	assert create_response.status_code == 200

	response = client.get("/memories/1")

	expected = expected_memory(
		1,
		"Learning FastAPI testing",
		["python", "api"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:12:00.000000Z",
		last_accessed_at="2026-04-06T14:20:00.000000Z",
	)

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == [expected]


def test_get_memory_by_id_not_found_returns_404(client: TestClient, data_file: Path):
	"""
	Testing if a GET request to the /memories/{id} endpoint returns a 404 status
	code when the memory is not found.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""
	response = client.get("/memories/1")

	assert response.status_code == 404
	assert response.json() == {"detail": "Memory not found"}
	assert read_database(data_file) == []
