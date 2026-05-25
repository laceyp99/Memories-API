from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import AssistantMessage

from app.schemas import MemoryCreate, MemoryListQuery, MemoryListResponse, MemoryUpdate
from app.storage import (
	create_memory,
	delete_memory,
	get_memories_page,
	get_memory,
	refresh_memories_last_accessed,
	update_memory,
)

mcp = FastMCP(
	"memories-api",
	stateless_http=True,
	json_response=True,
	streamable_http_path="/",
)

SKILL_DIR = Path(__file__).resolve().parent.parent / ".github" / "skills" / "memories"
REFERENCES_DIR = SKILL_DIR / "references"
ASSETS_DIR = SKILL_DIR / "assets"


def load_skill_reference(name: str) -> str:
	return (REFERENCES_DIR / name).read_text(encoding="utf-8").strip()


def load_skill_asset(name: str) -> str:
	return (ASSETS_DIR / name).read_text(encoding="utf-8").strip()


def build_memories_tool_behavior_resource() -> str:
	sections = [
		load_skill_reference("memories-tool-behavior-policy.md"),
		load_skill_reference("memories-query-recipes.md"),
	]
	return "\n\n".join(sections)


def build_use_memories_api_prompt_messages() -> list[AssistantMessage]:
	return [
		AssistantMessage(load_skill_asset("use-memories-api-assistant.md")),
	]


def serialize_memory(memory) -> dict:
	return memory.model_dump()


def _build_memory_page_response(query: MemoryListQuery) -> dict:
	paged_memories, total = get_memories_page(query)
	items = refresh_memories_last_accessed(paged_memories)

	return MemoryListResponse(
		items=items,
		total=total,
		limit=query.limit,
		offset=query.offset,
		has_more=query.offset + len(items) < total,
	).model_dump()


def _build_bootstrap_query(memory_type: str) -> MemoryListQuery:
	return MemoryListQuery(
		status="active",
		memory_type=memory_type,
		sort="updated_at",
		limit=10,
		offset=0,
	)


@mcp.resource(
	"memories://policy/tool-behavior",
	name="memories-tool-behavior-policy",
	description="Reference policy for using the memories API tools safely and consistently for recall, writes, and contradiction handling.",
	mime_type="text/markdown",
)
def memories_tool_behavior_resource() -> str:
	"""Return the tool-behavior policy and query recipes for the memories API."""
	return build_memories_tool_behavior_resource()


@mcp.prompt(
	name="use_memories_api",
	description="Prepare an agent to use the memories API MCP tools for personalization, durable recall, careful writes, and contradiction handling.",
)
def use_memories_api_prompt() -> list[AssistantMessage]:
	"""Return a static prompt for deliberate memories-api tool usage."""
	return build_use_memories_api_prompt_messages()


@mcp.tool(
	description="""Record a new durable memory when the user shares stable preference, identity,
project, or workflow information that should be available later. Use this after you have
decided the fact is worth keeping and you are not just capturing a one-off chat detail.
Keep the content atomic and concise, choose short literal tags that aid retrieval, and
confirm with the user before storing any sensitive material or anything that should be
tagged with sensitive, pii, or health. The tool creates a new memory and returns the stored
object so you can verify the content, tags, type, status, and server-managed metadata."""
)
def record_memory(
	content: str,
	tags: list[str],
	memory_type: str = "fact",
	status: str = "active",
) -> dict:
	"""Record a memory and return the stored object."""
	memory = create_memory(
		MemoryCreate(
			content=content,
			tags=tags,
			memory_type=memory_type,
			status=status,
		)
	)
	return serialize_memory(memory)


@mcp.tool(
	description="""Revise an existing memory when you have already found the right record and
the goal is to improve its wording, tags, type, or status without creating a duplicate.
Use this when the new statement is the same durable fact or preference, or when the current
record needs a small correction. Pass only the fields that actually need to change; omitted
fields stay untouched. If the new information conflicts with the current record, stop and
ask the user which version should remain authoritative before writing. The tool returns the
updated record, including the new version and updated timestamp, so you can confirm the change."""
)
def revise_memory(
	memory_id: int,
	content: str | None = None,
	tags: list[str] | None = None,
	memory_type: str | None = None,
	status: str | None = None,
) -> dict:
	"""Revise editable fields on an existing memory."""
	update_fields = {
		"content": content,
		"tags": tags,
		"memory_type": memory_type,
		"status": status,
	}
	memory = update_memory(
		memory_id,
		MemoryUpdate(**{key: value for key, value in update_fields.items() if value is not None}),
	)
	if memory is None:
		raise ValueError(f"Memory {memory_id} not found")
	return serialize_memory(memory)


@mcp.tool(
	description="""Retire a memory when it should no longer participate in normal recall but
should remain auditable. This performs a soft delete by changing the status to deleted rather
than removing the row, so it is safe for records that were stored in error, are no longer
relevant, or should be removed from active use after user confirmation. Use this only after
you have decided not to revise the memory instead. The tool returns the soft-deleted record
so you can confirm the final status and version."""
)
def retire_memory(memory_id: int) -> dict:
	"""Retire a memory by id and return the soft-deleted object."""
	memory = delete_memory(memory_id)
	if memory is None:
		raise ValueError(f"Memory {memory_id} not found")
	return serialize_memory(memory)


@mcp.tool(
	description="""Search the memory store with deterministic filtering and pagination when you
need targeted recall, deduping, or a follow-up read after bootstrap. Prefer structured
filters first (status, memory_type, and tag) and add one word q values only when lexical narrowing is
helpful. Use the smallest page that answers the question, because returned items are treated
as accessed and their access timestamps are refreshed. The tool returns the standard paginated
envelope with items, total, limit, offset, and has_more."""
)
def search_memories(
	status: str | None = None,
	memory_type: str | None = None,
	tag: str | None = None,
	q: str | None = None,
	sort: str = "id",
	limit: int = 10,
	offset: int = 0,
) -> dict:
	"""Search memories using the shared retrieval contract."""
	query = MemoryListQuery(
		status=status,
		memory_type=memory_type,
		tag=tag,
		q=q,
		sort=sort,
		limit=limit,
		offset=offset,
	)
	return _build_memory_page_response(query)


@mcp.tool(
	description="""Prime the working context at the start of a session or whenever you want the
default memory snapshot before broader reasoning. This tool performs the two canonical
startup recalls in one read-only call: active preferences and active identity memories, both
using the shared retrieval contract and small pages. Use it before other search calls so the
model can orient itself quickly without chaining two separate queries. The tool returns
separate preference and identity envelopes, making the next step obvious."""
)
def prime_memory_context() -> dict:
	"""Prime the working memory context with the startup snapshot."""
	preference_query = _build_bootstrap_query("preference")
	identity_query = _build_bootstrap_query("identity")

	return {
		"preferences": _build_memory_page_response(preference_query),
		"identities": _build_memory_page_response(identity_query),
	}


@mcp.tool(
	description="""Inspect a specific memory when you already know the memory ID and need the
full stored record. Use it for targeted verification, correction workflows, or a precise
read where broader recall would be unnecessary. Do not use it as a substitute for search
when you do not know which record matters. The tool returns the memory object and refreshes
its access timestamp because the record was surfaced to the caller."""
)
def inspect_memory(memory_id: int) -> dict:
	"""Inspect one memory by id and return the stored object."""
	memory = get_memory(memory_id)
	if memory is None:
		raise ValueError(f"Memory {memory_id} not found")
	return serialize_memory(memory)


def run_stdio() -> None:
	mcp.run()


def run() -> None:
	run_stdio()


if __name__ == "__main__":
	run_stdio()
