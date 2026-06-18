import re
from uuid import uuid4

from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-Id"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def resolve_request_id(header_value: str | None) -> str:
	if header_value is not None and REQUEST_ID_PATTERN.fullmatch(header_value):
		return header_value

	return str(uuid4())


def set_request_id_header(response: Response, request_id: str) -> Response:
	response.headers[REQUEST_ID_HEADER] = request_id
	return response
