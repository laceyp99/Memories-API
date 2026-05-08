import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.config import load_browser_client_config
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

logger = logging.getLogger(__name__)
browser_client_config = load_browser_client_config()


@asynccontextmanager
async def lifespan(_app: FastAPI):
	for warning_message in browser_client_config.warnings:
		logger.warning(warning_message)

	async with mcp.session_manager.run():
		yield


app = FastAPI(title="Memories API", lifespan=lifespan)
app.add_middleware(
	CORSMiddleware,
	allow_origins=browser_client_config.allowed_origins,
	allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
	allow_headers=[
		"Content-Type",
		"Accept",
		"MCP-Protocol-Version",
		"Mcp-Session-Id",
	],
	expose_headers=["Mcp-Session-Id"],
)


@app.middleware("http")
async def validate_mcp_browser_origin(request: Request, call_next):
	origin = request.headers.get("origin")
	if request.url.path.startswith("/mcp") and origin is not None:
		if origin not in browser_client_config.allowed_origins:
			return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})

	return await call_next(request)


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
