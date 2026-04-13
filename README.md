# Memories API

A small FastAPI project for storing memories with tags and lifecycle metadata in a JSON database.

## Project layout

```text
app/
	__init__.py
	config.py
	main.py
	schemas.py
	storage.py
tests/
	conftest.py
	test_memories.py
.github/workflows/ci.yml
data.json
pyproject.toml
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Run the API

```powershell
uvicorn app.main:app --reload
```

Interactive docs are available at `http://localhost:8000/docs`.

## Use as an MCP Server

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
        "MEMORIES_DATA_FILE": "path\to\Memories API\data.json"
      }
    }
  }
}
```
### Manual Start

For local debugging, you can start the MCP Inspector:
```
memories-mcp-inspector
```

Interactive MCP Inspector available at `http://localhost:6274`.


## Current memory object

The API currently stores and returns these fields:

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

Current request behavior:

- `content` and `tags` are required on create.
- `memory_type` and `status` are optional on create and patch.
- `created_at`, `updated_at`, `last_accessed_at`, and `version` are server-managed.
- `created_at` is set on POST.
- `updated_at` is refreshed only when PATCH changes at least one editable field.
- `last_accessed_at` is refreshed on GET `/memories/{id}`.
- `version` starts at `1` and increments only when PATCH changes at least one editable field.

Allowed values:

- `memory_type`: `preference`, `fact`, `goal`, `identity`, `instruction`, `task_context`, `event`
- `status`: `active`, `archived`, `superseded`, `invalid`, `deleted`

## Run tests

```powershell
pytest
```

## Format and lint

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

Get all memories:

```bash
curl http://127.0.0.1:8000/memories
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

Search memories by text or tag:

```bash
curl "http://127.0.0.1:8000/search?query=python"
```

## CI

GitHub Actions runs formatting, linting, and tests on every push and pull request using the workflow in `.github/workflows/ci.yml`.