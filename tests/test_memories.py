import json
from pathlib import Path


def read_database(data_file: Path) -> list[dict]:
    return json.loads(data_file.read_text(encoding="utf-8"))


def test_post_memory_returns_created_memory(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        }
    ]


def test_post_memory_handles_memory_missing_tags(client, data_file: Path):
    payload = {"content": "Learning FastAPI testing"}

    response = client.post("/memories", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(
        error["loc"] == ["body", "tags"] and error["type"] == "missing"
        for error in body["detail"]
    )
    assert read_database(data_file) == []


def test_post_memory_handles_memory_missing_content(client, data_file: Path):
    payload = {"tags": ["python", "api"]}

    response = client.post("/memories", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(
        error["loc"] == ["body", "content"] and error["type"] == "missing"
        for error in body["detail"]
    )
    assert read_database(data_file) == []


def test_post_memory_handles_memory_with_empty_content(client, data_file: Path):
    payload = {
        "content": "",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(
        error["loc"] == ["body", "content"]
        and "content cannot be empty" in error["msg"]
        for error in body["detail"]
    )
    assert read_database(data_file) == []


def test_post_memory_handles_memory_with_wrong_tag_type(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": "python",
    }

    response = client.post("/memories", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(
        error["loc"] == ["body", "tags"] and error["type"] == "list_type"
        for error in body["detail"]
    )
    assert read_database(data_file) == []


def test_post_memory_batch_returns_created_memories(client, data_file: Path):
    payload = [
        {
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
        {
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]

    response = client.post("/memories/batch", json=payload)

    assert response.status_code == 200

    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "id": 2,
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "id": 2,
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]


def test_get_memories_empty_returns_empty_list(client, data_file: Path):
    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == []
    assert read_database(data_file) == []


def test_get_memories_after_create_returns_list_with_memory(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        }
    ]
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        }
    ]


def test_get_memory_by_id_returns_correct_memory(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.get("/memories/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        }
    ]


def test_get_memory_by_id_not_found_returns_404(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.get("/memories/2")

    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found"}
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        }
    ]


def test_get_memory_by_id_returns_requested_memory_when_multiple_exist(
    client, data_file: Path
):
    payload = [
        {
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
        {
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]

    response = client.post("/memories/batch", json=payload)
    assert response.status_code == 200

    response = client.get("/memories/2")

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "content": "Practicing SQL joins and query optimization",
        "tags": ["database", "sql"],
    }
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "id": 2,
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]


def test_patch_memory_by_id_returns_correct_memory(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.patch(
        "/memories/1",
        json={
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Practicing SQL joins and query optimization",
        "tags": ["database", "sql"],
    }
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        }
    ]


def test_patch_memory_by_id_partial_data_returns_correct_memory(
    client, data_file: Path
):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.patch(
        "/memories/1", json={"content": "Practicing FastAPI testing"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Practicing FastAPI testing",
        "tags": ["python", "api"],
    }
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Practicing FastAPI testing",
            "tags": ["python", "api"],
        }
    ]


def test_patch_memory_by_id_not_found_returns_404(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.patch(
        "/memories/2",
        json={
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found"}
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        }
    ]


def test_patch_memory_by_id_returns_correct_memory_when_multiple(
    client, data_file: Path
):
    payload = [
        {
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
        {
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]

    response = client.post("/memories/batch", json=payload)
    assert response.status_code == 200

    response = client.patch(
        "/memories/2",
        json={
            "content": "Understanding Docker containers and images",
            "tags": ["devops", "docker"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "content": "Understanding Docker containers and images",
        "tags": ["devops", "docker"],
    }
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "id": 2,
            "content": "Understanding Docker containers and images",
            "tags": ["devops", "docker"],
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]


def test_delete_memory_by_id_returns_deleted_memory(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.delete("/memories/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }
    assert read_database(data_file) == []


def test_delete_memory_by_id_not_found_returns_404(client, data_file: Path):
    payload = {
        "content": "Learning FastAPI testing",
        "tags": ["python", "api"],
    }

    response = client.post("/memories", json=payload)
    assert response.status_code == 200

    response = client.delete("/memories/2")

    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found"}
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        }
    ]


def test_delete_memory_by_id_returns_deleted_memory_when_multiple(
    client, data_file: Path
):
    payload = [
        {
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
        },
        {
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]

    response = client.post("/memories/batch", json=payload)
    assert response.status_code == 200

    response = client.delete("/memories/2")

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "content": "Practicing SQL joins and query optimization",
        "tags": ["database", "sql"],
    }
    assert read_database(data_file) == [
        {
            "id": 1,
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
        {
            "id": 3,
            "content": "Building a CLI tool with argparse",
            "tags": ["python", "tooling"],
        },
    ]
