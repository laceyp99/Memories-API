---
name: memories
description: 'Use when working with the memories-api MCP server, query_memories_tool, create_memory_tool, update_memory_tool, delete_memory_tool, or read_memory. Guides recall, personalization, deduping, sensitive-memory confirmation, contradiction handling, and prompt/resource usage for this repo.'
argument-hint: '[task or memory operation]'
user-invocable: true
---

# Memories Tool Behavior

Use this skill when an agent is deciding how to interact with the memories API or its MCP tools.

## When to Use

- The task may benefit from recalled user preferences or identity context.
- The agent is deciding whether to create or update a durable memory.
- The task involves correcting, invalidating, or reconciling an existing memory.
- The agent needs to avoid broad recall patterns that would create noisy access timestamps.

## Procedure

1. Decide whether memory recall is actually needed for the task.
2. At the beginning of a session, run two targeted bootstrap queries: active preferences first, then active identity memories.
3. For a substantive reply, use one moderate query shaped by `memory_type`, `tag`, or focused `q` terms.
4. If considering a write, check whether the information is durable, atomic, and safe to store.
5. Ask before storing any sensitive memory.
6. Prefer updating an existing memory over creating a duplicate when the match is clear.
7. If a contradiction appears, ask the user which version should remain authoritative before updating or invalidating.
8. Do not delete memories automatically.

## References

- [Tool behavior policy](./references/memories-tool-behavior-policy.md)
- [Query recipes](./references/memories-query-recipes.md)

## Assets

- [Static MCP prompt assistant message](./assets/use-memories-api-assistant.md)
- [Anthropic Tools Schema JSON](./assets/anthropic_tools.json)
- [OpenAI Functions JSON](./assets/openai_functions.json)

## Scripts

- [Preview skill assets script](./scripts/preview_memories_skill.py)
- [Query memories curl script](./scripts/curl_query_memories.sh)
- [Create memory curl script](./scripts/curl_create_memory.sh)
- [Update memory curl script](./scripts/curl_update_memory.sh)
- [Delete memory curl script](./scripts/curl_delete_memory.sh)
- [Read memory curl script](./scripts/curl_read_memory.sh)
