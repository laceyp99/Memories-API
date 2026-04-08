import json
from datetime import UTC, datetime

from app.config import get_data_file_path
from app.schemas import Memory, MemoryCreate, MemoryUpdate


def current_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def find_next_id(data: list[dict]) -> int:
    largest_id = 0
    for item in data:
        if item.get("id", 0) > largest_id:
            largest_id = item["id"]
    return largest_id + 1


def load_data() -> list[dict]:
    data_file = get_data_file_path()
    try:
        with data_file.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def save_data(data: list[dict]) -> None:
    data_file = get_data_file_path()
    data_file.parent.mkdir(parents=True, exist_ok=True)
    with data_file.open("w", encoding="utf-8") as file:
        json.dump(data, file)


def create_memory(memory: MemoryCreate) -> Memory:
    data = load_data()
    timestamp = current_timestamp()
    new_memory = Memory(
        id=find_next_id(data),
        content=memory.content,
        tags=memory.tags,
        created_at=timestamp,
        updated_at=timestamp,
        last_accessed_at=None,
        memory_type=memory.memory_type,
        status=memory.status,
        version=1,
    )
    data.append(new_memory.model_dump())
    save_data(data)
    return new_memory


def create_memory_batch(memories: list[MemoryCreate]) -> list[Memory]:
    data = load_data()
    created_memories: list[Memory] = []
    next_id = find_next_id(data)

    for memory in memories:
        timestamp = current_timestamp()
        new_memory = Memory(
            id=next_id,
            content=memory.content,
            tags=memory.tags,
            created_at=timestamp,
            updated_at=timestamp,
            last_accessed_at=None,
            memory_type=memory.memory_type,
            status=memory.status,
            version=1,
        )
        data.append(new_memory.model_dump())
        created_memories.append(new_memory)
        next_id += 1

    save_data(data)
    return created_memories


def get_memories() -> list[Memory]:
    return [Memory(**item) for item in load_data()]


def get_memory(memory_id: int) -> Memory | None:
    data = load_data()

    for index, item in enumerate(data):
        if item["id"] == memory_id:
            item["last_accessed_at"] = current_timestamp()
            memory = Memory(**item)
            data[index] = memory.model_dump()
            save_data(data)
            return memory
    return None


def update_memory(memory_id: int, memory: MemoryUpdate) -> Memory | None:
    data = load_data()
    update_data = memory.model_dump(exclude_unset=True)

    for index, item in enumerate(data):
        if item["id"] == memory_id:
            has_changes = any(
                item.get(key) != value for key, value in update_data.items()
            )
            if not has_changes:
                return Memory(**item)

            item.update(update_data)
            item["updated_at"] = current_timestamp()
            item["version"] += 1
            updated_memory = Memory(**item)
            data[index] = updated_memory.model_dump()
            save_data(data)
            return updated_memory

    return None


def delete_memory(memory_id: int) -> Memory | None:
    data = load_data()

    for index, item in enumerate(data):
        if item["id"] == memory_id:
            deleted_memory = Memory(**item)
            data.pop(index)
            save_data(data)
            return deleted_memory

    return None


def search_memories(query: str) -> list[Memory]:
    query_lower = query.lower()
    results: list[Memory] = []

    for item in load_data():
        memory = Memory(**item)
        content_match = query_lower in memory.content.lower()
        tags_match = any(query_lower in tag.lower() for tag in memory.tags)
        if content_match or tags_match:
            results.append(memory)

    return results
