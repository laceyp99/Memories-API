from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database
from helpers.memory_builders import expected_memory

from app import storage


def test_post_memory_batch_returns_created_memories_with_defaults(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a POST request to the /memories/batch endpoint creates
	multiple memories with default values for:
	- `created_at`
	- `updated_at`
	- `last_accessed_at`
	fields because they are server-managed fields.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""

	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:13:00.000000Z",
			"2026-04-06T14:14:00.000000Z",
		]
	)
	monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

	response = client.post(
		"/memories/batch",
		json=[
			{
				"content": "Learning FastAPI testing",
				"tags": ["python", "api"],
			},
			{
				"content": "Practicing SQL joins and query optimization",
				"tags": ["database", "sql"],
				"memory_type": "task_context",
			},
			{
				"content": "Building a CLI tool with argparse",
				"tags": ["python", "tooling"],
				"status": "superseded",
			},
		],
	)

	expected = [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at="2026-04-06T14:12:00.000000Z",
			updated_at="2026-04-06T14:12:00.000000Z",
			last_accessed_at=None,
		),
		expected_memory(
			2,
			"Practicing SQL joins and query optimization",
			["database", "sql"],
			created_at="2026-04-06T14:13:00.000000Z",
			updated_at="2026-04-06T14:13:00.000000Z",
			last_accessed_at=None,
			memory_type="task_context",
		),
		expected_memory(
			3,
			"Building a CLI tool with argparse",
			["python", "tooling"],
			created_at="2026-04-06T14:14:00.000000Z",
			updated_at="2026-04-06T14:14:00.000000Z",
			last_accessed_at=None,
			status="superseded",
		),
	]

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == expected


def test_post_memory_batch_returns_400_for_invalid_input(client: TestClient, data_file: Path):
	"""
	Testing if a POST request to the /memories/batch endpoint with invalid input
	returns a 400 status code.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
	"""

	response = client.post(
		"/memories/batch",
		json=[
			{
				"content": "Valid memory",
				"tags": ["valid"],
			},
			{
				"content": "Invalid memory missing tags",
			},
			{
				"content": "Another valid memory",
				"tags": ["valid"],
			},
		],
	)

	assert response.status_code == 422
	assert response.json() == {
		"detail": [
			{
				"input": {"content": "Invalid memory missing tags"},
				"loc": ["body", 1, "tags"],
				"msg": "Field required",
				"type": "missing",
			}
		]
	}
	assert read_database(data_file) == []
