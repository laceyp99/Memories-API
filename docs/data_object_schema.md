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
8. [Scope](#8-scope)
9. [Source](#9-source)
10. [Importance](#10-importance)
11. [Confidence](#11-confidence)
12. [Status](#12-status)
13. [Expires At](#13-expires_at)
14. [Version](#14-version)

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
  "scope": "user",
  "source": {
    "kind": "conversation",
    "actor": "user"
  },
  "importance": 0.82,
  "confidence": 0.94,
  "status": "active",
  "expires_at": null,
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

## 8. `scope`

### What it is
The boundary within which the memory is valid or should be reused.

### Suggested values
- `session`
- `conversation`
- `user`
- `project`
- `workspace`
- `agent`

### Why it matters
Not all memories should travel everywhere. Scope prevents context leakage.

### Why choose one scope over another
- **`session`**: for very temporary context
- **`conversation`**: for context that matters only within one thread
- **`user`**: for preferences or facts that should persist across conversations
- **`project`**: for work linked to a specific initiative
- **`workspace`**: for team or organization-level context
- **`agent`**: for internal operating knowledge specific to the agent

### Recommendation
If you are starting simple, support `conversation`, `user`, and `project` first.

---

## 9. `source`

### What it is
Structured metadata describing where the memory came from.

### Suggested shape
```json
{
  "kind": "conversation",
  "actor": "user"
}
```

### Suggested `kind` values
- `conversation`
- `document`
- `integration`
- `manual`
- `system`
- `inferred`

### Suggested `actor` values
- `user`
- `agent`
- `system`
- `external`

### Why it matters
Source affects trust, explainability, and update policy.

### Why choose one source kind over another
- **`conversation`**: user or agent said it in chat
- **`document`**: extracted from a file or knowledge base
- **`integration`**: came from a connected app or API
- **`manual`**: explicitly entered by a human operator
- **`system`**: created by application logic
- **`inferred`**: guessed or synthesized from other data

### Why choose one actor over another
- **`user`**: usually highest trust for direct preferences
- **`agent`**: useful for generated summaries, but may need more caution
- **`system`**: trusted operational metadata
- **`external`**: useful but may depend on source quality

### Recommendation
At minimum, store `kind` and `actor`. Later you can add things like `message_id` or `document_id`.

---

## 10. `importance`

### What it is
A score representing how valuable the memory is for future reuse.

### Possible value options
- Float from `0.0` to `1.0`
- Integer scale such as `1` to `5`
- Enum such as `low`, `medium`, `high`

### Why it matters
Importance supports ranking, retention, summarization, and pruning.

### Why choose one format over another
- **Float `0.0–1.0`**: best for ranking systems and future tuning
- **Integer `1–5`**: simpler for humans to reason about
- **Enum**: easiest to understand, but least flexible

### Recommendation
Use a float from `0.0` to `1.0`. You can still map it to human-friendly buckets in the UI.

### Example interpretation
- `0.0–0.2`: likely disposable
- `0.3–0.5`: useful but not critical
- `0.6–0.8`: important
- `0.9–1.0`: highly durable memory

---

## 11. `confidence`

### What it is
A score representing how confident the system is that the memory is correct and well-extracted.

### Possible value options
- Float from `0.0` to `1.0`
- Integer scale
- Enum such as `uncertain`, `probable`, `confirmed`

### Why it matters
Importance and confidence are not the same. Something can be important but uncertain.

### Why choose one format over another
- **Float `0.0–1.0`**: more precise and easier for ranking formulas
- **Integer**: simpler but less expressive
- **Enum**: understandable, but coarse

### Recommendation
Use a float from `0.0` to `1.0`.

### Example interpretation
- `0.0–0.3`: weak inference or noisy extraction
- `0.4–0.7`: plausible but should be used carefully
- `0.8–1.0`: strong confidence, likely safe to reuse

### When to lower confidence
- The memory was inferred rather than directly stated
- The source was ambiguous
- The extraction process was lossy or probabilistic

---

## 12. `status`

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

## 13. `expires_at`

### What it is
An optional timestamp after which the memory should no longer be treated as current.

### Possible values
- ISO 8601 UTC timestamp
- `null` for non-expiring memories

### Why it matters
Some memories are temporary. Without expiration, stale context can pollute future agent behavior.

### Why choose to use this field
Use it when the truth of a memory is naturally time-bounded.

### Good use cases
- Temporary preferences
- Short-term task context
- Travel or schedule notes
- Event windows

### Why choose `null`
Many durable memories, such as identity or long-term preferences, should not expire automatically.

### Recommendation
Default to `null`, and only set it when there is a clear time boundary.

---

## 14. `version`

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
- `scope`
- `source.kind`
- `source.actor`
- `status`

And keep these flexible:
- `content`
- `tags`
- `importance`
- `confidence`

## Good defaults
```json
{
  "tags": [],
  "last_accessed_at": null,
  "importance": 0.5,
  "confidence": 0.8,
  "status": "active",
  "expires_at": null,
  "version": 1
}
```

## Recommended retrieval mindset
When retrieving memories, rank with a combination of:
- semantic match to `content`
- tag match
- `scope`
- `memory_type`
- `importance`
- `confidence`
- recency from `updated_at` or `last_accessed_at`
- whether `status` is still usable
- whether `expires_at` has passed