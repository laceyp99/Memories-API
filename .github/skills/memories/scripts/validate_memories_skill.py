#!/usr/bin/env python3
"""Run focused smoke checks for the memories MCP workflow."""

from __future__ import annotations

import asyncio
import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]

EXPECTED_TOOL_SYMBOLS = [
	"record_memory",
	"revise_memory",
	"retire_memory",
	"inspect_memory",
	"search_memories",
	"prime_memory_context",
]

EXPECTED_PROMPT_NAME = "use_memories_api"
EXPECTED_RESOURCE_URI = "memories://policy/tool-behavior"


def record(result: bool, label: str, failures: list[str]) -> None:
	status = "PASS" if result else "FAIL"
	print(f"[{status}] {label}")
	if not result:
		failures.append(label)


def load_mcp_server():
	if str(ROOT_DIR) not in sys.path:
		sys.path.insert(0, str(ROOT_DIR))
	return importlib.import_module("app.mcp_server")


def validate_tool_symbols(mcp_server, failures: list[str]) -> None:
	for symbol in EXPECTED_TOOL_SYMBOLS:
		record(hasattr(mcp_server, symbol), f"Runtime symbol present: {symbol}", failures)


def validate_prompt_and_resource_builders(mcp_server, failures: list[str]) -> None:
	resource_text = mcp_server.build_memories_tool_behavior_resource()
	record(
		"# Memories Tool Behavior Policy" in resource_text,
		"Resource contains policy heading",
		failures,
	)
	record("# Query Recipes" in resource_text, "Resource contains query recipes heading", failures)
	record("search_memories" in resource_text, "Resource mentions search_memories", failures)
	record(
		"prime_memory_context" in resource_text,
		"Resource mentions prime_memory_context",
		failures,
	)

	messages = mcp_server.build_use_memories_api_prompt_messages()
	record(len(messages) == 1, "Prompt builder returns one assistant message", failures)
	if messages:
		content = messages[0].content.text
		record(messages[0].role == "assistant", "Prompt message role is assistant", failures)
		record(
			"memories-api MCP server" in content,
			"Prompt content mentions the MCP server",
			failures,
		)
		record(
			"Memory actions:" in content,
			"Prompt content includes transparency guidance",
			failures,
		)


def validate_registered_surfaces(mcp_server, failures: list[str]) -> None:
	resources = asyncio.run(mcp_server.mcp.list_resources())
	record(
		any(str(resource.uri) == EXPECTED_RESOURCE_URI for resource in resources),
		f"Registered resource exists: {EXPECTED_RESOURCE_URI}",
		failures,
	)

	prompts = asyncio.run(mcp_server.mcp.list_prompts())
	record(
		any(prompt.name == EXPECTED_PROMPT_NAME for prompt in prompts),
		f"Registered prompt exists: {EXPECTED_PROMPT_NAME}",
		failures,
	)

	prompt = asyncio.run(mcp_server.mcp.get_prompt(EXPECTED_PROMPT_NAME))
	record(len(prompt.messages) == 1, "Registered prompt resolves to one message", failures)

	contents = list(asyncio.run(mcp_server.mcp.read_resource(EXPECTED_RESOURCE_URI)))
	record(len(contents) == 1, "Registered resource resolves to one content block", failures)


def validate_tool_workflow(mcp_server, failures: list[str]) -> None:
	created = mcp_server.record_memory(
		content="User prefers concise answers",
		tags=["preference", "writing-style"],
		memory_type="preference",
	)
	memory_id = created["id"]
	record(created["status"] == "active", "Create tool returns an active memory", failures)
	record(created["memory_type"] == "preference", "Create tool preserves memory_type", failures)

	queried = mcp_server.search_memories(
		status="active",
		memory_type="preference",
		tag="writing-style",
		q="concise",
		sort="updated_at",
		limit=5,
		offset=0,
	)
	record(queried["total"] == 1, "Query tool returns the created memory", failures)
	record(len(queried["items"]) == 1, "Query tool returns one paged item", failures)
	record(
		queried["items"][0]["id"] == memory_id,
		"Query tool returns the expected memory id",
		failures,
	)

	read_back = mcp_server.inspect_memory(memory_id)
	record(read_back["id"] == memory_id, "Read tool returns the created memory", failures)

	updated = mcp_server.revise_memory(
		memory_id,
		content="User prefers concise technical answers",
	)
	record(
		updated["content"] == "User prefers concise technical answers",
		"Update tool persists new content",
		failures,
	)

	deleted = mcp_server.retire_memory(memory_id)
	record(deleted["status"] == "deleted", "Delete tool performs a soft delete", failures)

	deleted_page = mcp_server.search_memories(status="deleted", limit=5, offset=0)
	record(
		deleted_page["total"] == 1,
		"Deleted memories remain queryable by explicit status",
		failures,
	)

	try:
		mcp_server.inspect_memory(memory_id)
	except ValueError:
		record(True, "Read tool hides deleted memories from normal reads", failures)
	else:
		record(False, "Read tool hides deleted memories from normal reads", failures)


def main() -> int:
	failures: list[str] = []
	original_db_file = os.environ.get("MEMORIES_DB_FILE")
	temp_dir = Path(tempfile.mkdtemp())

	try:
		os.environ["MEMORIES_DB_FILE"] = str(temp_dir / "memories-skill-smoke.db")
		mcp_server = load_mcp_server()

		validate_tool_symbols(mcp_server, failures)
		validate_prompt_and_resource_builders(mcp_server, failures)
		validate_registered_surfaces(mcp_server, failures)
		validate_tool_workflow(mcp_server, failures)
	finally:
		shutil.rmtree(temp_dir, ignore_errors=True)

	if original_db_file is None:
		os.environ.pop("MEMORIES_DB_FILE", None)
	else:
		os.environ["MEMORIES_DB_FILE"] = original_db_file

	if failures:
		print()
		print("Smoke validation failed:")
		for failure in failures:
			print(f"- {failure}")
		return 1

	print()
	print("Memories MCP workflow smoke validation passed.")
	return 0


if __name__ == "__main__":
	sys.exit(main())
