import pytest

from app.mcp_server import create_memory_tool, read_memory, serialize_memory
from app.schemas import Memory


def test_serialize_memory_returns_model_dump():
	memory = Memory(
		id=1,
		content="Remember this",
		tags=["note"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:12:00.000000Z",
		last_accessed_at=None,
		memory_type="fact",
		status="active",
		version=1,
	)

	assert serialize_memory(memory) == memory.model_dump()


def test_read_memory_raises_value_error_when_missing(monkeypatch):
	monkeypatch.setattr("app.mcp_server.get_memory", lambda memory_id: None)

	with pytest.raises(ValueError, match="Memory 99 not found"):
		read_memory(99)


def test_create_memory_tool_uses_schema_defaults(monkeypatch):
	created = {}

	def fake_create_memory(memory):
		created["memory"] = memory
		return Memory(
			id=1,
			content=memory.content,
			tags=memory.tags,
			created_at="2026-04-06T14:12:00.000000Z",
			updated_at="2026-04-06T14:12:00.000000Z",
			last_accessed_at=None,
			memory_type=memory.memory_type,
			status=memory.status,
			version=1,
		)

	monkeypatch.setattr("app.mcp_server.create_memory", fake_create_memory)

	result = create_memory_tool(content="Remember this", tags=["note"])

	assert created["memory"].memory_type == "fact"
	assert created["memory"].status == "active"
	assert result["content"] == "Remember this"
