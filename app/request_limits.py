import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.config import SafetyConfig

BODY_LIMITED_METHODS = {"POST", "PATCH"}
REQUEST_BODY_LIMIT_HEADER = "X-Request-Body-Limit"
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_CLIENT_ID_HEADER = "X-Client-Id"
RATE_LIMIT_CLIENT_ID_MAX_CHARS = 128


@dataclass(frozen=True)
class RateLimitBucket:
	name: str
	limit: int


@dataclass(frozen=True)
class RateLimitDecision:
	allowed: bool
	limit: int
	remaining: int
	reset_epoch: int
	retry_after_seconds: int


@dataclass
class _RateLimitWindow:
	count: int
	reset_monotonic: float
	reset_epoch: int


def request_body_limit_applies(request: Request) -> bool:
	if request.method.upper() not in BODY_LIMITED_METHODS:
		return False

	path = request.url.path
	return path == "/memories" or path.startswith("/memories/") or path.startswith("/mcp")


def declared_content_length(request: Request) -> int | None:
	header_value = request.headers.get("content-length")
	if header_value is None:
		return None

	try:
		content_length = int(header_value)
	except ValueError:
		return None

	if content_length < 0:
		return None

	return content_length


def reject_request_body_if_too_large(request: Request, max_body_bytes: int) -> JSONResponse | None:
	content_length = declared_content_length(request)
	if (
		content_length is not None
		and request_body_limit_applies(request)
		and content_length > max_body_bytes
	):
		return JSONResponse(
			status_code=413,
			content={"detail": "Request body too large"},
			headers={REQUEST_BODY_LIMIT_HEADER: str(max_body_bytes)},
		)

	return None


class FixedWindowRateLimiter:
	def __init__(
		self,
		*,
		monotonic_clock: Callable[[], float] = time.monotonic,
		wall_clock: Callable[[], float] = time.time,
	) -> None:
		self._monotonic_clock = monotonic_clock
		self._wall_clock = wall_clock
		self._windows: dict[tuple[str, str], _RateLimitWindow] = {}

	def check(self, *, identity: str, bucket: str, limit: int) -> RateLimitDecision:
		now = self._monotonic_clock()
		self._prune_expired_windows(now)

		key = (identity, bucket)
		window = self._windows.get(key)
		if window is None:
			window = _RateLimitWindow(
				count=0,
				reset_monotonic=now + RATE_LIMIT_WINDOW_SECONDS,
				reset_epoch=math.ceil(self._wall_clock() + RATE_LIMIT_WINDOW_SECONDS),
			)
			self._windows[key] = window

		retry_after_seconds = max(1, math.ceil(window.reset_monotonic - now))
		if window.count >= limit:
			return RateLimitDecision(
				allowed=False,
				limit=limit,
				remaining=0,
				reset_epoch=window.reset_epoch,
				retry_after_seconds=retry_after_seconds,
			)

		window.count += 1
		return RateLimitDecision(
			allowed=True,
			limit=limit,
			remaining=max(0, limit - window.count),
			reset_epoch=window.reset_epoch,
			retry_after_seconds=retry_after_seconds,
		)

	def _prune_expired_windows(self, now: float) -> None:
		expired_keys = [
			key for key, window in self._windows.items() if window.reset_monotonic <= now
		]
		for key in expired_keys:
			del self._windows[key]


def rate_limit_identity(request: Request) -> str:
	client_id = request.headers.get(RATE_LIMIT_CLIENT_ID_HEADER)
	if client_id is not None:
		normalized_client_id = client_id.strip()
		if normalized_client_id:
			return normalized_client_id[:RATE_LIMIT_CLIENT_ID_MAX_CHARS]

	if request.client is not None and request.client.host:
		return request.client.host

	return "unknown"


def classify_rate_limit_bucket(
	request: Request,
	safety_config: SafetyConfig,
) -> RateLimitBucket | None:
	method = request.method.upper()
	if method in {"HEAD", "OPTIONS"}:
		return None

	path = request.url.path
	if path.startswith("/mcp"):
		return RateLimitBucket("mcp", safety_config.rate_limit_mcp_per_minute)

	if method == "GET":
		if path == "/memories" or path.startswith("/memories/"):
			return RateLimitBucket("reads", safety_config.rate_limit_reads_per_minute)
		return None

	if method == "POST":
		if path == "/memories/batch":
			return RateLimitBucket("batch", safety_config.rate_limit_batch_per_minute)
		if path == "/memories":
			return RateLimitBucket("writes", safety_config.rate_limit_writes_per_minute)
		return None

	if method in {"PATCH", "DELETE"} and path.startswith("/memories/"):
		return RateLimitBucket("writes", safety_config.rate_limit_writes_per_minute)

	return None


def reject_request_if_rate_limited(
	request: Request,
	limiter: FixedWindowRateLimiter,
	safety_config: SafetyConfig,
) -> JSONResponse | None:
	if not safety_config.rate_limiting_enabled:
		return None

	bucket = classify_rate_limit_bucket(request, safety_config)
	if bucket is None:
		return None

	decision = limiter.check(
		identity=rate_limit_identity(request),
		bucket=bucket.name,
		limit=bucket.limit,
	)
	if decision.allowed:
		return None

	return JSONResponse(
		status_code=429,
		content={"detail": "Rate limit exceeded"},
		headers={
			"Retry-After": str(decision.retry_after_seconds),
			"X-RateLimit-Limit": str(decision.limit),
			"X-RateLimit-Remaining": str(decision.remaining),
			"X-RateLimit-Reset": str(decision.reset_epoch),
		},
	)
