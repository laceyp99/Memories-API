#!/usr/bin/env bash
# Delete a memory via HTTP API (requires `jq` for pretty output)
curl -s \
  -X DELETE \
  'http://localhost:8000/memories/123' | jq .
