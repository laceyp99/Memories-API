from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database
from helpers.memory_builders import expected_memory

from app import storage

DEFAULT_LIMIT = 10


def _expected_page(
	*, items: list[dict], total: int, limit: int = DEFAULT_LIMIT, offset: int = 0
) -> dict:
	return {
		"items": items,
		"total": total,
		"limit": limit,
		"offset": offset,
		"has_more": offset + len(items) < total,
	}


def test_get_memories_empty_returns_paginated_response(client: TestClient, data_file: Path):
	response = client.get("/memories")

	assert response.status_code == 200
	assert response.json() == _expected_page(items=[], total=0)
	assert read_database(data_file) == []


def test_get_memories_returns_paginated_shape_and_updates_last_accessed_at(
	client: TestClient, data_file: Path, monkeypatch
):
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

	response = client.get("/memories")

	expected = [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at="2026-04-06T14:12:00.000000Z",
			updated_at="2026-04-06T14:12:00.000000Z",
			last_accessed_at="2026-04-06T14:20:00.000000Z",
		)
	]

	assert response.status_code == 200
	assert response.json() == _expected_page(items=expected, total=1)
	assert read_database(data_file) == expected


def test_get_memories_filters_by_status_memory_type_and_exact_tag(
	client: TestClient, data_file: Path, monkeypatch
):
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:13:00.000000Z",
			"2026-04-06T14:14:00.000000Z",
			"2026-04-06T14:30:00.000000Z",
		]
	)
	monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

	client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
			"memory_type": "instruction",
			"status": "active",
		},
	)
	client.post(
		"/memories",
		json={
			"content": "Learning Python typing",
			"tags": ["pythonista", "typing"],
			"memory_type": "instruction",
			"status": "active",
		},
	)
	client.post(
		"/memories",
		json={
			"content": "Project launch is archived",
			"tags": ["python", "launch"],
			"memory_type": "task_context",
			"status": "archived",
		},
	)

	response = client.get(
		"/memories",
		params={
			"status": "active",
			"memory_type": "instruction",
			"tag": "python",
		},
	)

	expected_items = [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at="2026-04-06T14:12:00.000000Z",
			updated_at="2026-04-06T14:12:00.000000Z",
			last_accessed_at="2026-04-06T14:30:00.000000Z",
			memory_type="instruction",
		),
	]

	assert response.status_code == 200
	assert response.json() == _expected_page(items=expected_items, total=1)
	assert read_database(data_file) == [
		expected_items[0],
		expected_memory(
			2,
			"Learning Python typing",
			["pythonista", "typing"],
			created_at="2026-04-06T14:13:00.000000Z",
			updated_at="2026-04-06T14:13:00.000000Z",
			last_accessed_at=None,
			memory_type="instruction",
		),
		expected_memory(
			3,
			"Project launch is archived",
			["python", "launch"],
			created_at="2026-04-06T14:14:00.000000Z",
			updated_at="2026-04-06T14:14:00.000000Z",
			last_accessed_at=None,
			memory_type="task_context",
			status="archived",
		),
	]


def test_get_memories_filters_by_free_text_query_case_insensitively(
	client: TestClient, data_file: Path, monkeypatch
):
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:13:00.000000Z",
			"2026-04-06T14:25:00.000000Z",
			"2026-04-06T14:26:00.000000Z",
		]
	)
	monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

	client.post(
		"/memories",
		json={
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
		},
	)
	client.post(
		"/memories",
		json={
			"content": "Database query notes",
			"tags": ["SQL"],
		},
	)

	response = client.get("/memories", params={"q": "PY"})

	expected_items = [
		expected_memory(
			1,
			"Learning FastAPI testing",
			["python", "api"],
			created_at="2026-04-06T14:12:00.000000Z",
			updated_at="2026-04-06T14:12:00.000000Z",
			last_accessed_at="2026-04-06T14:25:00.000000Z",
		)
	]

	assert response.status_code == 200
	assert response.json() == _expected_page(items=expected_items, total=1)
	assert read_database(data_file) == [
		expected_items[0],
		expected_memory(
			2,
			"Database query notes",
			["SQL"],
			created_at="2026-04-06T14:13:00.000000Z",
			updated_at="2026-04-06T14:13:00.000000Z",
			last_accessed_at=None,
		),
	]


def test_get_memories_supports_explicit_sort_options_with_stable_tiebreaker(
	client: TestClient, monkeypatch
):
	timestamp = "2026-04-06T14:12:00.000000Z"
	monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

	client.post(
		"/memories",
		json={
			"content": "First memory",
			"tags": ["one"],
		},
	)
	client.post(
		"/memories",
		json={
			"content": "Second memory",
			"tags": ["two"],
		},
	)

	response = client.get("/memories", params={"sort": "created_at"})

	assert response.status_code == 200
	body = response.json()
	assert isinstance(body, dict)
	assert [item["id"] for item in body["items"]] == [2, 1]


def test_get_memories_returns_pagination_metadata(client: TestClient, monkeypatch):
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:13:00.000000Z",
			"2026-04-06T14:14:00.000000Z",
			"2026-04-06T14:30:00.000000Z",
			"2026-04-06T14:31:00.000000Z",
		]
	)
	monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

	for content in ["First", "Second", "Third"]:
		client.post("/memories", json={"content": content, "tags": [content.lower()]})

	response = client.get("/memories", params={"limit": 2, "offset": 1})

	assert response.status_code == 200
	body = response.json()
	assert isinstance(body, dict)
	assert body["total"] == 3
	assert body["limit"] == 2
	assert body["offset"] == 1
	assert body["has_more"] is False
	assert [item["id"] for item in body["items"]] == [2, 3]


def test_get_memories_updates_only_returned_page_items(
	client: TestClient, data_file: Path, monkeypatch
):
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:13:00.000000Z",
			"2026-04-06T14:14:00.000000Z",
			"2026-04-06T14:30:00.000000Z",
		]
	)
	monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

	for content in ["First", "Second", "Third"]:
		client.post("/memories", json={"content": content, "tags": [content.lower()]})

	response = client.get("/memories", params={"limit": 2, "offset": 1})

	expected_items = [
		expected_memory(
			2,
			"Second",
			["second"],
			created_at="2026-04-06T14:13:00.000000Z",
			updated_at="2026-04-06T14:13:00.000000Z",
			last_accessed_at="2026-04-06T14:30:00.000000Z",
		),
		expected_memory(
			3,
			"Third",
			["third"],
			created_at="2026-04-06T14:14:00.000000Z",
			updated_at="2026-04-06T14:14:00.000000Z",
			last_accessed_at="2026-04-06T14:30:00.000000Z",
		),
	]

	assert response.status_code == 200
	assert response.json() == _expected_page(items=expected_items, total=3, limit=2, offset=1)
	assert read_database(data_file) == [
		expected_memory(
			1,
			"First",
			["first"],
			created_at="2026-04-06T14:12:00.000000Z",
			updated_at="2026-04-06T14:12:00.000000Z",
			last_accessed_at=None,
		),
		*expected_items,
	]
