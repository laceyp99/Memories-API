import pytest

from app.mcp_server import prime_memory_context, retire_memory, search_memories
from app.schemas import Memory


def test_search_memories_returns_paginated_response_from_shared_retrieval_path(monkeypatch):
	seen = {}
	returned_memory = Memory(
		id=1,
		content="Learning FastAPI testing",
		tags=["python", "api"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:12:00.000000Z",
		last_accessed_at=None,
		memory_type="fact",
		status="active",
		version=1,
	)
	refreshed_memory = returned_memory.model_copy(
		update={"last_accessed_at": "2026-04-06T14:20:00.000000Z"}
	)

	def fake_get_memories_page(query):
		seen["query"] = query
		return [returned_memory], 3

	monkeypatch.setattr("app.mcp_server.get_memories_page", fake_get_memories_page)
	monkeypatch.setattr(
		"app.mcp_server.refresh_memories_last_accessed",
		lambda memories: [refreshed_memory],
	)

	result = search_memories(
		status="active",
		memory_type="fact",
		tag="python",
		q="FastAPI",
		sort="updated_at",
		limit=1,
		offset=1,
	)

	assert seen["query"].model_dump() == {
		"status": "active",
		"memory_type": "fact",
		"tag": "python",
		"q": "FastAPI",
		"sort": "updated_at",
		"limit": 1,
		"offset": 1,
	}
	assert result == {
		"items": [
			{
				"id": 1,
				"content": "Learning FastAPI testing",
				"tags": ["python", "api"],
				"created_at": "2026-04-06T14:12:00.000000Z",
				"updated_at": "2026-04-06T14:12:00.000000Z",
				"last_accessed_at": "2026-04-06T14:20:00.000000Z",
				"memory_type": "fact",
				"status": "active",
				"version": 1,
			}
		],
		"total": 3,
		"limit": 1,
		"offset": 1,
		"has_more": True,
	}


def test_prime_memory_context_returns_two_shared_retrieval_pages(monkeypatch):
	seen = []
	preference_memory = Memory(
		id=1,
		content="Pref memory",
		tags=["preference"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:12:00.000000Z",
		last_accessed_at=None,
		memory_type="preference",
		status="active",
		version=1,
	)
	identity_memory = Memory(
		id=2,
		content="Identity memory",
		tags=["identity"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:12:00.000000Z",
		last_accessed_at=None,
		memory_type="identity",
		status="active",
		version=1,
	)

	def fake_get_memories_page(query):
		seen.append(query.model_dump())
		if query.memory_type == "preference":
			return [preference_memory], 1
		return [identity_memory], 1

	def fake_refresh_memories_last_accessed(memories):
		return memories

	monkeypatch.setattr("app.mcp_server.get_memories_page", fake_get_memories_page)
	monkeypatch.setattr(
		"app.mcp_server.refresh_memories_last_accessed", fake_refresh_memories_last_accessed
	)

	result = prime_memory_context()

	assert seen == [
		{
			"status": "active",
			"memory_type": "preference",
			"tag": None,
			"q": None,
			"sort": "updated_at",
			"limit": 10,
			"offset": 0,
		},
		{
			"status": "active",
			"memory_type": "identity",
			"tag": None,
			"q": None,
			"sort": "updated_at",
			"limit": 10,
			"offset": 0,
		},
	]
	assert result == {
		"preferences": {
			"items": [preference_memory.model_dump()],
			"total": 1,
			"limit": 10,
			"offset": 0,
			"has_more": False,
		},
		"identities": {
			"items": [identity_memory.model_dump()],
			"total": 1,
			"limit": 10,
			"offset": 0,
			"has_more": False,
		},
	}


def test_retire_memory_raises_value_error_when_missing(monkeypatch):
	monkeypatch.setattr("app.mcp_server.delete_memory", lambda memory_id: None)

	with pytest.raises(ValueError, match="Memory 7 not found"):
		retire_memory(7)


def test_retire_memory_returns_soft_deleted_memory(monkeypatch):
	deleted_memory = Memory(
		id=7,
		content="Unsafe note",
		tags=["safety"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:20:00.000000Z",
		last_accessed_at=None,
		memory_type="fact",
		status="deleted",
		version=2,
	)

	monkeypatch.setattr("app.mcp_server.delete_memory", lambda memory_id: deleted_memory)

	result = retire_memory(7)

	assert result == {
		"id": 7,
		"content": "Unsafe note",
		"tags": ["safety"],
		"created_at": "2026-04-06T14:12:00.000000Z",
		"updated_at": "2026-04-06T14:20:00.000000Z",
		"last_accessed_at": None,
		"memory_type": "fact",
		"status": "deleted",
		"version": 2,
	}
