# Curl Examples

Use this file for manual HTTP checks and copy-paste examples.

When this file is useful:

- verifying the HTTP API without going through MCP
- reproducing a bug report with a minimal request
- smoke-testing local behavior while editing storage or routing code
- drafting examples for docs or client integrations

When these examples are not the right tool:

- agent runtime behavior, which should follow the MCP prompt and policy files
- repository validation, which should prefer tests over hand-run curl commands
- schema truth, which should come from the FastAPI and MCP implementations

Set a base URL first:

```bash
BASE_URL=http://127.0.0.1:8000
```

Create a memory:

```bash
curl -s -X POST "$BASE_URL/memories" \
	-H "Content-Type: application/json" \
	-d '{
		"content": "User prefers concise answers",
		"tags": ["preference", "writing-style"],
		"memory_type": "preference",
		"status": "active"
	}' | jq .
```

Query active preference memories:

```bash
curl -s \
	"$BASE_URL/memories?status=active&memory_type=preference&sort=updated_at&limit=5&offset=0" | jq .
```

Query with a tag and free-text filter:

```bash
curl -s \
	"$BASE_URL/memories?status=active&memory_type=preference&tag=writing-style&q=concise&sort=updated_at&limit=5&offset=0" | jq .
```

Read one memory by id:

```bash
curl -s "$BASE_URL/memories/1" | jq .
```

Update an existing memory:

```bash
curl -s -X PUT "$BASE_URL/memories/1" \
	-H "Content-Type: application/json" \
	-d '{
		"content": "User prefers concise technical answers",
		"tags": ["preference", "writing-style"],
		"memory_type": "preference"
	}' | jq .
```

Invalidate a memory without deleting it:

```bash
curl -s -X PUT "$BASE_URL/memories/1" \
	-H "Content-Type: application/json" \
	-d '{
		"status": "invalid"
	}' | jq .
```

Soft-delete a memory:

```bash
curl -s -X DELETE "$BASE_URL/memories/1" | jq .
```

Notes:

- `DELETE /memories/{id}` performs a soft delete and returns the updated memory.
- `GET /memories` and `GET /memories/{id}` refresh `last_accessed_at` for returned memories.
- Prefer this markdown file for condensed examples. Keep executable scripts only if they become real parameterized smoke-test helpers.
