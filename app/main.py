import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.requests import Request

from app.config import load_browser_client_config, load_safety_config
from app.db import check_database_readiness, init_db
from app.mcp_server import mcp
from app.request_context import REQUEST_ID_HEADER, resolve_request_id, set_request_id_header
from app.request_limits import (
	FixedWindowRateLimiter,
	reject_request_body_if_too_large,
	reject_request_if_rate_limited,
	reject_request_stream_if_too_large,
)
from app.request_logging import current_duration_ms, log_http_request
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

		init_db()

		async with mcp.session_manager.run():
			yield

	application = FastAPI(title="Memories API", lifespan=lifespan)
	application.state.browser_client_config = browser_client_config
	application.state.safety_config = safety_config
	application.state.rate_limiter = FixedWindowRateLimiter()

	@application.exception_handler(Exception)
	async def unhandled_exception_response(request: Request, _error: Exception) -> JSONResponse:
		request_id = getattr(
			request.state,
			"request_id",
			resolve_request_id(request.headers.get(REQUEST_ID_HEADER)),
		)
		return set_request_id_header(
			JSONResponse(status_code=500, content={"detail": "Internal Server Error"}),
			request_id,
		)

	application.add_middleware(
		CORSMiddleware,
		allow_origins=browser_client_config.allowed_origins,
		allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
		allow_headers=[
			"Content-Type",
			"Accept",
			"MCP-Protocol-Version",
			"Mcp-Session-Id",
			"X-Client-Id",
			REQUEST_ID_HEADER,
		],
		expose_headers=[
			"Mcp-Session-Id",
			"Retry-After",
			"X-RateLimit-Limit",
			"X-RateLimit-Remaining",
			"X-RateLimit-Reset",
			"X-Request-Body-Limit",
			REQUEST_ID_HEADER,
		],
	)

	@application.middleware("http")
	async def enforce_request_safety(request: Request, call_next):
		start_time = time.perf_counter()
		request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
		request.state.request_id = request_id

		def complete_response(response):
			log_http_request(
				logger,
				request,
				status_code=response.status_code,
				duration_ms=current_duration_ms(start_time),
				request_id=request_id,
			)
			return set_request_id_header(response, request_id)

		origin = request.headers.get("origin")
		if request.url.path.startswith("/mcp") and origin is not None:
			if origin not in browser_client_config.allowed_origins:
				return complete_response(
					JSONResponse(status_code=403, content={"detail": "Origin not allowed"}),
				)

		rate_limit_response = reject_request_if_rate_limited(
			request,
			application.state.rate_limiter,
			safety_config,
		)
		if rate_limit_response is not None:
			return complete_response(rate_limit_response)

		body_limit_response = reject_request_body_if_too_large(
			request,
			safety_config.request_body_max_bytes,
		)
		if body_limit_response is not None:
			return complete_response(body_limit_response)

		body_limit_response = await reject_request_stream_if_too_large(
			request,
			safety_config.request_body_max_bytes,
		)
		if body_limit_response is not None:
			return complete_response(body_limit_response)

		try:
			response = await call_next(request)
		except Exception:
			log_http_request(
				logger,
				request,
				status_code=500,
				duration_ms=current_duration_ms(start_time),
				request_id=request_id,
			)
			raise

		return complete_response(response)

	@application.get("/health")
	def health_check() -> dict[str, str]:
		return {"status": "ok"}

	@application.get("/ready")
	def readiness_check():
		checks = check_database_readiness()
		if all(status == "ok" for status in checks.values()):
			return {"status": "ready", "checks": checks}

		return JSONResponse(
			status_code=503,
			content={"status": "not_ready", "checks": checks},
		)

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
