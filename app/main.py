from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from app.mcp_server import mcp
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
	get_memories_page,
	get_memory,
	refresh_memories_last_accessed,
	update_memory,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
	async with mcp.session_manager.run():
		yield


app = FastAPI(title="Memories API", lifespan=lifespan)


@app.post("/memories")
def post_memory(memory: MemoryCreate) -> Memory:
	return create_memory(memory)


@app.post("/memories/batch")
def post_memory_batch(memories: list[MemoryCreate]) -> list[Memory]:
	return create_memory_batch(memories)


@app.get("/memories")
def list_memories(query: Annotated[MemoryListQuery, Depends()]) -> MemoryListResponse:
	paged_memories, total = get_memories_page(query)
	items = refresh_memories_last_accessed(paged_memories)

	return MemoryListResponse(
		items=items,
		total=total,
		limit=query.limit,
		offset=query.offset,
		has_more=query.offset + len(items) < total,
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


app.mount("/mcp", mcp.streamable_http_app())
