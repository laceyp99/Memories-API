# Memories Tool Behavior Policy

Use this policy when deciding how to query, read, create, update, or invalidate memories.

## Goals

- Personalize responses with durable user context.
- Preserve continuity across sessions without over-reading the store.
- Keep memory writes concise, durable, and easy to retrieve.

## Read Policy

### Bootstrap recall

At the beginning of a session, run two targeted queries:

1. Active preferences with `memory_type=preference`, `status=active`, `sort=updated_at`, and a small `limit`.
2. Active identity memories with `memory_type=identity`, `status=active`, `sort=updated_at`, and a small `limit`.

Use `query_memories_tool` for these retrieval steps.

Do not start with a broad catch-all query.

### Substantive reply recall

For a reply that benefits from memory, use one moderate query shaped by the task.

Preferred order:

1. Structured filters such as `memory_type`, `status`, and `tag`
2. `q` only when lexical narrowing is useful
3. Conservative pagination

Avoid repeated broad queries because returned items refresh `last_accessed_at`.

### Debug and correction workflows

Ignore `invalid` and `deleted` memories during normal recall.
Inspect `invalid` memories only when the user is correcting data, debugging tool behavior, or reconciling contradictions.

## Write Policy

Create or update memories only when the information is durable and likely to matter again.

Good candidates:

- stable preferences
- durable identity details
- lasting project context
- recurring workflow constraints

Avoid storing:

- transient chat details
- one-off reasoning steps
- speculative interpretations
- sensitive data unless the user explicitly confirms storage

## Deduping and Updates

When a new fact clearly matches an existing durable memory, prefer `update_memory_tool` over `create_memory_tool`.
Create a new memory only when the new information is materially distinct.

## Contradictions

If a new statement contradicts an existing memory:

1. Surface the conflict to the user.
2. Ask which version should remain authoritative.
3. Update the existing memory if it should be corrected.
4. Invalidate the older memory if it should remain recorded but no longer used.

Do not delete automatically.

## Tag Guidance

Use light conventions that help retrieval.

Recommended tags include:

- `preference`
- `identity`
- `writing-style`
- `project`
- a domain or topic tag relevant to the content

Keep tags short, literal, and reusable.
