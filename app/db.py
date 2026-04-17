import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import get_database_file_path

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


def init_db() -> None:
	database_file = get_database_file_path()
	database_file.parent.mkdir(parents=True, exist_ok=True)
	with sqlite3.connect(database_file) as connection:
		connection.execute(SCHEMA_SQL)
		connection.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
	init_db()
	connection = sqlite3.connect(get_database_file_path())
	connection.row_factory = sqlite3.Row
	try:
		yield connection
	finally:
		connection.close()
