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

## Autonomy

- Default autonomy level: `autonomous`.
- Autonomy levels and allowed actions:
	- `manual` — Agent may suggest recall and writes but must request explicit human confirmation before performing any create, update, or delete operations. Reads are allowed for context but agents should minimize broad queries.
	- `suggest` — Agent may perform reads and propose writes; it may perform non-destructive updates to clearly matching preference records when the match is unambiguous, but should request confirmation for new creates and deletions.
	- `autonomous` — Agent may perform reads, create, update, and soft-delete (`status='deleted'`) operations without an additional human approval step, provided it follows the behavior policy (sensitive-data confirmation, deduping flow, concise atomic writes, and transparency reporting).

- Soft-delete behavior: deletions performed by agents set memory `status` to `deleted` (soft-delete) so items remain auditable and may be inspected or restored by humans or repair workflows.

- Transparency: agents operating under any autonomy level must follow the assistant guidance in `assets/use-memories-api-assistant.md` which requires a short `Memory actions:` summary appended to replies whenever memory tools are used.


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
