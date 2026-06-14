import pytest
from pydantic import ValidationError

from app.schemas import (
	DEFAULT_PAGE_LIMIT,
	MAX_MEMORY_CONTENT_CHARS,
	MAX_MEMORY_TAG_CHARS,
	MAX_MEMORY_TAGS,
	MAX_TEXT_FILTER_CHARS,
	Memory,
	MemoryCreate,
	MemoryListQuery,
	MemoryListResponse,
	MemoryUpdate,
	validate_tags_value,
)


def test_memory_create_applies_defaults():
	memory = MemoryCreate(content="Remember this", tags=["note"])

	assert memory.memory_type == "fact"
	assert memory.status == "active"


def test_memory_create_rejects_whitespace_only_content():
	with pytest.raises(ValidationError) as error:
		MemoryCreate(content="   ", tags=["note"])

	assert "content cannot be empty" in str(error.value)


def test_memory_create_rejects_content_over_character_limit():
	with pytest.raises(ValidationError) as error:
		MemoryCreate(content="x" * (MAX_MEMORY_CONTENT_CHARS + 1), tags=["note"])

	assert f"content cannot exceed {MAX_MEMORY_CONTENT_CHARS} characters" in str(error.value)


def test_validate_tags_value_rejects_blank_tag():
	with pytest.raises(ValueError, match="tags cannot contain empty strings"):
		validate_tags_value(["valid", "   "])


def test_validate_tags_value_rejects_too_many_tags():
	with pytest.raises(
		ValueError, match=f"tags cannot contain more than {MAX_MEMORY_TAGS} entries"
	):
		validate_tags_value([f"tag-{index}" for index in range(MAX_MEMORY_TAGS + 1)])


def test_validate_tags_value_rejects_tag_over_character_limit():
	with pytest.raises(ValueError, match=f"tags cannot exceed {MAX_MEMORY_TAG_CHARS} characters"):
		validate_tags_value(["x" * (MAX_MEMORY_TAG_CHARS + 1)])


def test_memory_update_allows_partial_payload():
	memory = MemoryUpdate(status="invalid")

	assert memory.content is None
	assert memory.status == "invalid"


def test_memory_update_rejects_extra_fields():
	with pytest.raises(ValidationError) as error:
		MemoryUpdate(status="active", version=2)

	assert "Extra inputs are not permitted" in str(error.value)


def test_memory_update_rejects_content_and_tags_over_limits():
	with pytest.raises(ValidationError) as error:
		MemoryUpdate(
			content="x" * (MAX_MEMORY_CONTENT_CHARS + 1),
			tags=["x" * (MAX_MEMORY_TAG_CHARS + 1)],
		)

	message = str(error.value)
	assert f"content cannot exceed {MAX_MEMORY_CONTENT_CHARS} characters" in message
	assert f"tags cannot exceed {MAX_MEMORY_TAG_CHARS} characters" in message


def test_memory_list_query_applies_defaults():
	query = MemoryListQuery()

	assert query.sort == "id"
	assert query.limit == DEFAULT_PAGE_LIMIT
	assert query.offset == 0
	assert query.status is None
	assert query.memory_type is None
	assert query.tag is None
	assert query.q is None


def test_memory_list_query_rejects_unknown_sort_value():
	with pytest.raises(ValidationError) as error:
		MemoryListQuery(sort="score")

	assert "Input should be 'id', 'created_at', 'updated_at' or 'last_accessed_at'" in str(
		error.value
	)


def test_memory_list_query_rejects_invalid_limit_and_offset():
	with pytest.raises(ValidationError) as error:
		MemoryListQuery(limit=0, offset=-1)

	message = str(error.value)
	assert "greater than or equal to 1" in message
	assert "greater than or equal to 0" in message


def test_memory_list_query_validates_status_memory_type_and_text_filters():
	query = MemoryListQuery(
		status="active",
		memory_type="identity",
		tag=" python ",
		q=" fastapi ",
	)

	assert query.status == "active"
	assert query.memory_type == "identity"
	assert query.tag == "python"
	assert query.q == "fastapi"


def test_memory_list_query_rejects_blank_tag_or_query():
	with pytest.raises(ValidationError) as error:
		MemoryListQuery(tag="   ", q=" ")

	assert "filter cannot be empty" in str(error.value)


def test_memory_list_query_rejects_text_filters_over_character_limit():
	with pytest.raises(ValidationError) as error:
		MemoryListQuery(tag="x" * (MAX_TEXT_FILTER_CHARS + 1), q="y" * (MAX_TEXT_FILTER_CHARS + 1))

	assert f"filter cannot exceed {MAX_TEXT_FILTER_CHARS} characters" in str(error.value)


def test_memory_list_response_requires_non_negative_counts():
	memory = Memory(
		id=1,
		content="Remember this",
		tags=["note"],
		created_at="2026-04-06T14:12:00.000000Z",
		updated_at="2026-04-06T14:12:00.000000Z",
		last_accessed_at=None,
		memory_type="fact",
		status="active",
		version=1,
	)

	response = MemoryListResponse(
		items=[memory],
		total=1,
		limit=10,
		offset=0,
		has_more=False,
	)

	assert response.total == 1
	assert response.items[0].id == 1

	with pytest.raises(ValidationError) as error:
		MemoryListResponse(items=[memory], total=-1, limit=10, offset=0, has_more=False)

	assert "greater than or equal to 0" in str(error.value)
