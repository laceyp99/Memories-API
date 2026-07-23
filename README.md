# Memories API

Memories API is a local FastAPI and MCP service for shared memory across chatbots and agents. It gives every client one SQLite-backed source of truth for preferences, facts, identity notes, and event history, so memory written by one tool is immediately available to the next instead of living in separate per-agent silos. That keeps long-running conversations consistent and makes recall behavior easier to inspect and reason about.

## Usage

### Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install .
```

### Run the API

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive docs are available at http://127.0.0.1:8000/docs

The running app exposes:

- REST API at `http://127.0.0.1:8000/memories`
- Health endpoint at `http://127.0.0.1:8000/health`
- Readiness endpoint at `http://127.0.0.1:8000/ready`
- MCP streamable HTTP endpoint at `http://127.0.0.1:8000/mcp`
- MCP stdio entrypoint with `python -m app.mcp_server`

### Core memory model

The API and MCP server share the same server-managed memory shape. See [docs/data_object_schema.md](docs/data_object_schema.md) for the full schema.

The main fields and lifecycle rules are:

- `content` and `tags` are required when creating a memory.
- `memory_type` defaults to `fact` and `status` defaults to `active`.
- `id`, `created_at`, `updated_at`, `last_accessed_at`, and `version` are managed by the server.
- Allowed `memory_type` values are `preference`, `fact`, `identity`, and `event`.
- Allowed `status` values are `active`, `invalid`, and `deleted`.
- `POST /memories/batch` is all-or-nothing when validation fails.
- `PATCH` only changes `updated_at` and `version` when an editable field actually changes.
- `DELETE /memories/{id}` is a soft delete that marks the row as `deleted`.

### Try it out with HTTP

The REST API is available at http://127.0.0.1:8000/memories.

```bash
curl http://127.0.0.1:8000/memories
```

