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
- `DELETE /memories/{id}` performs a soft delete by setting `status` to `deleted`, refreshing `updated_at`, and incrementing `version`.
- `last_accessed_at` is refreshed on `GET /memories/{id}`.
- Soft-deleted memories are hidden from `GET /memories/{id}`.
- Every memory returned by retrieval is also considered accessed, so `GET /memories` and MCP `query_memories_tool` refresh `last_accessed_at` only for the returned page.
- Retrieval excludes soft-deleted memories by default unless `status=deleted` is requested explicitly.

Allowed values:

- `memory_type`: `preference`, `fact`, `identity`, `event`
- `status`: `active`, `invalid`, `deleted`

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

## Security Model

This project is intended for single-user, local-only use on a trusted machine.

- The HTTP API and MCP server do not implement application-level authentication or authorization.
- The HTTP API and MCP streamable HTTP endpoint should only be bound to localhost for local development.
- Browser-based MCP access is denied by default unless you create a local browser client allowlist file.
- Browser origins are matched exactly. A configured origin of `http://localhost:3000` does not also allow `http://127.0.0.1:3000`.
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
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive docs are available at `http://127.0.0.1:8000/docs`.

This single app serves both surfaces:

- REST API at `http://127.0.0.1:8000/memories`
- MCP streamable HTTP endpoint at `http://127.0.0.1:8000/mcp`

The MCP server exposes three surface types:

- Tools for create, read, update, delete, and deterministic query flows
- A static prompt named `use_memories_api` for deliberate memory-tool usage
- A resource at `memories://policy/tool-behavior` with tool-behavior policy and query recipes

The prompt and resource are meant to keep MCP clients and agents aligned on the same memory behavior:

- Default autonomy is `autonomous` for normal memory handling.
- Agents should remain transparent and include a short `Memory actions:` summary whenever they use memory tools.
- Sensitive memories tagged with `sensitive`, `pii`, or `health` require explicit user confirmation before storage.
- Before creating a new memory, agents should query narrowly first and prefer `update` over `create` when an active memory already captures the same durable fact.
- Tags should stay lowercase, short, and literal, with one or two words preferred.

### Configure browser-based MCP clients

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

### Open WebUI note

For a local Open WebUI setup, two values matter:

- Browser origin: usually `http://localhost:3000`. This is what goes into `mcp_browser_clients.local.json`.
- MCP server URL: if Open WebUI runs in Docker, it may need `http://host.docker.internal:8000/mcp` instead of `http://localhost:8000/mcp` to reach the host machine.

### Use as an MCP Server

This project supports both MCP transports during local development:

- Streamable HTTP through the mounted `/mcp` endpoint on the main FastAPI app
- Stdio through the dedicated MCP entrypoint

### Stdio MCP clients

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

### Streamable HTTP MCP clients

Point the client at:

```text
http://127.0.0.1:8000/mcp
```

If the client application runs in Docker on the same machine, use the host-reachable URL that the container can resolve, for example:

```text
http://host.docker.internal:8000/mcp
```

Browser-based clients still need an exact allowed origin in `mcp_browser_clients.local.json`.

### Manual Start

For local debugging, you can start the MCP Inspector:
```
mcp dev app/mcp_server.py
```

Interactive MCP Inspector available at `http://localhost:6274`.


## Example requests

Create a memory:

```bash
curl -X POST http://127.0.0.1:8000/memories \
	-H "Content-Type: application/json" \
	-d '{"content":"Learning FastAPI testing","tags":["python","api"],"memory_type":"identity"}'
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
curl "http://127.0.0.1:8000/memories?status=active&memory_type=preference&tag=python&q=testing&sort=updated_at&limit=5&offset=0"
```

Get one memory by id:

```bash
curl http://127.0.0.1:8000/memories/1
```

Update a memory:

```bash
curl -X PATCH http://127.0.0.1:8000/memories/1 \
	-H "Content-Type: application/json" \
	-d '{"content":"Practicing FastAPI testing","status":"invalid"}'
```

Delete a memory:

```bash
curl -X DELETE http://127.0.0.1:8000/memories/1
```

This performs a soft delete. The row remains stored with `status="deleted"` and is hidden from normal single-record access and default retrieval.

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
			"memory_type": "event",
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

The MCP server exposes the same core memory operations over stdio and streamable HTTP:

- `create_memory_tool`
- `update_memory_tool`
- `delete_memory_tool`
- `read_memory`
- `query_memories_tool`

`query_memories_tool` mirrors the HTTP retrieval contract and accepts `status`, `memory_type`, `tag`, `q`, `sort`, `limit`, and `offset`.

`delete_memory_tool` performs the same soft delete as `DELETE /memories/{id}` and marks the memory as `deleted` rather than removing the row physically.

## CI

GitHub Actions runs formatting, linting, and tests on every push and pull request using the workflow in `.github/workflows/ci.yml`.
