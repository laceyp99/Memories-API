from pydantic import BaseModel, ConfigDict, field_validator

ALLOWED_MEMORY_TYPES = {
    "preference",
    "fact",
    "goal",
    "identity",
    "instruction",
    "task_context",
    "event",
}
ALLOWED_STATUSES = {"active", "archived", "superseded", "invalid", "deleted"}


def validate_content_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("content must be a string")
    if not value.strip():
        raise ValueError("content cannot be empty")
    return value


def validate_tags_value(value: list[str]) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("tags must be a list of strings")
    if not value:
        raise ValueError("tags cannot be empty")
    for tag in value:
        if not isinstance(tag, str):
            raise ValueError("each tag must be a string")
        if not tag.strip():
            raise ValueError("tags cannot contain empty strings")
    return value


def validate_memory_type_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("memory_type must be a string")
    if value not in ALLOWED_MEMORY_TYPES:
        raise ValueError(
            "memory_type must be one of: " + ", ".join(sorted(ALLOWED_MEMORY_TYPES))
        )
    return value


def validate_status_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("status must be a string")
    if value not in ALLOWED_STATUSES:
        raise ValueError(
            "status must be one of: " + ", ".join(sorted(ALLOWED_STATUSES))
        )
    return value


class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    tags: list[str]
    memory_type: str = "fact"
    status: str = "active"

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return validate_content_value(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return validate_tags_value(value)

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, value: str) -> str:
        return validate_memory_type_value(value)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return validate_status_value(value)


class MemoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str | None = None
    tags: list[str] | None = None
    memory_type: str | None = None
    status: str | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_content_value(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return validate_tags_value(value)

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_memory_type_value(value)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_status_value(value)


class Memory(BaseModel):
    id: int
    content: str
    tags: list[str]
    created_at: str
    updated_at: str
    last_accessed_at: str | None
    memory_type: str
    status: str
    version: int
