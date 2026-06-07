import json
from datetime import UTC, datetime

from app.db import get_connection
from app.schemas import Memory, MemoryCreate, MemoryListQuery, MemoryUpdate

MEMORY_SORT_COLUMNS = {
	"id": "id",
	"created_at": "created_at",
	"updated_at": "updated_at",
	"last_accessed_at": "last_accessed_at",
}


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


def _fetch_visible_memory_row(connection, memory_id: int):
	return connection.execute(
		"""
		SELECT id, content, tags, created_at, updated_at, last_accessed_at, memory_type, status, version
		FROM memories
		WHERE id = ? AND status != 'deleted'
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


def _build_memory_filters(query: MemoryListQuery | None) -> tuple[str, list[object]]:
	clauses: list[str] = []
	parameters: list[object] = []

	if query is None or query.status is None:
		clauses.append("status != ?")
		parameters.append("deleted")
	else:
		clauses.append("status = ?")
		parameters.append(query.status)

	if query is not None and query.memory_type is not None:
		clauses.append("memory_type = ?")
		parameters.append(query.memory_type)

	if query is not None and query.tag is not None:
		clauses.append("EXISTS (SELECT 1 FROM json_each(memories.tags) WHERE json_each.value = ?)")
		parameters.append(query.tag)

	if query is not None and query.q is not None:
		query_pattern = f"%{query.q.lower()}%"
		clauses.append("(LOWER(content) LIKE ? OR LOWER(tags) LIKE ?)")
		parameters.extend([query_pattern, query_pattern])

	return "WHERE " + " AND ".join(clauses), parameters


def _build_memory_order_by(sort_key: str) -> str:
	column = MEMORY_SORT_COLUMNS[sort_key]
	if sort_key == "id":
		return f"ORDER BY {column} ASC"

	return f"ORDER BY {column} DESC, id DESC"


def _query_memories(query: MemoryListQuery | None = None) -> list[Memory]:
	where_clause, parameters = _build_memory_filters(query)

	with get_connection() as connection:
		rows = connection.execute(
			f"""
			SELECT id, content, tags, created_at, updated_at, last_accessed_at, memory_type, status, version
			FROM memories
			{where_clause}
			ORDER BY id
			""",
			parameters,
		).fetchall()
	return [_row_to_memory(row) for row in rows]


def get_memories_page(query: MemoryListQuery) -> tuple[list[Memory], int]:
	where_clause, parameters = _build_memory_filters(query)
	order_by_clause = _build_memory_order_by(query.sort)
	paging_parameters = [*parameters, query.limit, query.offset]

	with get_connection() as connection:
		connection.execute("BEGIN")
		total = connection.execute(
			f"SELECT COUNT(*) FROM memories {where_clause}",
			parameters,
		).fetchone()[0]
		rows = connection.execute(
			f"""
			SELECT id, content, tags, created_at, updated_at, last_accessed_at, memory_type, status, version
			FROM memories
			{where_clause}
			{order_by_clause}
			LIMIT ? OFFSET ?
			""",
			paging_parameters,
		).fetchall()
		connection.commit()

	return [_row_to_memory(row) for row in rows], total


def get_memories(query: MemoryListQuery | None = None) -> list[Memory]:
	return _query_memories(query)


def refresh_memories_last_accessed(memories: list[Memory]) -> list[Memory]:
	if not memories:
		return memories

	last_accessed_at = current_timestamp()
	memory_ids = [memory.id for memory in memories]
	placeholders = ", ".join("?" for _ in memory_ids)

	with get_connection() as connection:
		connection.execute(
			f"UPDATE memories SET last_accessed_at = ? WHERE id IN ({placeholders})",
			[last_accessed_at, *memory_ids],
		)
		connection.commit()

	return [memory.model_copy(update={"last_accessed_at": last_accessed_at}) for memory in memories]


def get_memory(memory_id: int) -> Memory | None:
	with get_connection() as connection:
		row = _fetch_visible_memory_row(connection, memory_id)
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
		row = _fetch_visible_memory_row(connection, memory_id)
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
		row = _fetch_visible_memory_row(connection, memory_id)
		if row is None:
			return None

		existing_memory = _row_to_memory(row)
		updated_at = current_timestamp()
		version = existing_memory.version + 1
		connection.execute(
			"""
			UPDATE memories
			SET status = ?, updated_at = ?, version = ?
			WHERE id = ?
			""",
			("deleted", updated_at, version, memory_id),
		)
		connection.commit()
		return existing_memory.model_copy(
			update={"status": "deleted", "updated_at": updated_at, "version": version}
		)
