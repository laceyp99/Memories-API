from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json

class MemoryCreate(BaseModel):
    content: str
    tags: list[str] = Field(default_factory=list)

class MemoryUpdate(BaseModel):
    content: str | None = None
    tags: list[str] | None = None

class Memory(BaseModel):
    id: int
    content: str
    tags: list[str] = Field(default_factory=list)

def find_next_id(data: list) -> int:
    largest_id = 0
    for item in data:
        if item.get("id", 0) > largest_id:
            largest_id = item["id"]
    next_id = largest_id + 1
    return next_id

app = FastAPI()

@app.post("/memories")
async def post_memory(memory: MemoryCreate) -> Memory:
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        data = []
    except json.JSONDecodeError as e:
        print(f"ERROR: {e}")
        data = []

    
    id = find_next_id(data)
    memory = Memory(id=id, content=memory.content, tags=memory.tags)
    data.append(memory.model_dump())

    with open("data.json", "w") as file:
        json.dump(data, file)
    
    return memory

@app.post("/memories/batch")
async def post_memory_batch(memories: list[MemoryCreate]) -> list[Memory]:
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        data = []
    except json.JSONDecodeError as e:
        print(f"ERROR: {e}")
        data = []

    created_memories = []
    id = find_next_id(data)
    for memory in memories:
        new_memory = Memory(id=id, content=memory.content, tags=memory.tags)
        data.append(new_memory.model_dump())
        created_memories.append(new_memory)
        id += 1

    with open("data.json", "w") as file:
        json.dump(data, file)
    
    return created_memories 

@app.get("/memories")
async def get_memories() -> list[Memory]:
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        data = []
    except json.JSONDecodeError as e:
        print(f"ERROR: {e}")
        data = []
    return [Memory(**item) for item in data]

@app.get("/memories/{memory_id}")
async def get_memory_by_id(memory_id: int):
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        data = []
    except json.JSONDecodeError as e:
        print(f"ERROR: {e}")
        data = []
    for item in data:
        if item["id"] == memory_id:
            return Memory(**item)
    else:
        raise HTTPException(status_code=404, detail="Memory not found")

@app.patch("/memories/{memory_id}")
async def patch_memory_by_id(memory_id: int, memory: MemoryUpdate):
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        data = []
    except json.JSONDecodeError as e:
        print(f"ERROR: {e}")
        data = []
    update_data = memory.model_dump(exclude_unset=True)
    for i, item in enumerate(data):
        if item["id"] == memory_id:
            item.update(update_data)
            patch = Memory(**item)
            data[i] = patch.model_dump()

            with open("data.json", "w") as file:
                json.dump(data, file)

            return patch
    else:
        raise HTTPException(status_code=404, detail="Memory not found")

@app.delete("/memories/{memory_id}")
async def delete_memory_by_id(memory_id: int):
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        data = []
    except json.JSONDecodeError as e:
        print(f"ERROR: {e}")
        data = []
    for i, item in enumerate(data):
        if item["id"] == memory_id:
            deleted = Memory(**item)
            data.pop(i)

            with open("data.json", "w") as file:
                json.dump(data, file)
            
            return deleted
    else:
        raise HTTPException(status_code=404, detail="Memory not found")

@app.get("/search")
async def search_memories(query: str) -> list[Memory]:
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        data = []
    except json.JSONDecodeError as e:
        print(f"ERROR: {e}")
        data = []

    query_lower = query.lower()
    results = []

    for item in data:
        memory = Memory(**item)

        content_match = query_lower in memory.content.lower()
        tags_match = any(query_lower in tag.lower() for tag in memory.tags)

        if content_match or tags_match:
            results.append(memory)

    return results