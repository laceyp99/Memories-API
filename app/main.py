from fastapi import FastAPI, HTTPException

from app.schemas import Memory, MemoryCreate, MemoryUpdate
from app.storage import (
	create_memory,
	create_memory_batch,
	delete_memory,
	get_memories,
	get_memory,
	search_memories,
	update_memory,
)

app = FastAPI(title="Memories API")


@app.post("/memories")
def post_memory(memory: MemoryCreate) -> Memory:
	return create_memory(memory)


@app.post("/memories/batch")
def post_memory_batch(memories: list[MemoryCreate]) -> list[Memory]:
	return create_memory_batch(memories)


@app.get("/memories")
def list_memories() -> list[Memory]:
	return get_memories()


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


@app.get("/search")
def search_memory_endpoint(query: str) -> list[Memory]:
	return search_memories(query)
