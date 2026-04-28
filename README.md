# Memories API

A small FastAPI and MCP project for storing memories with tags, lifecycle metadata, and a unified retrieval contract backed by SQLite.

## Memory object

The API and MCP server both operate on this server-managed memory shape:

```json
{
	"id": 1,
	"content": "User prefers concise answers.",
	"tags": ["preference", "writing-style"],
	"created_at": "2026-04-06T14:12:00.000000Z",
	"updated_at": "2026-04-06T14:12:00.000000Z",
	"last_accessed_at": null,
	"memory_type": "preference",
	"status": "active",
	"version": 1
}
```

Behavior summary:

- `content` and `tags` are required on create.
- `memory_type` defaults to `fact` and `status` defaults to `active`.
- `created_at`, `updated_at`, `last_accessed_at`, and `version` are server-managed.
- `POST /memories/batch` is all-or-nothing when validation fails.
- `updated_at` and `version` change only when a PATCH request actually changes an editable field.
- `last_accessed_at` is refreshed on `GET /memories/{id}`.
- Every memory returned by retrieval is also considered accessed, so `GET /memories` and MCP `query_memories_tool` refresh `last_accessed_at` only for the returned page.

Allowed values:

- `memory_type`: `preference`, `fact`, `goal`, `identity`, `instruction`, `task_context`, `event`
- `status`: `active`, `archived`, `superseded`, `invalid`, `deleted`

## Unified retrieval model

Retrieval now flows through one contract on both surfaces:

- HTTP uses `GET /memories`.
- MCP uses `query_memories_tool`.
- Both accept the same filters: `status`, `memory_type`, `tag`, `q`, `sort`, `limit`, and `offset`.
- Both return the same envelope: `items`, `total`, `limit`, `offset`, and `has_more`.

Filter semantics:

- `tag` is exact matching against the stored tag list.
- `q` is case-insensitive free-text matching over `content` and stored tags.
- Filters compose with `AND`, so you can narrow retrieval with both structured filters and free-text matching.

Sort semantics:

- Allowed sort keys are `id`, `created_at`, `updated_at`, and `last_accessed_at`.
- `id` sorts ascending.
- Timestamp-based sorts are descending and use `id DESC` as a deterministic tie-breaker.

Pagination semantics:

- `limit` defaults to `10` and is capped at `100`.
- `offset` defaults to `0`.
- `total` reports the full number of matches before pagination.
- `has_more` indicates whether another page exists after the current one.

## Access-time rationale

`last_accessed_at` is part of the retrieval contract, not just a single-record read detail.

- A memory that is surfaced to a client or agent has been used, so its access timestamp should reflect that usage.
- Only returned rows are refreshed. Filtered-out rows and rows beyond the current page are left unchanged.
- This keeps access data meaningful for later retention, pruning, and ranking decisions instead of inflating timestamps for records the caller never actually saw.

## Ranking rationale

This project intentionally separates deterministic retrieval from semantic ranking.

- Today, retrieval is deterministic: exact filters, case-insensitive substring matching for `q`, explicit sort keys, and stable pagination.
- Deterministic sorting makes the contract easy to test, reason about, and reuse from both HTTP and MCP.
- The current `q` behavior is not semantic search. It is a lightweight lexical filter over `content` and tags.

## Project layout

```text
app/
	__init__.py
	config.py
	main.py
	mcp_server.py
	schemas.py
	storage.py
tests/
	conftest.py
	contract/
	helpers/
	integration/
	unit/
.github/workflows/ci.yml
data.db
docs/
	data_object_schema.md
pyproject.toml
```

## Security Model

This project is intended for single-user, local-only use on a trusted machine.

- The HTTP API and MCP server do not implement application-level authentication or authorization.
- The MCP server is intended to be used locally over stdio by a local MCP client.
- The HTTP API should only be bound to localhost for local development.
- Do not expose this service to the internet, a LAN, a shared VM, or any untrusted environment.
- Do not run it behind a reverse proxy or with host binding such as `0.0.0.0` unless you add proper authentication, authorization, and transport security.
- Treat the SQLite database file and local MCP/client configuration as sensitive local data.

If you need multi-user or remote access, this project’s current security model is insufficient.

## Usage
### Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install .
```

### Run the API

```powershell
uvicorn app.main:app --reload
```

Interactive docs are available at `http://localhost:8000/docs`.

### Use as an MCP Server

This project can also run as a local MCP server over stdio.

### MCP-Compatible Clients

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

### Manual Start

For local debugging, you can start the MCP Inspector:
```
mcp dev app/mcp_server.py
```

Interactive MCP Inspector available at `http://localhost:6274`.

### Run tests

```powershell
pytest # The entire test suite

pytest tests/unit # only the unit tests
pytest tests/contract # only the contract tests
pytest tests/integration # only the integration tests
```

### Format and lint

```powershell
ruff format .
ruff check .
```

## Example requests

Create a memory:

```bash
curl -X POST http://127.0.0.1:8000/memories \
	-H "Content-Type: application/json" \
	-d '{"content":"Learning FastAPI testing","tags":["python","api"],"memory_type":"task_context"}'
```

Create multiple memories:

```bash
curl -X POST http://127.0.0.1:8000/memories/batch \
	-H "Content-Type: application/json" \
	-d '[
		{"content":"Learning FastAPI testing","tags":["python","api"]},
		{"content":"Practicing SQL joins","tags":["database","sql"]}
	]'
```

Get the first page of memories:

```bash
curl http://127.0.0.1:8000/memories
```

Query memories with filters, free-text matching, sort, and pagination:

```bash
curl "http://127.0.0.1:8000/memories?status=active&memory_type=instruction&tag=python&q=testing&sort=updated_at&limit=5&offset=0"
```

Get one memory by id:

```bash
curl http://127.0.0.1:8000/memories/1
```

Update a memory:

```bash
curl -X PATCH http://127.0.0.1:8000/memories/1 \
	-H "Content-Type: application/json" \
	-d '{"content":"Practicing FastAPI testing","status":"archived"}'
```

Delete a memory:

```bash
curl -X DELETE http://127.0.0.1:8000/memories/1
```

Example retrieval response:

```json
{
	"items": [
		{
			"id": 1,
			"content": "Learning FastAPI testing",
			"tags": ["python", "api"],
			"created_at": "2026-04-06T14:12:00.000000Z",
			"updated_at": "2026-04-06T14:12:00.000000Z",
			"last_accessed_at": "2026-04-06T14:20:00.000000Z",
			"memory_type": "instruction",
			"status": "active",
			"version": 1
		}
	],
	"total": 12,
	"limit": 5,
	"offset": 0,
	"has_more": true
}
```

## MCP tools

The MCP server exposes the same core memory operations over stdio:

- `create_memory_tool`
- `update_memory_tool`
- `delete_memory_tool`
- `read_memory`
- `query_memories_tool`

`query_memories_tool` mirrors the HTTP retrieval contract and accepts `status`, `memory_type`, `tag`, `q`, `sort`, `limit`, and `offset`.

## CI

GitHub Actions runs formatting, linting, and tests on every push and pull request using the workflow in `.github/workflows/ci.yml`.
