import sqlite3
from pathlib import Path

from app.db import SQLITE_BUSY_TIMEOUT_MS, get_connection, init_db

EXPECTED_COLUMNS = [
	("id", "INTEGER", 0, 1),
	("content", "TEXT", 1, 0),
	("tags", "TEXT", 1, 0),
	("created_at", "TEXT", 1, 0),
	("updated_at", "TEXT", 1, 0),
	("last_accessed_at", "TEXT", 0, 0),
	("memory_type", "TEXT", 1, 0),
	("status", "TEXT", 1, 0),
	("version", "INTEGER", 1, 0),
]

EXPECTED_INDEXES = {
	"idx_memories_status_memory_type_updated_at_id": [
		("status", 0),
		("memory_type", 0),
		("updated_at", 1),
		("id", 1),
	],
	"idx_memories_status": [("status", 0)],
	"idx_memories_memory_type": [("memory_type", 0)],
	"idx_memories_created_at": [("created_at", 0)],
	"idx_memories_updated_at": [("updated_at", 0)],
	"idx_memories_last_accessed_at": [("last_accessed_at", 0)],
}


def _read_table_columns(database_file: Path) -> list[tuple[str, str, int, int]]:
	with sqlite3.connect(database_file) as connection:
		rows = connection.execute("PRAGMA table_info(memories)").fetchall()

	return [(row[1], row[2], row[3], row[5]) for row in rows]


def _read_index_columns(database_file: Path, index_name: str) -> list[tuple[str, int]]:
	with sqlite3.connect(database_file) as connection:
		rows = connection.execute(f"PRAGMA index_xinfo({index_name})").fetchall()

	return [(row[2], row[3]) for row in rows if row[5]]


def test_init_db_creates_memories_table_and_expected_indexes(data_file):
	init_db()

	assert _read_table_columns(data_file) == EXPECTED_COLUMNS

	with sqlite3.connect(data_file) as connection:
		index_names = {row[1] for row in connection.execute("PRAGMA index_list(memories)")}

	assert EXPECTED_INDEXES.keys() <= index_names
	for index_name, expected_columns in EXPECTED_INDEXES.items():
		assert _read_index_columns(data_file, index_name) == expected_columns


def test_get_connection_sets_busy_timeout():
	with get_connection() as connection:
		busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]

	assert busy_timeout == SQLITE_BUSY_TIMEOUT_MS


def test_get_connection_initializes_each_database_file_path(monkeypatch, tmp_path):
	first_database = tmp_path / "first.db"
	second_database = tmp_path / "second.db"

	monkeypatch.setenv("MEMORIES_DB_FILE", str(first_database))
	with get_connection() as connection:
		first_count = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

	monkeypatch.setenv("MEMORIES_DB_FILE", str(second_database))
	with get_connection() as connection:
		second_count = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

	assert first_count == 0
	assert second_count == 0
	assert _read_table_columns(first_database) == EXPECTED_COLUMNS
	assert _read_table_columns(second_database) == EXPECTED_COLUMNS
