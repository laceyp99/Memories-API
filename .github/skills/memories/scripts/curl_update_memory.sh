#!/usr/bin/env bash
# Update a memory via HTTP API (requires `jq` for pretty output)
curl -s \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated memory content", "tags": ["updated", "example"], "memory_type": "event"}' \
  'http://localhost:8000/memories/123' | jq .
