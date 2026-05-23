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

### Sensitive Data

Treat `sensitive`, `pii`, and `health` as sensitive tags.

Before storing any memory that contains or should be tagged with sensitive data:

1. Ask the user for explicit confirmation.
2. Confirm the user wants the information persisted in the memories store.
3. Keep the stored memory atomic and minimal.
4. Use the sensitive tag alongside any other narrow retrieval tags only when confirmed.

If the user does not clearly confirm storage, do not create or update the memory.

## Deduping and Updates

Use a check-before-write flow to avoid duplicates.

Recommended flow:

1. Check whether a relevant active memory already exists.
2. Query narrowly using structured filters first, especially `memory_type`, `status`, and `tag`.
3. Compare the candidate against existing active memories for the same durable fact or preference.
4. If the match is clear, update the existing memory instead of creating a duplicate.
5. If the information is materially distinct, create a new memory.
6. If overlap or contradiction is uncertain, ask the user before writing.

When the match is clear, prefer `update_memory_tool` over `create_memory_tool`.
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

- `writing-style`
- `project`
- `identity`
- `workflow`
- `project-<name>` when the tag stays short and literal
- `sensitive`
- `pii`
- `health`

Keep tags lowercase, short, literal, and reusable.
Prefer one or two words per tag.
Use tags to describe retrieval concepts, not schema fields or memory_type values.
