# Query Recipes

Use these recipes as starting points. Keep limits small unless the user explicitly asks for broader recall.

## Bootstrap Preference Recall

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

## Update-Over-Create Checks

Before creating a memory, check whether an existing active memory already captures the same durable fact or preference.

- If the match is clear, use `update_memory_tool`.
- If the new information is materially distinct, use `create_memory_tool`.
- If the overlap is uncertain, ask the user before writing.

## Contradiction Flow

If a new statement conflicts with an existing memory:

1. Read or query the existing memory narrowly.
2. Explain the conflict to the user.
3. Ask whether to correct the existing record or invalidate it.
4. Apply `update_memory_tool` or `update_memory_tool(..., status="invalid")` only after confirmation.
