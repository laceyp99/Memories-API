import pytest

from app.mcp_server import delete_memory_tool, search_memories_tool
from app.schemas import Memory


def test_search_memories_tool_returns_serialized_memory_list(monkeypatch):
	monkeypatch.setattr(
		"app.mcp_server.search_memories",
		lambda query: [
			Memory(
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
		],
	)

	result = search_memories_tool("python")

	assert result == [
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
		}
	]


def test_delete_memory_tool_raises_value_error_when_missing(monkeypatch):
	monkeypatch.setattr("app.mcp_server.delete_memory", lambda memory_id: None)

	with pytest.raises(ValueError, match="Memory 7 not found"):
		delete_memory_tool(7)
