# MCP Prompt, Resource, and Skill Design

This document explains how the memories API exposes one shared behavior model through three surfaces: the MCP prompt, the MCP resource, and the repository skill. The goal is to keep the runtime prompt, the server policy, and the workspace guidance aligned without duplicating policy text here.

## Shared behavior model

The system is organized around a small set of consistent behaviors:

- Personalization is the primary reason to consult memory.
- Recall should stay narrow so access timestamps are not distorted by broad scans.
- Writes should be durable, atomic, and conservative.
- Sensitive information requires explicit user confirmation before it is stored.
- When a durable memory already exists, updating it is preferred over creating a duplicate.
- Conflicts should be resolved with the user before older records are corrected or invalidated.
- Invalid and deleted memories are excluded from normal recall.
- The same rules should be visible to both MCP clients and repository maintainers.

## Surface map

| Surface | Purpose | Canonical file |
| --- | --- | --- |
| MCP prompt | Static assistant priming for memory-aware sessions | [use-memories-api-assistant.md](../.github/skills/memories/assets/use-memories-api-assistant.md) |
| MCP resource | Canonical policy, bootstrap guidance, and query recipes served by the MCP server | [memories-tool-behavior-policy.md](../.github/skills/memories/references/memories-tool-behavior-policy.md), [memories-query-recipes.md](../.github/skills/memories/references/memories-query-recipes.md) |
| Repository skill | Workspace guidance for using and maintaining the memory workflow | [SKILL.md](../.github/skills/memories/SKILL.md) |
| MCP wiring | FastMCP registration for the prompt and resource | [app/mcp_server.py](../app/mcp_server.py) |

## MCP prompt

The MCP prompt is the runtime entry point for agents that need a memory-aware posture. It is best used when an assistant is about to begin a task that may benefit from bootstrap recall, cautious writes, or contradiction handling.

The prompt should point the model toward `prime_memory_context` for startup and `search_memories` for follow-up recall instead of restating the entire behavior contract in every session.

The prompt is intentionally static and concise. It should point the model toward the shared policy rather than restating the entire behavior contract in every session. That keeps the runtime surface stable and reduces drift between prompt behavior and the policy files.

Related files:

- [use-memories-api-assistant.md](../.github/skills/memories/assets/use-memories-api-assistant.md)
- [app/mcp_server.py](../app/mcp_server.py)

## MCP resource

The MCP resource is the policy surface. It is the right place to describe how the system should read, write, update, invalidate, and compare memories without forcing clients to parse tool descriptions.

The resource is assembled from the policy and query recipe reference files and exposed by the server implementation. That makes it useful as a stable, human-readable reference for clients, tools, and documentation that need a single source of behavioral truth.

Related files:

- [memories-tool-behavior-policy.md](../.github/skills/memories/references/memories-tool-behavior-policy.md)
- [memories-query-recipes.md](../.github/skills/memories/references/memories-query-recipes.md)
- [app/mcp_server.py](../app/mcp_server.py)

## Repository skill

The workspace skill is the maintainer-facing guide. It explains when the memory workflow should be used, how much autonomy is expected, and how the repository organizes the prompt, policy references, tool schemas, and helper scripts.

This is the best entry point when editing or reviewing the memory system in the repository because it groups the operational guidance with the supporting assets.

The skill should stay thin. Its main job is routing: tell maintainers or agents which surface to load next, instead of duplicating the full policy or recipe text.

## Skill file map

### Core guidance

- [SKILL.md](../.github/skills/memories/SKILL.md)

### Policy references

- [references/memories-tool-behavior-policy.md](../.github/skills/memories/references/memories-tool-behavior-policy.md)
- [references/memories-query-recipes.md](../.github/skills/memories/references/memories-query-recipes.md)

### Prompt asset

- [assets/use-memories-api-assistant.md](../.github/skills/memories/assets/use-memories-api-assistant.md)

### Helper scripts

- [scripts/validate_memories_skill.py](../.github/skills/memories/scripts/validate_memories_skill.py)
- [scripts/curl_examples.md](../.github/skills/memories/scripts/curl_examples.md)

The validation script is the maintainer-facing executable check for prompt and resource wiring. It verifies that the required skill files exist, that the MCP prompt and resource builders still load, and that the expected MCP surfaces remain registered.

The validation script is most useful as a quick smoke test after editing [app/mcp_server.py](../app/mcp_server.py), the prompt asset, or the policy references, because it exercises the actual tool workflow against a temporary database instead of only reprinting documentation.

The curl examples file is the better home for manual HTTP examples because it is easy to skim, easy to copy from, and does not pretend to be executable automation.

As a rule, the scripts directory should contain runnable checks or maintenance helpers that are useful after editing the memory workflow. Static examples and explanatory material belong in markdown files instead.

## Notes on current alignment

The implementation in [app/mcp_server.py](../app/mcp_server.py) wires the prompt and resource directly from the skill directory. That keeps the server behavior and the workspace guidance in sync and makes the documentation easier to maintain.

If the prompt, resource, or skill files change, update this document by adjusting the links and the short role descriptions rather than copying the underlying policy text.
