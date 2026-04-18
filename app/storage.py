import json
from datetime import UTC, datetime

from app.db import get_connection
from app.schemas import Memory, MemoryCreate, MemoryUpdate


def current_timestamp() -> str:
	return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _serialize_tags(tags: list[str]) -> str:
	return json.dumps(tags)


def _row_to_memory(row) -> Memory:
	return Memory(
		id=row["id"],
		content=row["content"],
		tags=json.loads(row["tags"]),
		created_at=row["created_at"],
		updated_at=row["updated_at"],
		last_accessed_at=row["last_accessed_at"],
		memory_type=row["memory_type"],
		status=row["status"],
		version=row["version"],
	)


def _fetch_memory_row(connection, memory_id: int):
	return connection.execute(
		"""
		SELECT id, content, tags, created_at, updated_at, last_accessed_at, memory_type, status, version
		FROM memories
		WHERE id = ?
		""",
		(memory_id,),
	).fetchone()


def create_memory(memory: MemoryCreate) -> Memory:
	timestamp = current_timestamp()
	with get_connection() as connection:
		cursor = connection.execute(
			"""
			INSERT INTO memories (
				content,
				tags,
				created_at,
				updated_at,
				last_accessed_at,
				memory_type,
				status,
				version
			)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				memory.content,
				_serialize_tags(memory.tags),
				timestamp,
				timestamp,
				None,
				memory.memory_type,
				memory.status,
				1,
			),
		)
		connection.commit()
		memory_id = cursor.lastrowid

	return Memory(
		id=memory_id,
		content=memory.content,
		tags=memory.tags,
		created_at=timestamp,
		updated_at=timestamp,
		last_accessed_at=None,
		memory_type=memory.memory_type,
		status=memory.status,
		version=1,
	)


def create_memory_batch(memories: list[MemoryCreate]) -> list[Memory]:
	created_memories: list[Memory] = []
	with get_connection() as connection:
		for memory in memories:
			timestamp = current_timestamp()
			cursor = connection.execute(
				"""
				INSERT INTO memories (
					content,
					tags,
					created_at,
					updated_at,
					last_accessed_at,
					memory_type,
					status,
					version
				)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?)
				""",
				(
					memory.content,
					_serialize_tags(memory.tags),
					timestamp,
					timestamp,
					None,
					memory.memory_type,
					memory.status,
					1,
				),
			)
			created_memories.append(
				Memory(
					id=cursor.lastrowid,
					content=memory.content,
					tags=memory.tags,
					created_at=timestamp,
					updated_at=timestamp,
					last_accessed_at=None,
					memory_type=memory.memory_type,
					status=memory.status,
					version=1,
				)
			)
		connection.commit()

	return created_memories


def get_memories() -> list[Memory]:
	with get_connection() as connection:
		rows = connection.execute(
			"""
			SELECT id, content, tags, created_at, updated_at, last_accessed_at, memory_type, status, version
			FROM memories
			ORDER BY id
			"""
		).fetchall()
	return [_row_to_memory(row) for row in rows]


def get_memory(memory_id: int) -> Memory | None:
	with get_connection() as connection:
		row = _fetch_memory_row(connection, memory_id)
		if row is None:
			return None

		last_accessed_at = current_timestamp()
		connection.execute(
			"UPDATE memories SET last_accessed_at = ? WHERE id = ?",
			(last_accessed_at, memory_id),
		)
		connection.commit()

		memory = _row_to_memory(row)
		return memory.model_copy(update={"last_accessed_at": last_accessed_at})


def update_memory(memory_id: int, memory: MemoryUpdate) -> Memory | None:
	update_data = memory.model_dump(exclude_unset=True)
	with get_connection() as connection:
		row = _fetch_memory_row(connection, memory_id)
		if row is None:
			return None

		existing_memory = _row_to_memory(row)
		has_changes = any(
			getattr(existing_memory, key) != value for key, value in update_data.items()
		)
		if not has_changes:
			return existing_memory

		updated_memory = existing_memory.model_copy(update=update_data)
		updated_at = current_timestamp()
		version = existing_memory.version + 1
		connection.execute(
			"""
			UPDATE memories
			SET content = ?, tags = ?, updated_at = ?, memory_type = ?, status = ?, version = ?
			WHERE id = ?
			""",
			(
				updated_memory.content,
				_serialize_tags(updated_memory.tags),
				updated_at,
				updated_memory.memory_type,
				updated_memory.status,
				version,
				memory_id,
			),
		)
		connection.commit()

		return updated_memory.model_copy(update={"updated_at": updated_at, "version": version})


def delete_memory(memory_id: int) -> Memory | None:
	with get_connection() as connection:
		row = _fetch_memory_row(connection, memory_id)
		if row is None:
			return None

		deleted_memory = _row_to_memory(row)
		connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
		connection.commit()
		return deleted_memory


def search_memories(query: str) -> list[Memory]:
	query_lower = query.lower()
	query_pattern = f"%{query_lower}%"
	with get_connection() as connection:
		rows = connection.execute(
			"""
			SELECT id, content, tags, created_at, updated_at, last_accessed_at, memory_type, status, version
			FROM memories
			WHERE LOWER(content) LIKE ? OR LOWER(tags) LIKE ?
			ORDER BY id
			""",
			(query_pattern, query_pattern),
		).fetchall()
	return [_row_to_memory(row) for row in rows]
