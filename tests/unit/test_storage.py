import json

from app.schemas import MemoryUpdate
from app.storage import find_next_id, search_memories, update_memory


def test_find_next_id_returns_next_largest_id():
	data = [{"id": 1}, {"id": 4}, {"id": 2}]

	assert find_next_id(data) == 5


def test_search_memories_matches_content_and_tags_case_insensitively(monkeypatch):
	data = [
		{
			"id": 1,
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
			"created_at": "2026-04-06T14:12:00.000000Z",
			"updated_at": "2026-04-06T14:12:00.000000Z",
			"last_accessed_at": None,
			"memory_type": "fact",
			"status": "active",
			"version": 1,
		},
		{
			"id": 2,
			"content": "Database query notes",
			"tags": ["SQL"],
			"created_at": "2026-04-06T14:13:00.000000Z",
			"updated_at": "2026-04-06T14:13:00.000000Z",
			"last_accessed_at": None,
			"memory_type": "task_context",
			"status": "active",
			"version": 1,
		},
	]

	monkeypatch.setattr("app.storage.load_data", lambda: data)

	results = search_memories("sql")

	assert [memory.id for memory in results] == [2]


def test_update_memory_returns_existing_memory_without_saving_on_no_op(monkeypatch):
	stored_item = {
		"id": 1,
		"content": "Learning FastAPI testing",
		"tags": ["python", "api"],
		"created_at": "2026-04-06T14:12:00.000000Z",
		"updated_at": "2026-04-06T14:12:00.000000Z",
		"last_accessed_at": None,
		"memory_type": "fact",
		"status": "active",
		"version": 1,
	}
	data = [stored_item.copy()]

	monkeypatch.setattr("app.storage.load_data", lambda: data)
	monkeypatch.setattr(
		"app.storage.save_data",
		lambda _data: (_ for _ in ()).throw(AssertionError("save_data should not be called")),
	)

	result = update_memory(
		1,
		MemoryUpdate(content="Learning FastAPI testing", tags=["python", "api"]),
	)

	assert result is not None
	assert result.model_dump() == stored_item


def test_update_memory_persists_changes(monkeypatch):
	stored_item = {
		"id": 1,
		"content": "Learning FastAPI testing",
		"tags": ["python", "api"],
		"created_at": "2026-04-06T14:12:00.000000Z",
		"updated_at": "2026-04-06T14:12:00.000000Z",
		"last_accessed_at": None,
		"memory_type": "fact",
		"status": "active",
		"version": 1,
	}
	data = [stored_item.copy()]
	saved_payloads: list[str] = []

	monkeypatch.setattr("app.storage.load_data", lambda: data)
	monkeypatch.setattr("app.storage.current_timestamp", lambda: "2026-04-06T14:30:00.000000Z")
	monkeypatch.setattr(
		"app.storage.save_data",
		lambda payload: saved_payloads.append(json.dumps(payload, sort_keys=True)),
	)

	result = update_memory(1, MemoryUpdate(status="archived"))

	assert result is not None
	assert result.status == "archived"
	assert result.updated_at == "2026-04-06T14:30:00.000000Z"
	assert result.version == 2
	assert len(saved_payloads) == 1
