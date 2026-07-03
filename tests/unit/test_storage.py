import sqlite3

import pytest
from helpers.database_helpers import read_database

from app import storage
from app.schemas import MemoryCreate, MemoryListQuery, MemoryUpdate
from app.storage import (
	create_memory,
	delete_memory,
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


def test_get_memories_treats_free_text_like_wildcards_as_literals():
	create_memory(MemoryCreate(content="foo_bar", tags=["plain"]))
	create_memory(MemoryCreate(content="fooXbar", tags=["plain"]))
	create_memory(MemoryCreate(content="discount 10% today", tags=["sale"]))
	create_memory(MemoryCreate(content="discount 100 today", tags=["sale"]))
	create_memory(MemoryCreate(content="path C:\\Temp", tags=["windows"]))
	create_memory(MemoryCreate(content="path C:Temp", tags=["windows"]))

	underscore_results = get_memories(MemoryListQuery(q="foo_bar"))
	percent_results = get_memories(MemoryListQuery(q="10%"))
	backslash_results = get_memories(MemoryListQuery(q="c:\\temp"))

	assert [memory.id for memory in underscore_results] == [1]
	assert [memory.id for memory in percent_results] == [3]
	assert [memory.id for memory in backslash_results] == [5]


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


def test_update_memory_raises_conflict_when_row_changes_after_visible_read(data_file, monkeypatch):
	create_memory(MemoryCreate(content="Initial content", tags=["initial"]))
	original_fetch = storage._fetch_visible_memory_row
	did_concurrent_write = False

	def fetch_then_change_row(connection, memory_id):
		nonlocal did_concurrent_write

		row = original_fetch(connection, memory_id)
		if row is not None and not did_concurrent_write:
			did_concurrent_write = True
			with sqlite3.connect(data_file) as concurrent_connection:
				concurrent_connection.execute(
					"""
					UPDATE memories
					SET content = ?, updated_at = ?, version = ?
					WHERE id = ?
					""",
					(
						"Concurrent update",
						"2026-04-06T14:20:00.000000Z",
						row["version"] + 1,
						memory_id,
					),
				)
				concurrent_connection.commit()

		return row

	monkeypatch.setattr(storage, "_fetch_visible_memory_row", fetch_then_change_row)
	conflict_error = getattr(storage, "MemoryWriteConflictError", Exception)

	with pytest.raises(conflict_error):
		update_memory(1, MemoryUpdate(content="Stale update"))

	rows = read_database(data_file)
	assert rows == [
		{
			"id": 1,
			"content": "Concurrent update",
			"tags": ["initial"],
			"created_at": rows[0]["created_at"],
			"updated_at": "2026-04-06T14:20:00.000000Z",
			"last_accessed_at": None,
			"memory_type": "fact",
			"status": "active",
			"version": 2,
		}
	]


def test_delete_memory_raises_conflict_when_row_changes_after_visible_read(data_file, monkeypatch):
	create_memory(MemoryCreate(content="Initial content", tags=["initial"]))
	original_fetch = storage._fetch_visible_memory_row
	did_concurrent_write = False

	def fetch_then_change_row(connection, memory_id):
		nonlocal did_concurrent_write

		row = original_fetch(connection, memory_id)
		if row is not None and not did_concurrent_write:
			did_concurrent_write = True
			with sqlite3.connect(data_file) as concurrent_connection:
				concurrent_connection.execute(
					"""
					UPDATE memories
					SET content = ?, updated_at = ?, version = ?
					WHERE id = ?
					""",
					(
						"Concurrent update",
						"2026-04-06T14:20:00.000000Z",
						row["version"] + 1,
						memory_id,
					),
				)
				concurrent_connection.commit()

		return row

	monkeypatch.setattr(storage, "_fetch_visible_memory_row", fetch_then_change_row)
	conflict_error = getattr(storage, "MemoryWriteConflictError", Exception)

	with pytest.raises(conflict_error):
		delete_memory(1)

	rows = read_database(data_file)
	assert rows == [
		{
			"id": 1,
			"content": "Concurrent update",
			"tags": ["initial"],
			"created_at": rows[0]["created_at"],
			"updated_at": "2026-04-06T14:20:00.000000Z",
			"last_accessed_at": None,
			"memory_type": "fact",
			"status": "active",
			"version": 2,
		}
	]
