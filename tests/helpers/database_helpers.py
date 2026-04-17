import json
import sqlite3
from pathlib import Path


def read_database(data_file: Path) -> list[dict]:
	if not data_file.exists():
		return []

	with sqlite3.connect(data_file) as connection:
		connection.row_factory = sqlite3.Row
		rows = connection.execute(
			"""
			SELECT id, content, tags, created_at, updated_at, last_accessed_at, memory_type, status, version
			FROM memories
			ORDER BY id
			"""
		).fetchall()

	return [
		{
			"id": row["id"],
			"content": row["content"],
			"tags": json.loads(row["tags"]),
			"created_at": row["created_at"],
			"updated_at": row["updated_at"],
			"last_accessed_at": row["last_accessed_at"],
			"memory_type": row["memory_type"],
			"status": row["status"],
			"version": row["version"],
		}
		for row in rows
	]
