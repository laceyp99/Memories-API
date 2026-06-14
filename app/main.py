import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.requests import Request

from app.config import load_browser_client_config, load_safety_config
from app.mcp_server import mcp
from app.schemas import (
	DEFAULT_PAGE_LIMIT,
	MAX_BATCH_CREATE_MEMORIES,
	Memory,
	MemoryCreate,
	MemoryListQuery,
	MemoryListResponse,
	MemoryUpdate,
)
from app.storage import (
	MemoryWriteConflictError,
	create_memory,
	create_memory_batch,
	delete_memory,
	get_memories_page,
	get_memory,
	refresh_memories_last_accessed,
	update_memory,
)

logger = logging.getLogger(__name__)


def _query_validation_errors(error: ValidationError) -> list[dict]:
	errors: list[dict] = []
	for validation_error in error.errors():
		query_error = validation_error.copy()
		query_error["loc"] = ("query", *validation_error["loc"])
		if "ctx" in query_error and "error" in query_error["ctx"]:
			query_error["ctx"] = {
				**query_error["ctx"],
				"error": str(query_error["ctx"]["error"]),
			}
		errors.append(query_error)
	return errors


def build_memory_list_query(
	status: str | None = None,
	memory_type: str | None = None,
	tag: str | None = None,
	q: str | None = None,
	sort: str = "id",
	limit: int = DEFAULT_PAGE_LIMIT,
	offset: int = 0,
) -> MemoryListQuery:
	try:
		return MemoryListQuery(
			status=status,
			memory_type=memory_type,
			tag=tag,
			q=q,
			sort=sort,
			limit=limit,
			offset=offset,
		)
	except ValidationError as error:
		raise RequestValidationError(_query_validation_errors(error)) from error


def create_app() -> FastAPI:
	browser_client_config = load_browser_client_config()
	safety_config = load_safety_config()

	@asynccontextmanager
	async def lifespan(_app: FastAPI):
		for warning_message in browser_client_config.warnings:
			logger.warning(warning_message)
		for warning_message in safety_config.warnings:
			logger.warning(warning_message)

		async with mcp.session_manager.run():
			yield

	application = FastAPI(title="Memories API", lifespan=lifespan)
	application.state.browser_client_config = browser_client_config
	application.state.safety_config = safety_config
	application.add_middleware(
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

	@application.middleware("http")
	async def validate_mcp_browser_origin(request: Request, call_next):
		origin = request.headers.get("origin")
		if request.url.path.startswith("/mcp") and origin is not None:
			if origin not in browser_client_config.allowed_origins:
				return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})

		return await call_next(request)

	@application.post("/memories")
	def post_memory(memory: MemoryCreate) -> Memory:
		return create_memory(memory)

	@application.post("/memories/batch")
	def post_memory_batch(memories: list[MemoryCreate]) -> list[Memory]:
		if len(memories) > MAX_BATCH_CREATE_MEMORIES:
			raise HTTPException(
				status_code=422,
				detail=f"Batch create is limited to {MAX_BATCH_CREATE_MEMORIES} memories",
			)
		return create_memory_batch(memories)

	@application.get("/memories")
	def list_memories(
		query: Annotated[MemoryListQuery, Depends(build_memory_list_query)],
	) -> MemoryListResponse:
		paged_memories, total = get_memories_page(query)
		items = refresh_memories_last_accessed(paged_memories)

		return MemoryListResponse(
			items=items,
			total=total,
			limit=query.limit,
			offset=query.offset,
			has_more=query.offset + len(items) < total,
		)

	@application.get("/memories/{memory_id}")
	def get_memory_by_id(memory_id: int) -> Memory:
		memory = get_memory(memory_id)
		if memory is None:
			raise HTTPException(status_code=404, detail="Memory not found")
		return memory

	@application.patch("/memories/{memory_id}")
	def patch_memory_by_id(memory_id: int, memory: MemoryUpdate) -> Memory:
		try:
			updated_memory = update_memory(memory_id, memory)
		except MemoryWriteConflictError as error:
			raise HTTPException(
				status_code=409,
				detail="Memory was modified by another request",
			) from error

		if updated_memory is None:
			raise HTTPException(status_code=404, detail="Memory not found")
		return updated_memory

	@application.delete("/memories/{memory_id}")
	def delete_memory_by_id(memory_id: int) -> Memory:
		try:
			deleted_memory = delete_memory(memory_id)
		except MemoryWriteConflictError as error:
			raise HTTPException(
				status_code=409,
				detail="Memory was modified by another request",
			) from error

		if deleted_memory is None:
			raise HTTPException(status_code=404, detail="Memory not found")
		return deleted_memory

	application.mount("/mcp", mcp.streamable_http_app())

	return application


app = create_app()
