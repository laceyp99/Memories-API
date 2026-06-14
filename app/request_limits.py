from fastapi.responses import JSONResponse
from starlette.requests import Request

BODY_LIMITED_METHODS = {"POST", "PATCH"}
REQUEST_BODY_LIMIT_HEADER = "X-Request-Body-Limit"


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
