from mcp.server.fastmcp import FastMCP

from app.schemas import MemoryCreate, MemoryUpdate
from app.storage import (
	create_memory,
	delete_memory,
	get_memories,
	get_memory,
	search_memories,
	update_memory,
)


mcp = FastMCP("memories-api")


def serialize_memory(memory) -> dict:
	return memory.model_dump()


@mcp.tool()
def list_memories() -> list[dict]:
	"""Return all stored memories."""
	return [serialize_memory(memory) for memory in get_memories()]


@mcp.tool()
def read_memory(memory_id: int) -> dict:
	"""Return one memory by id."""
	memory = get_memory(memory_id)
	if memory is None:
		raise ValueError(f"Memory {memory_id} not found")
	return serialize_memory(memory)


@mcp.tool()
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


@mcp.tool()
def update_memory_tool(
	memory_id: int,
	content: str | None = None,
	tags: list[str] | None = None,
	memory_type: str | None = None,
	status: str | None = None,
) -> dict:
	"""Update editable fields on an existing memory."""
	memory = update_memory(
		memory_id,
		MemoryUpdate(
			content=content,
			tags=tags,
			memory_type=memory_type,
			status=status,
		),
	)
	if memory is None:
		raise ValueError(f"Memory {memory_id} not found")
	return serialize_memory(memory)


@mcp.tool()
def delete_memory_tool(memory_id: int) -> dict:
	"""Delete a memory by id and return the removed object."""
	memory = delete_memory(memory_id)
	if memory is None:
		raise ValueError(f"Memory {memory_id} not found")
	return serialize_memory(memory)


@mcp.tool()
def search_memories_tool(query: str) -> list[dict]:
	"""Search memories by content or tag."""
	return [serialize_memory(memory) for memory in search_memories(query)]


def run() -> None:
	mcp.run()


if __name__ == "__main__":
	run()
