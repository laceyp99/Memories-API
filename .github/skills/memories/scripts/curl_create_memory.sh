#!/usr/bin/env bash
# Create a memory via HTTP API (requires `jq` for pretty output)
curl -s -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers concise answers",
    "tags": ["preference", "writing-style"],
    "memory_type": "preference",
    "status": "active"
  }' | jq .
