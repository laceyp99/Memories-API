# Query Recipes

Use these recipes as the canonical query shapes behind `bootstrap_memories_tool` and targeted `query_memories_tool` calls. Keep limits small unless the user explicitly asks for broader recall.

## Bootstrap Preference Recall

This is the preference page returned by `bootstrap_memories_tool`.

```json
{
  "status": "active",
  "memory_type": "preference",
  "sort": "updated_at",
  "limit": 5,
  "offset": 0
}
```

## Bootstrap Identity Recall

This is the identity page returned by `bootstrap_memories_tool`.

```json
{
  "status": "active",
  "memory_type": "identity",
  "sort": "updated_at",
  "limit": 5,
  "offset": 0
}
```

## Moderate Substantive Recall

```json
{
  "status": "active",
  "memory_type": "preference",
  "tag": "writing-style",
  "q": "examples concise",
  "sort": "updated_at",
  "limit": 5,
  "offset": 0
}
```

## Deduping Candidate Search

Use this pattern before creating a new memory when a durable fact or preference may already exist.

```json
{
  "status": "active",
  "memory_type": "preference",
  "tag": "writing-style",
  "q": "concise technical",
  "sort": "updated_at",
  "limit": 5,
  "offset": 0
}
```

Suggested process:

1. Search narrowly by `memory_type`, `status`, and a tag when possible.
2. Compare the results against the new fact or preference.
3. Update the best match if the content is the same durable memory with improved wording or tags.
4. Create a new memory only if the information is materially distinct.
5. Ask the user if the overlap is unclear or contradictory.

## Sensitive Data Confirmation

Use this workflow when the content may need `sensitive`, `pii`, or `health` tags.

1. Ask the user for explicit confirmation before storing it.
2. Narrow the search first if you are checking for an existing related memory.
3. Keep the eventual stored memory atomic and concise.
4. Tag it only with confirmed sensitive tags and any other short retrieval tags that truly help.

## Update-Over-Create Checks

Before creating a memory, check whether an existing active memory already captures the same durable fact or preference.

- If the match is clear, use `update_memory_tool`.
- If the new information is materially distinct, use `create_memory_tool`.
- If the overlap is uncertain, ask the user before writing.

For sensitive memories, do the confirmation step before any create or update.

## Contradiction Flow

If a new statement conflicts with an existing memory:

1. Read or query the existing memory narrowly.
2. Explain the conflict to the user.
3. Ask whether to correct the existing record or invalidate it.
4. Apply `update_memory_tool` or `update_memory_tool(..., status="invalid")` only after confirmation.
