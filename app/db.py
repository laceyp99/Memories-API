import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from app.config import get_database_file_path

SQLITE_BUSY_TIMEOUT_SECONDS = 5.0
SQLITE_BUSY_TIMEOUT_MS = 5000
_INITIALIZED_DATABASE_FILES: set[Path] = set()
_INITIALIZED_DATABASE_FILES_LOCK = Lock()

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


def _database_key(database_file: Path) -> Path:
	return database_file.expanduser().resolve()


def _connect_database(database_file: Path) -> sqlite3.Connection:
	connection = sqlite3.connect(
		database_file,
		timeout=SQLITE_BUSY_TIMEOUT_SECONDS,
	)
	connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
	return connection


def _initialize_database(database_file: Path) -> None:
	database_file.parent.mkdir(parents=True, exist_ok=True)
	with _connect_database(database_file) as connection:
		connection.execute(SCHEMA_SQL)
		for index_sql in INDEX_SQL:
			connection.execute(index_sql)
		connection.commit()


def init_db() -> None:
	database_file = get_database_file_path()
	database_key = _database_key(database_file)
	with _INITIALIZED_DATABASE_FILES_LOCK:
		_initialize_database(database_file)
		_INITIALIZED_DATABASE_FILES.add(database_key)


def _ensure_db_initialized(database_file: Path) -> None:
	database_key = _database_key(database_file)
	if database_key in _INITIALIZED_DATABASE_FILES and database_file.exists():
		return

	with _INITIALIZED_DATABASE_FILES_LOCK:
		if database_key in _INITIALIZED_DATABASE_FILES and database_file.exists():
			return
		_initialize_database(database_file)
		_INITIALIZED_DATABASE_FILES.add(database_key)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
	database_file = get_database_file_path()
	_ensure_db_initialized(database_file)
	connection = _connect_database(database_file)
	connection.row_factory = sqlite3.Row
	try:
		yield connection
	finally:
		connection.close()
