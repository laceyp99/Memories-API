from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from app.schemas import (
	Memory,
	MemoryCreate,
	MemoryListQuery,
	MemoryListResponse,
	MemoryUpdate,
)
from app.storage import (
	create_memory,
	create_memory_batch,
	delete_memory,
	get_memories,
	get_memory,
	update_memory,
)

app = FastAPI(title="Memories API")


def _sort_memories(memories: list[Memory], sort_key: str) -> list[Memory]:
	if sort_key == "id":
		return sorted(memories, key=lambda memory: memory.id)

	return sorted(
		memories,
		key=lambda memory: (
			getattr(memory, sort_key) is not None,
			getattr(memory, sort_key) or "",
			memory.id,
		),
		reverse=True,
	)


@app.post("/memories")
def post_memory(memory: MemoryCreate) -> Memory:
	return create_memory(memory)


@app.post("/memories/batch")
def post_memory_batch(memories: list[MemoryCreate]) -> list[Memory]:
	return create_memory_batch(memories)


@app.get("/memories")
def list_memories(query: Annotated[MemoryListQuery, Depends()]) -> MemoryListResponse:
	sorted_memories = _sort_memories(get_memories(query), query.sort)
	total = len(sorted_memories)
	paged_memories = sorted_memories[query.offset : query.offset + query.limit]
	items = [get_memory(memory.id) for memory in paged_memories]

	return MemoryListResponse(
		items=[memory for memory in items if memory is not None],
		total=total,
		limit=query.limit,
		offset=query.offset,
		has_more=query.offset + len(paged_memories) < total,
	)


@app.get("/memories/{memory_id}")
def get_memory_by_id(memory_id: int) -> Memory:
	memory = get_memory(memory_id)
	if memory is None:
		raise HTTPException(status_code=404, detail="Memory not found")
	return memory


@app.patch("/memories/{memory_id}")
def patch_memory_by_id(memory_id: int, memory: MemoryUpdate) -> Memory:
	updated_memory = update_memory(memory_id, memory)
	if updated_memory is None:
		raise HTTPException(status_code=404, detail="Memory not found")
	return updated_memory


@app.delete("/memories/{memory_id}")
def delete_memory_by_id(memory_id: int) -> Memory:
	deleted_memory = delete_memory(memory_id)
	if deleted_memory is None:
		raise HTTPException(status_code=404, detail="Memory not found")
	return deleted_memory
