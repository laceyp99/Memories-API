import asyncio

import pytest

from app.mcp_server import (
	build_memories_tool_behavior_resource,
	build_use_memories_api_prompt_messages,
	create_memory_tool,
	mcp,
	query_memories_tool,
	read_memory,
	serialize_memory,
	update_memory_tool,
)
from app.schemas import Memory, MemoryUpdate


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


def test_query_memories_tool_uses_default_query_values(monkeypatch):
	seen = {}

	def fake_get_memories_page(query):
		seen["query"] = query
		return [], 0

	monkeypatch.setattr("app.mcp_server.get_memories_page", fake_get_memories_page)
	monkeypatch.setattr("app.mcp_server.refresh_memories_last_accessed", lambda memories: memories)

	result = query_memories_tool()

	assert seen["query"].model_dump() == {
		"status": None,
		"memory_type": None,
		"tag": None,
		"q": None,
		"sort": "id",
		"limit": 10,
		"offset": 0,
	}
	assert result == {
		"items": [],
		"total": 0,
		"limit": 10,
		"offset": 0,
		"has_more": False,
	}


def test_update_memory_tool_omits_unset_optional_fields(monkeypatch):
	seen = {}

	def fake_update_memory(memory_id, memory):
		seen["memory_id"] = memory_id
		seen["memory"] = memory
		return Memory(
			id=memory_id,
			content=memory.content or "Remember this",
			tags=["note"],
			created_at="2026-04-06T14:12:00.000000Z",
			updated_at="2026-04-06T14:13:00.000000Z",
			last_accessed_at=None,
			memory_type="fact",
			status="active",
			version=2,
		)

	monkeypatch.setattr("app.mcp_server.update_memory", fake_update_memory)

	result = update_memory_tool(7, content="Updated memory content")

	assert seen["memory_id"] == 7
	assert isinstance(seen["memory"], MemoryUpdate)
	assert seen["memory"].model_dump(exclude_unset=True) == {"content": "Updated memory content"}
	assert result["content"] == "Updated memory content"


def test_build_memories_tool_behavior_resource_includes_policy_and_recipes():
	resource_text = build_memories_tool_behavior_resource()

	assert "# Memories Tool Behavior Policy" in resource_text
	assert "# Query Recipes" in resource_text
	assert "### Sensitive Data" in resource_text
	assert "## Deduping and Updates" in resource_text
	assert "## Tag Guidance" in resource_text
	assert "query_memories_tool" in resource_text


def test_build_use_memories_api_prompt_messages_returns_static_messages():
	messages = build_use_memories_api_prompt_messages()

	assert [message.role for message in messages] == ["assistant"]
	assert "memories-api MCP server" in messages[0].content.text
	assert "Default to autonomous memory handling" in messages[0].content.text
	assert "sensitive markers" in messages[0].content.text
	assert "Deduping process before writes" in messages[0].content.text
	assert "Memory actions:" in messages[0].content.text


def test_mcp_lists_tool_behavior_resource():
	resources = asyncio.run(mcp.list_resources())
	resource = next(
		item for item in resources if str(item.uri) == "memories://policy/tool-behavior"
	)

	assert resource.name == "memories-tool-behavior-policy"
	assert resource.mimeType == "text/markdown"


def test_mcp_reads_tool_behavior_resource():
	contents = asyncio.run(mcp.read_resource("memories://policy/tool-behavior"))
	content = list(contents)

	assert len(content) == 1
	assert content[0].mime_type == "text/markdown"
	assert "# Memories Tool Behavior Policy" in content[0].content
	assert "### Sensitive Data" in content[0].content
	assert "## Deduping and Updates" in content[0].content
	assert "## Tag Guidance" in content[0].content


def test_mcp_lists_static_memories_prompt():
	prompts = asyncio.run(mcp.list_prompts())
	prompt = next(item for item in prompts if item.name == "use_memories_api")

	assert prompt.description is not None
	assert prompt.arguments == []


def test_mcp_gets_static_memories_prompt_messages():
	prompt = asyncio.run(mcp.get_prompt("use_memories_api"))

	assert [message.role for message in prompt.messages] == ["assistant"]
	assert "memories-api MCP server" in prompt.messages[0].content.text
	assert "Default to autonomous memory handling" in prompt.messages[0].content.text
	assert "Memory actions:" in prompt.messages[0].content.text
