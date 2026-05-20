#!/usr/bin/env bash
# Query memories via HTTP API (requires `jq` for pretty output)
curl -s \
  'http://localhost:8000/memories?memory_type=preference&limit=5' | jq .
