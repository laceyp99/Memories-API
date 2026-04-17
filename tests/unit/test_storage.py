from app.schemas import MemoryCreate, MemoryUpdate
from app.storage import create_memory, search_memories, update_memory


def test_create_memory_assigns_incrementing_ids():
	first = create_memory(MemoryCreate(content="First memory", tags=["python"]))
	second = create_memory(MemoryCreate(content="Second memory", tags=["sql"]))

	assert first.id == 1
	assert second.id == 2


def test_search_memories_matches_content_and_tags_case_insensitively(monkeypatch):
	create_memory(MemoryCreate(content="Learning FastAPI testing", tags=["python", "api"]))
	create_memory(
		MemoryCreate(
			content="Database query notes",
			tags=["SQL"],
			memory_type="task_context",
		)
	)

	results = search_memories("sql")

	assert [memory.id for memory in results] == [2]


def test_update_memory_returns_existing_memory_without_refreshing_timestamp(monkeypatch):
	stored_item = create_memory(
		MemoryCreate(content="Learning FastAPI testing", tags=["python", "api"])
	)
	monkeypatch.setattr(
		"app.storage.current_timestamp",
		lambda: (_ for _ in ()).throw(AssertionError("current_timestamp should not be called")),
	)

	result = update_memory(
		1,
		MemoryUpdate(content="Learning FastAPI testing", tags=["python", "api"]),
	)

	assert result is not None
	assert result.model_dump() == stored_item.model_dump()


def test_update_memory_persists_changes(monkeypatch):
	create_memory(MemoryCreate(content="Learning FastAPI testing", tags=["python", "api"]))
	monkeypatch.setattr("app.storage.current_timestamp", lambda: "2026-04-06T14:30:00.000000Z")

	result = update_memory(1, MemoryUpdate(status="archived"))

	assert result is not None
	assert result.status == "archived"
	assert result.updated_at == "2026-04-06T14:30:00.000000Z"
	assert result.version == 2
