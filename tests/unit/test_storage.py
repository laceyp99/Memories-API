from app.schemas import MemoryCreate, MemoryListQuery, MemoryUpdate
from app.storage import create_memory, get_memories, search_memories, update_memory


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


def test_get_memories_applies_structured_filters_with_exact_tag_matching():
	create_memory(
		MemoryCreate(
			content="Learning FastAPI testing",
			tags=["python", "api"],
			memory_type="instruction",
		)
	)
	create_memory(
		MemoryCreate(
			content="Learning Python typing",
			tags=["pythonista", "typing"],
			memory_type="instruction",
		)
	)
	create_memory(
		MemoryCreate(
			content="Archived launch notes",
			tags=["python", "launch"],
			memory_type="task_context",
			status="archived",
		)
	)

	results = get_memories(
		MemoryListQuery(status="active", memory_type="instruction", tag="python")
	)

	assert [memory.id for memory in results] == [1]


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
