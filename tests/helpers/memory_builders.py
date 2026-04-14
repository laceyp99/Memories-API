def expected_memory(
	memory_id: int,
	content: str,
	tags: list[str],
	*,
	created_at: str,
	updated_at: str,
	last_accessed_at: str | None,
	memory_type: str = "fact",
	status: str = "active",
	version: int = 1,
) -> dict:
	return {
		"id": memory_id,
		"content": content,
		"tags": tags,
		"created_at": created_at,
		"updated_at": updated_at,
		"last_accessed_at": last_accessed_at,
		"memory_type": memory_type,
		"status": status,
		"version": version,
	}
