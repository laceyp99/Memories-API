from pydantic import BaseModel, field_validator


class MemoryCreate(BaseModel):
    content: str
    tags: list[str]

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content cannot be empty")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("tags cannot be empty")
        return value


class MemoryUpdate(BaseModel):
    content: str | None = None
    tags: list[str] | None = None


class Memory(BaseModel):
    id: int
    content: str
    tags: list[str]
