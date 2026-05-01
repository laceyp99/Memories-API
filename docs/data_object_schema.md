# Memory Data Object Schema

This document describes the memory object used by this project and the retrieval model built around it. The goal is to keep the schema lean while still supporting safe updates, deterministic retrieval, and future ranking strategies.

## Table of Contents

- [Object Schema Example](#object-schema-example)

Elements
1. [ID](#1-id)
2. [Content](#2-content)
3. [Tags](#3-tags)
4. [Created At](#4-created_at)
5. [Updated At](#5-updated_at)
6. [Last Accessed At](#6-last_accessed_at)
7. [Memory Type](#7-memory_type)
8. [Status](#8-status)
9. [Version](#9-version)

Practical Implementation Advice
- [Best First Step](#best-first-step)
- [Good Defaults](#good-defaults)
- [Recommended Retrieval Mindset](#recommended-retrieval-mindset)

## Object Schema Example

```json
{
  "id": 1,
  "content": "User prefers concise answers with examples.",
  "tags": ["preference", "writing-style", "concise"],
  "created_at": "2026-04-06T14:12:00.000000Z",
  "updated_at": "2026-04-06T14:12:00.000000Z",
  "last_accessed_at": "2026-04-10T09:21:00.000000Z",
  "memory_type": "preference",
  "status": "active",
  "version": 1
}
```

---

## 1. `id`

### What it is
A stable unique identifier for the memory record.

### Typical values
- Database-generated integer ID

### Why it matters
Without an `id`, you cannot reliably update, delete, merge, supersede, or reference a memory later.

### Recommendation
Use a database-generated integer ID if the service owns persistence end to end. It is simple, compact, and works well with deterministic tie-breaking in retrieval.

---

## 2. `content`

### What it is
The main text of the memory.

### Typical values
- A direct fact: `User lives in Albany.`
- A preference: `User prefers concise responses.`
- A temporary state: `User is traveling this week.`
- A task context note: `Project Falcon launch moved to May.`

### Guidelines for values
- Keep it atomic when possible
- Prefer one memory per distinct fact or idea
- Write it in normalized language rather than raw chat fragments

### Why it matters
This is the actual memory payload the system will retrieve and use.

### Why choose shorter vs longer content
- **Shorter content**: easier to rank, compare, and inject into prompts
- **Longer content**: preserves nuance, but may be harder to maintain and deduplicate

### Recommendation
Keep `content` focused and singular. If a memory contains multiple independent facts, split it into separate records.

---

## 3. `tags`

### What it is
A list of keywords or labels associated with the memory.

### Typical values
- `preference`
- `profile`
- `project-falcon`
- `deadline`
- `travel`
- `writing-style`

### Possible value strategy options
- Freeform strings
- Controlled vocabulary
- Hybrid approach with a few controlled categories and some freeform tags

### Why it matters
Tags make filtering and retrieval easier, especially before the system has richer structured fields or graph relationships.

### Why choose one approach over another
- **Freeform tags**: fast to implement, flexible, but can become messy
- **Controlled vocabulary**: cleaner analytics and retrieval, but slower to evolve
- **Hybrid**: best balance for most systems

### Recommendation
Use a hybrid approach. Keep a small set of standard tags for core concepts, and allow a limited set of extra freeform tags.

---

## 4. `created_at`

### What it is
The timestamp when the memory was first created.

### Typical values
- ISO 8601 UTC timestamp such as `2026-04-06T14:12:00Z`

### Why it matters
It helps with auditability, ordering, debugging, analytics, and understanding how old a memory is.

### Why choose UTC ISO 8601
- Standard across systems
- Easy to serialize and parse
- Avoids time zone ambiguity

### Recommendation
Always store in ISO 8601 UTC.

---

## 5. `updated_at`

### What it is
The timestamp when the memory was last edited or changed.

### Typical values
- ISO 8601 UTC timestamp

### Why it matters
A memory may be corrected, refined, or reclassified after creation. `updated_at` helps the system know which version is current.

### Why it is separate from `created_at`
A record can be old overall but recently corrected/patched. Keeping both fields lets you distinguish original age from latest revision.

### Recommendation
Always update this field whenever any meaningful part of the record changes.

In this project, `updated_at` changes only when PATCH actually modifies at least one editable field.

---

## 6. `last_accessed_at`

### What it is
The timestamp when the memory was last retrieved or used by the system.

### Typical values
- ISO 8601 UTC timestamp
- `null` if never accessed after creation

### Why it matters
This is useful for ranking, retention, pruning, and decay strategies.

### Why choose to track this
- Helps identify stale but unused memories
- Helps preserve records that are actively useful
- Supports future cleanup policies

### Why choose `null` vs setting it equal to `created_at`
- **`null` initially**: clearly means never retrieved
- **Set to `created_at` initially**: simpler if you treat creation as first use

### Recommendation
Use `null` initially unless your system explicitly treats creation as a read event.

In this project, `last_accessed_at` is refreshed when a client reads one memory directly or when retrieval returns a memory in a paginated result set.

---

## 7. `memory_type`

### What it is
A categorical label describing what kind of memory this is.

### Suggested values
- `preference`
- `fact`
- `goal`
- `identity`
- `instruction`
- `task_context`
- `event`

### Why it matters
Different memory types should be ranked and retained differently.

### Why choose one type over another
- **`preference`**: use for stable likes, dislikes, or style choices
- **`fact`**: use for concrete statements that may be true independently of the current task
- **`goal`**: use when the memory reflects a desired future outcome
- **`identity`**: use for durable user or agent profile details
- **`instruction`**: use for standing guidance on behavior
- **`task_context`**: use for project or work-in-progress details
- **`event`**: use for time-linked things that happened or will happen

### Recommendation
Start with 5 to 7 enum values max. Add more only when retrieval or policy behavior clearly needs them.

---

## 8. `status`

### What it is
The current lifecycle state of the memory.

### Suggested values
- `active`
- `archived`
- `superseded`
- `invalid`
- `deleted`

### Why it matters
You need a way to retire or disable memories without losing record history.

### Why choose one status over another
- **`active`**: memory is available for normal retrieval
- **`archived`**: memory is kept for history but should rarely be surfaced
- **`superseded`**: replaced by a newer memory
- **`invalid`**: determined to be wrong or unsafe to use
- **`deleted`**: soft-deleted by the delete operation, hidden from single-record reads, and excluded from retrieval unless `status=deleted` is requested

### Recommendation
At minimum support `active`, `superseded`, and `invalid`. Add `archived` and `deleted` if lifecycle control matters in your system.

---

## 9. `version`

### What it is
A number that increments each time the record is updated.

### Possible values
- Integer starting at `1`

### Why it matters
Versioning supports safe updates, concurrency control, and auditability.

### Why choose an integer
- Easy to compare
- Easy to increment
- Familiar for optimistic locking patterns

### Recommendation
Start at `1` and increment on every meaningful update.

In this project, `version` increments only when PATCH changes the record.

---

# Retrieval contract

This project uses one retrieval contract across HTTP and MCP.

- HTTP: `GET /memories`
- MCP: `query_memories_tool`

Both surfaces accept the same query fields:

- `status`
- `memory_type`
- `tag`
- `q`
- `sort`
- `limit`
- `offset`

Both surfaces return the same envelope:

```json
{
  "items": [],
  "total": 0,
  "limit": 10,
  "offset": 0,
  "has_more": false
}
```

## Filter semantics

- `status` and `memory_type` are exact structured filters.
- Retrieval excludes `status=deleted` by default unless the caller explicitly requests `status=deleted`.
- `tag` is exact matching against the stored tag list.
- `q` is case-insensitive free-text matching over `content` and stored tags.
- Filters compose with `AND`.

This distinction matters because exact filters are predictable and contract-friendly, while `q` provides a lightweight lexical narrowing mechanism without introducing opaque ranking behavior.

## Sort and pagination semantics

- Allowed sort keys are `id`, `created_at`, `updated_at`, and `last_accessed_at`.
- `id` sorts ascending.
- Other sort keys sort descending with `id DESC` as a stable tie-breaker.
- `limit` defaults to `10` and is capped at `100`.
- `offset` defaults to `0`.
- `total` counts matches before pagination.
- `has_more` tells the caller whether another page exists.

These rules keep retrieval deterministic, which makes pagination reliable and prevents page boundaries from drifting unpredictably when multiple rows share the same timestamp.

## Access-time rationale

`last_accessed_at` is not just an audit field. It is part of the retrieval model.

- A memory returned to the caller has been used and should be marked as accessed.
- Only returned rows are refreshed.
- Filtered-out rows and rows outside the current page are not refreshed.

That design keeps access history meaningful for future retention, decay, and ranking logic. It avoids the misleading outcome where a broad query updates timestamps for many records the agent never actually saw.

## Ranking rationale

This project intentionally keeps today's retrieval logic deterministic.

- Structured filters narrow the candidate set.
- `q` provides case-insensitive lexical matching over `content` and tags.
- Explicit sort keys define presentation order.
- Pagination is applied after deterministic ordering.

That is different from semantic search. If you later add vector-based retrieval, treat it as a separate ranking mode or dedicated search tool instead of changing the meaning of this contract in place.

---

# Practical implementation advice

## Best first step
If you want to implement this quickly, define strict types for:
- `memory_type`
- `status`

And keep these flexible:
- `content`
- `tags`

## Good defaults
```json
{
  "memory_type": "fact",
  "last_accessed_at": null,
  "status": "active",
  "version": 1
}
```

## Recommended retrieval mindset
When retrieving memories in this implementation, start with:
- exact lifecycle filters such as `status`
- exact structural filters such as `memory_type` and `tag`
- lightweight `q` matching over `content` and tags
- explicit deterministic sort keys

If you later add semantic search, combine that ranking with the existing lifecycle and access signals rather than replacing them blindly.
