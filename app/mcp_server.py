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
	description="Create a new memory. Use this to store new information that you want to remember. Make sure the content is concise and informative, and use tags to categorize the memory for easy retrieval later."
)
def create_memory_tool(
	content: str,
	tags: list[str],
	memory_type: str = "fact",
	status: str = "active",
) -> dict:
	"""Create a memory and return the stored object."""
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
	description="Update an existing memory. Use this to modify the content, tags, type, or status of a memory you have previously created."
)
def update_memory_tool(
	memory_id: int,
	content: str | None = None,
	tags: list[str] | None = None,
	memory_type: str | None = None,
	status: str | None = None,
) -> dict:
	"""Update editable fields on an existing memory."""
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
	description="Delete a memory by its ID. Use this to remove a memory you no longer need or find irrelevant/untrue."
)
def delete_memory_tool(memory_id: int) -> dict:
	"""Delete a memory by id and return the removed object."""
	memory = delete_memory(memory_id)
	if memory is None:
		raise ValueError(f"Memory {memory_id} not found")
	return serialize_memory(memory)


@mcp.tool(
	description="Query memories with optional filters, free-text matching, deterministic sorting, and pagination. Use this to retrieve memories by status, type, tag, or q and inspect the paginated result envelope."
)
def query_memories_tool(
	status: str | None = None,
	memory_type: str | None = None,
	tag: str | None = None,
	q: str | None = None,
	sort: str = "id",
	limit: int = 10,
	offset: int = 0,
) -> dict:
	"""Query memories using the same retrieval contract as the HTTP API."""
	query = MemoryListQuery(
		status=status,
		memory_type=memory_type,
		tag=tag,
		q=q,
		sort=sort,
		limit=limit,
		offset=offset,
	)
	paged_memories, total = get_memories_page(query)
	items = refresh_memories_last_accessed(paged_memories)

	return MemoryListResponse(
		items=items,
		total=total,
		limit=query.limit,
		offset=query.offset,
		has_more=query.offset + len(items) < total,
	).model_dump()


@mcp.tool(
	description="Read a memory by its ID. Use this only when you know the ID of the memory you want to read."
)
def read_memory(memory_id: int) -> dict:
	"""Return one memory by id."""
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
