# Memory Data Object Schema

This document breaks down a lean but capable memory object for an AI agent. The goal is to keep the schema small and easy to manage, while still giving the agent enough structure to store, rank, update, and safely reuse memory over time.

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
  "id": "mem_01JXYZ...",
  "content": "User prefers concise answers with examples.",
  "tags": ["preference", "writing-style", "concise"],
  "created_at": "2026-04-06T14:12:00Z",
  "updated_at": "2026-04-06T14:12:00Z",
  "last_accessed_at": "2026-04-10T09:21:00Z",
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
- String UUID
- ULID
- Database-generated ID
- Prefixed string such as `mem_abc123`

### Recommended format
- `mem_<unique_value>`
- Example: `mem_01JXYZ8M2KQ4...`

### Why it matters
Without an `id`, you cannot reliably update, delete, merge, supersede, or reference a memory later.

### Why choose one format over another
- **UUID**: good default, widely supported, easy to generate
- **ULID**: useful if you want sortable IDs by creation time
- **Prefixed IDs**: easier for debugging and log readability
- **Database integer IDs**: simple internally, but less portable across systems

### Recommendation
Use a prefixed ULID or UUID string. It is readable, portable, and safe across distributed systems.

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
Start with 5 to 7 enum values max. Add more only when you find retrieval or policy behavior needs them.

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
- **`deleted`**: logically removed from normal operations

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
  "tags": [],
  "last_accessed_at": null,
  "status": "active",
  "version": 1
}
```

## Recommended retrieval mindset
When retrieving memories, rank with a combination of:
- semantic match to `content`
- tag match
- `memory_type`
- recency from `updated_at` or `last_accessed_at`
- whether `status` is still usable