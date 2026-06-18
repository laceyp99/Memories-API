import json
import logging
import time

from starlette.requests import Request

OPERATIONAL_PATHS = {"/health", "/ready"}


def current_duration_ms(start_time: float) -> float:
	return round((time.perf_counter() - start_time) * 1000, 3)


def log_http_request(
	logger: logging.Logger,
	request: Request,
	*,
	status_code: int,
	duration_ms: float,
	request_id: str,
) -> None:
	payload = {
		"method": request.method,
		"path": request.url.path,
		"status": status_code,
		"duration_ms": duration_ms,
		"request_id": request_id,
	}
	level = logging.DEBUG if request.url.path in OPERATIONAL_PATHS else logging.INFO
	logger.log(level, json.dumps(payload, separators=(",", ":")))
