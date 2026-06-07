from app.schemas import MemoryCreate, MemoryListQuery, MemoryUpdate
from app.storage import (
	create_memory,
	get_memories,
	get_memories_page,
	update_memory,
)


def test_create_memory_assigns_incrementing_ids():
	first = create_memory(MemoryCreate(content="First memory", tags=["python"]))
	second = create_memory(MemoryCreate(content="Second memory", tags=["sql"]))

	assert first.id == 1
	assert second.id == 2


def test_get_memories_applies_free_text_filter_case_insensitively():
	create_memory(MemoryCreate(content="Learning FastAPI testing", tags=["python", "api"]))
	create_memory(
		MemoryCreate(
			content="Database query notes",
			tags=["SQL"],
			memory_type="event",
		)
	)

	results = get_memories(MemoryListQuery(q="sql"))

	assert [memory.id for memory in results] == [2]


def test_get_memories_applies_structured_filters_with_exact_tag_matching():
	create_memory(
		MemoryCreate(
			content="Learning FastAPI testing",
			tags=["python", "api"],
			memory_type="identity",
		)
	)
	create_memory(
		MemoryCreate(
			content="Learning Python typing",
			tags=["pythonista", "typing"],
			memory_type="identity",
		)
	)
	create_memory(
		MemoryCreate(
			content="Launch notes marked invalid",
			tags=["python", "launch"],
			memory_type="event",
			status="invalid",
		)
	)

	results = get_memories(MemoryListQuery(status="active", memory_type="identity", tag="python"))

	assert [memory.id for memory in results] == [1]


def test_get_memories_excludes_deleted_by_default_but_allows_explicit_deleted_filter():
	create_memory(MemoryCreate(content="Visible memory", tags=["active"]))
	create_memory(MemoryCreate(content="Hidden memory", tags=["deleted"], status="deleted"))

	default_results = get_memories()
	deleted_results = get_memories(MemoryListQuery(status="deleted"))

	assert [memory.id for memory in default_results] == [1]
	assert [memory.id for memory in deleted_results] == [2]


def test_get_memories_page_sorts_by_created_at_with_stable_id_tiebreaker(monkeypatch):
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:13:00.000000Z",
		]
	)
	monkeypatch.setattr("app.storage.current_timestamp", lambda: next(timestamps))

	for content in ["First", "Second", "Third"]:
		create_memory(MemoryCreate(content=content, tags=[content.lower()]))

	items, total = get_memories_page(MemoryListQuery(sort="created_at", limit=2, offset=0))

	assert total == 3
	assert [memory.id for memory in items] == [3, 2]


def test_get_memories_page_sorts_by_last_accessed_at_and_counts_full_result(monkeypatch):
	timestamps = iter(
		[
			"2026-04-06T14:12:00.000000Z",
			"2026-04-06T14:13:00.000000Z",
			"2026-04-06T14:14:00.000000Z",
			"2026-04-06T14:30:00.000000Z",
			"2026-04-06T14:30:00.000000Z",
		]
	)
	monkeypatch.setattr("app.storage.current_timestamp", lambda: next(timestamps))

	for content in ["First", "Second", "Third"]:
		create_memory(MemoryCreate(content=content, tags=[content.lower()]))

	assert update_memory(1, MemoryUpdate(status="invalid")) is not None
	assert update_memory(2, MemoryUpdate(status="invalid")) is not None

	items, total = get_memories_page(MemoryListQuery(sort="updated_at", limit=2, offset=0))

	assert total == 3
	assert [memory.id for memory in items] == [2, 1]


def test_get_memories_page_reads_count_and_rows_in_one_transaction(monkeypatch):
	executed_statements: list[str] = []

	class FakeResult:
		def __init__(self, *, one=None, all_rows=None):
			self._one = one
			self._all_rows = all_rows or []

		def fetchone(self):
			return self._one

		def fetchall(self):
			return self._all_rows

	class FakeConnection:
		def execute(self, sql, parameters=()):
			normalized_sql = " ".join(sql.split()).upper()

			if normalized_sql == "BEGIN":
				executed_statements.append("BEGIN")
				return FakeResult()

			if "SELECT COUNT(*) FROM MEMORIES" in normalized_sql:
				executed_statements.append("COUNT")
				return FakeResult(one=(0,))

			if "SELECT ID, CONTENT, TAGS" in normalized_sql:
				executed_statements.append("PAGE")
				return FakeResult(all_rows=[])

			raise AssertionError(f"Unexpected SQL: {sql}")

		def commit(self):
			executed_statements.append("COMMIT")

	class FakeConnectionContext:
		def __enter__(self):
			return FakeConnection()

		def __exit__(self, _exc_type, _exc_value, _traceback):
			return False

	monkeypatch.setattr("app.storage.get_connection", lambda: FakeConnectionContext())

	items, total = get_memories_page(MemoryListQuery(limit=2, offset=0))

	assert items == []
	assert total == 0
	assert executed_statements == ["BEGIN", "COUNT", "PAGE", "COMMIT"]


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

	result = update_memory(1, MemoryUpdate(status="invalid"))

	assert result is not None
	assert result.status == "invalid"
	assert result.updated_at == "2026-04-06T14:30:00.000000Z"
	assert result.version == 2
