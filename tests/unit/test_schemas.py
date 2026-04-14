import pytest
from pydantic import ValidationError

from app.schemas import MemoryCreate, MemoryUpdate, validate_tags_value


def test_memory_create_applies_defaults():
	memory = MemoryCreate(content="Remember this", tags=["note"])

	assert memory.memory_type == "fact"
	assert memory.status == "active"


def test_memory_create_rejects_whitespace_only_content():
	with pytest.raises(ValidationError) as error:
		MemoryCreate(content="   ", tags=["note"])

	assert "content cannot be empty" in str(error.value)


def test_validate_tags_value_rejects_blank_tag():
	with pytest.raises(ValueError, match="tags cannot contain empty strings"):
		validate_tags_value(["valid", "   "])


def test_memory_update_allows_partial_payload():
	memory = MemoryUpdate(status="archived")

	assert memory.content is None
	assert memory.status == "archived"


def test_memory_update_rejects_extra_fields():
	with pytest.raises(ValidationError) as error:
		MemoryUpdate(status="active", version=2)

	assert "Extra inputs are not permitted" in str(error.value)
