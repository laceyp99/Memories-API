from fastapi.testclient import TestClient
from src.main import app
import json

client = TestClient(app)

def reset_database():
    with open("data.json", "w") as file:
        json.dump([], file)

# For each endpoint, ask:

# what is the happy path?
# what are the invalid inputs?
# what are the edge cases?
# should this endpoint mutate data?
# what should happen if the target resource does not exist?

# POST Endpoint

## POST /memories
### Test that POST memory creates memory correctly
def test_post_memory_returns_created_memory():
    reset_database()
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        }
    ]

### Test that POST handles empty/partial memory request data
#### Test POST with a missing tag key
def test_post_memory_handles_memory_missing_tags():
    reset_database()
    payload = {
        "content": "Learning FastAPI testing"
    }
    response = client.post("/memories", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(error["loc"] == ["body", "tags"] and error["type"] == "missing" for error in body["detail"])

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    assert stored_data == []

#### Test POST with a missing content key
def test_post_memory_handles_memory_missing_content():
    reset_database()
    payload = {
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(error["loc"] == ["body", "content"] and error["type"] == "missing" for error in body["detail"])

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    assert stored_data == []

#### Test POST with a empty string for the value of content 
def test_post_memory_handles_memory_with_empty_content():
    reset_database()
    payload = {
        "content": "",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(error["loc"] == ["body", "content"] and "content cannot be empty" in error["msg"] for error in body["detail"])

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    assert stored_data == []

#### Test POST with a wrong data type for the value of tags 
def test_post_memory_handles_memory_with_wrong_tag_type():
    reset_database()
    payload = {
        "content": "Learning FastAPI testing",
        "tags": "python"
    }
    response = client.post("/memories", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(error["loc"] == ["body", "tags"] and error["type"] == "list_type" for error in body["detail"])
    with open("data.json", "r") as file:
        stored_data = json.load(file)
    assert stored_data == []

### Test that POST handles picking the right next id number? (scenarios where id number gaps exist)

## POST /memories/batch
### Test that POST memory batch creates memory correctly
def test_post_memory_batch_returns_created_memories():
    reset_database()
    payload = [
        {
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"]
        },
        {
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]
    response = client.post("/memories/batch", json=payload)
    assert response.status_code == 200

    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "id": 2,
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"]
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "id": 2,
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"]
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]

### Test that POST handles empty/partial memories in request data
### Test that POST handles picking the right next id numbers? (scenarios where id number gaps exist)

# GET Endpoint

## GET /memories
### Test GET memories on an empty database
def test_get_memories_empty_returns_empty_list():
    reset_database()
    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == []

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    assert stored_data == []

### Test GET memories on a database with an existing data point
def test_get_memories_after_create_returns_list_with_memory():
    reset_database()
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        }
    ]

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        }
    ]

### Test GET memories returns a list of multiple memories?

## GET /memory/{memory_id}
### Test GET memory by id returns the right data
def test_get_memory_by_id_returns_correct_memory():
    reset_database()

    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.get("/memories/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        }
    ]

### Test GET memory by id returns errors when the id doesn't exist
def test_get_memory_by_id_not_found_returns_404():
    reset_database()
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.get("/memories/2")

    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found"}

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        }
    ]

### Test GET memory by id returns the right data from the correct id
def test_get_memory_by_id_returns_requested_memory_when_multiple_exist():
    reset_database()
    payload = [
        {
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"]
        },
        {
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]
    response = client.post("/memories/batch", json=payload)
    assert response.status_code == 200

    response = client.get("/memories/2")

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "content": "Practicing SQL joins and query optimization",
        "tags": ["database", "sql"]
    }

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "id": 2,
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"]
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]

# PATCH Endpoint

## PATCH /memories/{memory_id}
### Test that PATCH returns patched memory (and persistence!)
def test_patch_memory_by_id_returns_correct_memory():
    reset_database()

    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.patch("/memories/1", json={"content": "Practicing SQL joins and query optimization", "tags": ["database", "sql"]})

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Practicing SQL joins and query optimization", 
        "tags": ["database", "sql"]
    }

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Practicing SQL joins and query optimization", 
            "tags": ["database", "sql"]
        }
    ]

### Test that PATCH handles partial memory data (with proper persistence!)
def test_patch_memory_by_id_partial_data_returns_correct_memory():
    reset_database()

    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.patch("/memories/1", json={"content": "Practicing FastAPI testing"})

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Practicing FastAPI testing", 
        "tags": ["python", "api"]
    }

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Practicing FastAPI testing", 
            "tags": ["python", "api"]
        }
    ]

### Test PATCH when id not found
def test_patch_memory_by_id_not_found_returns_404():
    reset_database()
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.patch("/memories/2", json={"content": "Practicing SQL joins and query optimization", "tags": ["database", "sql"]})

    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found"}

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        }
    ]

### Test that PATCH patches the right memory based on the id, when multiple exist
def test_patch_memory_by_id_returns_correct_memory_when_multiple():
    reset_database()
    payload = [
        {
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"]
        },
        {
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]
    response = client.post("/memories/batch", json=payload)
    assert response.status_code == 200

    response = client.patch("/memories/2", json={"content": "Understanding Docker containers and images", "tags": ["devops", "docker"]})

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "content": "Understanding Docker containers and images",
        "tags": ["devops", "docker"]
    }

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "id": 2,
            "content": "Understanding Docker containers and images",
            "tags": ["devops", "docker"]
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]

# DELETE Endpoint

## DELETE /memories/{memory_id}
### Test that DELETE returns deleted memory (and persistence!)
def test_delete_memory_by_id_returns_deleted_memory():
    reset_database()

    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.delete("/memories/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == []

### Test DELETE when id not found
def test_delete_memory_by_id_not_found_returns_404():
    reset_database()
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"]
    }
    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.delete("/memories/2")

    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found"}

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        }
    ]

### Test that DELETE deletes the right memory based on the id, when multiple exist
def test_delete_memory_by_id_returns_deleted_memory():
    reset_database()

    payload = [
        {
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"]
        },
        {
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]
    response = client.post("/memories/batch", json=payload)
    assert response.status_code == 200

    response = client.delete("/memories/2")

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "content": "Practicing SQL joins and query optimization",
        "tags": ["database", "sql"]
    }

    with open("data.json", "r") as file:
        stored_data = json.load(file)
    
    assert stored_data == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"]
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"]
        }
    ]