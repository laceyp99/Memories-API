import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import get_database_file_path

SQLITE_BUSY_TIMEOUT_SECONDS = 5.0
SQLITE_BUSY_TIMEOUT_MS = 5000

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memories (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	content TEXT NOT NULL,
	tags TEXT NOT NULL,
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	last_accessed_at TEXT,
	memory_type TEXT NOT NULL,
	status TEXT NOT NULL,
	version INTEGER NOT NULL
)
"""

INDEX_SQL = [
	"""
	CREATE INDEX IF NOT EXISTS idx_memories_status_memory_type_updated_at_id
	ON memories (status, memory_type, updated_at DESC, id DESC)
	""",
	"CREATE INDEX IF NOT EXISTS idx_memories_status ON memories (status)",
	"CREATE INDEX IF NOT EXISTS idx_memories_memory_type ON memories (memory_type)",
	"CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories (created_at)",
	"CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories (updated_at)",
	"CREATE INDEX IF NOT EXISTS idx_memories_last_accessed_at ON memories (last_accessed_at)",
]


def _connect_database() -> sqlite3.Connection:
	connection = sqlite3.connect(
		get_database_file_path(),
		timeout=SQLITE_BUSY_TIMEOUT_SECONDS,
	)
	connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
	return connection


def init_db() -> None:
	database_file = get_database_file_path()
	database_file.parent.mkdir(parents=True, exist_ok=True)
	with _connect_database() as connection:
		connection.execute(SCHEMA_SQL)
		for index_sql in INDEX_SQL:
			connection.execute(index_sql)
		connection.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
	init_db()
	connection = _connect_database()
	connection.row_factory = sqlite3.Row
	try:
		yield connection
	finally:
		connection.close()
