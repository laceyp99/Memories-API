import pytest

from app.mcp_server import delete_memory_tool, query_memories_tool
from app.schemas import Memory


def test_query_memories_tool_returns_paginated_response_from_shared_retrieval_path(monkeypatch):
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

	result = query_memories_tool(
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


def test_delete_memory_tool_raises_value_error_when_missing(monkeypatch):
	monkeypatch.setattr("app.mcp_server.delete_memory", lambda memory_id: None)

	with pytest.raises(ValueError, match="Memory 7 not found"):
		delete_memory_tool(7)


def test_delete_memory_tool_returns_soft_deleted_memory(monkeypatch):
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

	result = delete_memory_tool(7)

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