Use the [interactive docs](http://127.0.0.1:8000/docs) to create, update, delete, and filter memories.

### Try it out with MCP

The MCP server includes record, inspect, revise, retire, bootstrap, and search tools.

For prompt and resource design details, see [docs/mcp_prompt_skill_design.md](docs/mcp_prompt_skill_design.md).

#### MCP Inspector

For local debugging, start the MCP Inspector:
```
mcp dev app/mcp_server.py
```

Interactive MCP Inspector available at `http://localhost:6274`.

#### Stdio MCP clients

Add to your claude_desktop_config.json or mcp-config.json file:

```
{
	"mcpServers": {
		"memories-api": {
			"command": "python",
			"args": ["-m", "app.mcp_server"],
			"cwd": "path\to\Memories API",
			"env": {
		"MEMORIES_DB_FILE": "path\to\Memories API\data.db"
			}
		}
	}
}
```

#### Streamable HTTP MCP clients

Point the client at:

```text
http://127.0.0.1:8000/mcp
```

If the client application runs in Docker on the same machine, use the host-reachable URL that the container can resolve, for example:

```text
http://host.docker.internal:8000/mcp
```

#### Browser-based MCP clients

The repo includes a committed example file:

- `mcp_browser_clients.example.json`

Create your real local override file in the repo root:

- `mcp_browser_clients.local.json`

That local override file is gitignored and is the only file read by the app for browser-origin allowlisting.

If `mcp_browser_clients.local.json` does not exist, browser-based MCP access is denied by default, but the REST API and stdio MCP server still work.

Example local file for Open WebUI running in the browser at `http://localhost:3000`:

```json
{
	"browser_clients": [
		{
			"name": "open-webui-local",
			"origin": "http://localhost:3000"
		}
	]
}
```

If the local file exists but is invalid, the app logs a warning and denies browser-based MCP access instead of failing startup.

For a local Open WebUI setup, two values matter:

- Browser origin: usually `http://localhost:3000`. This is what goes into `mcp_browser_clients.local.json`.
- MCP server URL: if Open WebUI runs in Docker, it may need `http://host.docker.internal:8000/mcp` instead of `http://localhost:8000/mcp` to reach the host machine.

## Retrieval contract

HTTP and MCP expose one deterministic retrieval contract.

- HTTP uses `GET /memories`.
- MCP uses `prime_memory_context` for startup recall and `search_memories` for targeted recall.
- Both accept `status`, `memory_type`, `tag`, `q`, `sort`, `limit`, and `offset`.
- Both return `items`, `total`, `limit`, `offset`, and `has_more`.
- `tag` matches exactly.
- `q` is case-insensitive lexical matching over `content` and tags, not semantic search; `%`, `_`, and `\` are treated as literal characters.
- Filters compose with `AND`.
- Sort keys are `id`, `created_at`, `updated_at`, and `last_accessed_at`; timestamp sorts are descending with `id DESC` as a tie-breaker.
- `last_accessed_at` is refreshed only for rows actually returned by `GET /memories/{id}`, `GET /memories`, `search_memories`, and `prime_memory_context`.

That keeps retrieval easy to test and consistent across HTTP and MCP.

### Operational endpoints and request IDs

The API includes lightweight local operational endpoints:

- `GET /health` returns `{"status": "ok"}` as a side-effect-free ping. It does not read memories or refresh `last_accessed_at`.
- `GET /ready` checks that SQLite is reachable and the `memories` table exists. It may initialize the local DB/schema on first run, but it does not create, read, or update memory rows.

Readiness responses include non-sensitive check status only. A ready response returns:

```json
{
	"status": "ready",
	"checks": {
		"database": "ok",
		"memories_table": "ok"
	}
}
```

If a readiness check fails, the endpoint returns `503` with `status` set to `not_ready` and failed checks marked as `failed`. Responses do not include local database paths, raw exception text, or environment-derived file locations.

Every HTTP response includes `X-Request-Id`, including REST responses, MCP streamable HTTP responses, and middleware-generated rejections such as `413`, `429`, and MCP-origin `403`. If a request sends `X-Request-Id` and it matches `^[A-Za-z0-9._:-]{1,128}$`, the server echoes it. Missing or invalid values are replaced with a server-generated UUID.

The app emits one JSON request log record per HTTP request. Normal REST and MCP HTTP requests are logged at `INFO`; `/health` and `/ready` are logged at `DEBUG` to keep probe traffic quieter. Request log records contain only:

```json
{
	"method": "GET",
	"path": "/memories",
	"status": 200,
	"duration_ms": 1.23,
	"request_id": "example-request-id"
}
```

### Local safety limits

The HTTP API and MCP streamable HTTP endpoint include conservative local safety limits by default. These are intended to protect a single-user local service from runaway agents, oversized payloads, and accidental request floods. They are not a substitute for authentication or transport security.

Schema and API limits:

- Memory `content` is capped at `8,000` characters.
- A memory can have at most `20` tags.
- Each tag is capped at `64` characters.
- `tag` and `q` retrieval filters are capped at `256` characters.
- `POST /memories/batch` accepts at most `25` memories.

Runtime limits are configured with environment variables:

| Environment variable | Default | Notes |
| --- | ---: | --- |
| `MEMORIES_RATE_LIMITING_ENABLED` | `true` | Set to `false` only as a local debugging escape hatch. |
| `MEMORIES_RATE_LIMIT_READS_PER_MINUTE` | `120` | Applies to REST memory reads. Reads refresh `last_accessed_at`. |
| `MEMORIES_RATE_LIMIT_WRITES_PER_MINUTE` | `30` | Applies to REST create, update, and delete requests. |
| `MEMORIES_RATE_LIMIT_BATCH_PER_MINUTE` | `10` | Applies to `POST /memories/batch`. |
| `MEMORIES_RATE_LIMIT_MCP_PER_MINUTE` | `240` | Applies to MCP streamable HTTP traffic under `/mcp`. |
| `MEMORIES_REQUEST_BODY_MAX_BYTES` | `1048576` | Applies to `POST` and `PATCH` REST/MCP HTTP request bodies. |

Rate limiting uses a fixed 60-second in-memory window per process. Clients are identified by a trimmed `X-Client-Id` header, capped at 128 characters, when present; otherwise the client IP is used. A limited request returns `429` with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.

`/health` and `/ready` are exempt from normal rate limiting.

Request body-size enforcement returns `413` with `X-Request-Body-Limit` when the declared or streamed request body exceeds the configured limit.

For behavioral load checks, use the standalone stress harness at [scripts/rate_limit_stress.py](scripts/rate_limit_stress.py). It exercises mixed agent usage, fast bursts, concurrent floods, and two-agent isolation across REST and MCP surfaces, then writes an HTML report. See [scripts/README.md](scripts/README.md) for setup, tuning options, and result interpretation.


## Security

This project is intended for single-user, local-only use on a trusted machine.

- The HTTP API and MCP streamable HTTP endpoint do not implement application-level authentication or authorization.
- Bind the HTTP API and MCP streamable HTTP endpoint to localhost only.
- Browser-based MCP access is denied by default unless you create a local browser client allowlist file.
- Browser origins are matched exactly.
- Default local safety limits reduce accidental runaway behavior but do not make the service safe to expose beyond localhost.
- Do not expose this service to the internet, a LAN, a shared VM, or a reverse proxy unless you add proper authentication, authorization, and transport security.
- Treat the SQLite database file and local MCP/client configuration as sensitive local data.

If you need multi-user or remote access, the current security model is not sufficient.
