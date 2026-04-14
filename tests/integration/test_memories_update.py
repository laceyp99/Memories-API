from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database
from helpers.memory_builders import expected_memory

from app import storage


def test_patch_memory_by_id_updates_fields_and_increments_version(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a PATCH request to the /memories/{id} endpoint updates
	the memory fields and increments the version.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:25:00.000000Z",
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

	response = client.patch(
		"/memories/1",
		json={
			"content": "Practicing SQL joins and query optimization",
			"tags": ["database", "sql"],
			"memory_type": "task_context",
			"status": "archived",
		},
	)

	expected = expected_memory(
		1,
		"Practicing SQL joins and query optimization",
		["database", "sql"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:25:00.000000Z",
		last_accessed_at=None,
		memory_type="task_context",
		status="archived",
		version=2,
	)

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == [expected]


def test_patch_memory_by_id_partial_data_preserves_untouched_fields(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a PATCH request to the /memories/{id} endpoint with partial data
	updates only the provided fields and preserves the untouched fields.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:30:00.000000Z",
		]
	)
	monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

	create_response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
			"memory_type": "instruction",
			"status": "active",
		},
	)
	assert create_response.status_code == 200

	response = client.patch("/memories/1", json={"content": "Practicing FastAPI testing"})

	expected = expected_memory(
		1,
		"Practicing FastAPI testing",
		["python", "api"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:30:00.000000Z",
		last_accessed_at=None,
		memory_type="instruction",
		status="active",
		version=2,
	)

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == [expected]


def test_patch_memory_by_id_no_op_does_not_change_updated_at_or_version(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a PATCH request to the /memories/{id} endpoint with no changes
	does not update the `updated_at` timestamp or increment the version.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
		monkeypatch: The MonkeyPatch for modifying attributes during tests.
	"""
	create_timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: create_timestamp)

	create_response = client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)
	assert create_response.status_code == 200

	monkeypatch.setattr(
		storage,
		"current_timestamp",
		lambda: (_ for _ in ()).throw(AssertionError("PATCH should not refresh timestamps")),
	)

	response = client.patch(
		"/memories/1",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)

	expected = expected_memory(
		1,
		"Learning FastAPI testing",
		["python", "api"],
		created_at=create_timestamp,
		updated_at=create_timestamp,
		last_accessed_at=None,
	)

	assert response.status_code == 200
	assert response.json() == expected
	assert read_database(data_file) == [expected]


def test_patch_memory_rejects_invalid_status(client: TestClient, data_file: Path, monkeypatch):
	"""
	Testing if a PATCH request to the /memories/{id} endpoint with an invalid
	`status` field returns a 422 error with the correct validation message.

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

	response = client.patch("/memories/1", json={"status": "pending"})

	assert response.status_code == 422
	body = response.json()
	assert any(
		error["loc"] == ["body", "status"] and "status must be one of" in error["msg"]
		for error in body["detail"]
	)
	assert read_database(data_file) == [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at=timestamp,
			updated_at=timestamp,
			last_accessed_at=None,
		)
	]


def test_patch_memory_rejects_server_managed_fields(
	client: TestClient, data_file: Path, monkeypatch
):
	"""
	Testing if a PATCH request to the /memories/{id} endpoint with server-managed
	fields returns a 422 error with the correct validation message.

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

	response = client.patch(
		"/memories/1",
		json={
			"updated_at": "2026-04-06T15:00:00.000000Z",
			"version": 99,
		},
	)

	assert response.status_code == 422
	body = response.json()
	assert any(
		error["loc"] == ["body", "updated_at"] and error["type"] == "extra_forbidden"
		for error in body["detail"]
	)
	assert any(
		error["loc"] == ["body", "version"] and error["type"] == "extra_forbidden"
		for error in body["detail"]
	)
	assert read_database(data_file) == [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at=timestamp,
			updated_at=timestamp,
			last_accessed_at=None,
		)
	]


def test_patch_memory_by_id_not_found_returns_404(client: TestClient, data_file: Path):
	"""
	Testing if a PATCH request to the /memories/{id} endpoint returns a 404 status
	code when the memory is not found.

	Args:
		client (TestClient): The TestClient for making requests to the FastAPI app.
		data_file (Path): The Path for accessing the test database file.
	"""
	response = client.patch("/memories/1", json={"content": "Updated content"})

	assert response.status_code == 404
	assert response.json() == {"detail": "Memory not found"}
	assert read_database(data_file) == []
