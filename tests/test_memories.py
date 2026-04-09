import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import storage


## Helper functions
def read_database(data_file: Path) -> list[dict]:
    return json.loads(data_file.read_text(encoding="utf-8"))


def expected_memory(
    memory_id: int,
    content: str,
    tags: list[str],
    *,
    created_at: str,
    updated_at: str,
    last_accessed_at: str | None,
    memory_type: str = "fact",
    status: str = "active",
    version: int = 1,
) -> dict:
    return {
        "id": memory_id,
        "content": content,
        "tags": tags,
        "created_at": created_at,
        "updated_at": updated_at,
        "last_accessed_at": last_accessed_at,
        "memory_type": memory_type,
        "status": status,
        "version": version,
    }


# POST /memories tests
def test_post_memory_returns_created_memory_with_defaults(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a POST request creates a memory with default values for
    - `created_at`
    - `updated_at`
    - `last_accessed_at`
    fields because they are server-managed fields.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamp = "2026-04-06T14:12:00.000000Z"
    monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

    response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )

    expected = expected_memory(
        1,
        "Learning FastAPI testing",
        ["python", "api"],
        created_at=timestamp,
        updated_at=timestamp,
        last_accessed_at=None,
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == [expected]


def test_post_memory_accepts_optional_memory_type_and_status(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a POST request creates a memory with optional
    - `memory_type`
    - `status`
    fields included within the request.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamp = "2026-04-06T14:12:00.000000Z"
    monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

    response = client.post(
        "/memories",
        json={
            "content": "User prefers concise responses",
            "tags": ["preference", "writing-style"],
            "memory_type": "preference",
            "status": "archived",
        },
    )

    expected = expected_memory(
        1,
        "User prefers concise responses",
        ["preference", "writing-style"],
        created_at=timestamp,
        updated_at=timestamp,
        last_accessed_at=None,
        memory_type="preference",
        status="archived",
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == [expected]


def test_post_memory_handles_memory_missing_tags(client: TestClient, data_file: Path):
    """
    Testing if a POST request with missing `tags` field returns a 422 error
    with the correct validation message.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
    """
    response = client.post("/memories", json={"content": "Learning FastAPI testing"})

    assert response.status_code == 422
    body = response.json()
    assert any(
        error["loc"] == ["body", "tags"] and error["type"] == "missing"
        for error in body["detail"]
    )
    assert read_database(data_file) == []


def test_post_memory_handles_memory_missing_content(
    client: TestClient, data_file: Path
):
    """
    Testing if a POST request with missing `content` field returns a 422 error
    with the correct validation message.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
    """
    response = client.post("/memories", json={"tags": ["python", "api"]})

    assert response.status_code == 422
    body = response.json()
    assert any(
        error["loc"] == ["body", "content"] and error["type"] == "missing"
        for error in body["detail"]
    )
    assert read_database(data_file) == []


def test_post_memory_rejects_invalid_memory_type(client: TestClient, data_file: Path):
    """
    Testing if a POST request with an invalid `memory_type` field returns a 422 error
    with the correct validation message.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
    """

    response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
            "memory_type": "unknown",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert any(
        error["loc"] == ["body", "memory_type"]
        and "memory_type must be one of" in error["msg"]
        for error in body["detail"]
    )
    assert read_database(data_file) == []


def test_post_memory_rejects_invalid_status(client: TestClient, data_file: Path):
    """
    Testing if a POST request with an invalid `status` field returns a 422 error
    with the correct validation message.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
    """
    response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
            "status": "pending",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert any(
        error["loc"] == ["body", "status"] and "status must be one of" in error["msg"]
        for error in body["detail"]
    )
    assert read_database(data_file) == []


def test_post_memory_rejects_server_managed_fields(client: TestClient, data_file: Path):
    """
    Testing if a POST request with server-managed fields returns a 422 error
    with the correct validation message.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
    """
    response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
            "created_at": "2026-04-06T14:12:00.000000Z",
            "updated_at": "2026-04-06T14:12:00.000000Z",
            "last_accessed_at": "2026-04-06T14:12:00.000000Z",
            "version": 99,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert any(
        error["loc"] == ["body", "created_at"] and error["type"] == "extra_forbidden"
        for error in body["detail"]
    )
    assert any(
        error["loc"] == ["body", "version"] and error["type"] == "extra_forbidden"
        for error in body["detail"]
    )
    assert read_database(data_file) == []


## POST /memories/batch tests
def test_post_memory_batch_returns_created_memories_with_defaults(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a POST request to the /memories/batch endpoint creates
    multiple memories with default values for:
    - `created_at`
    - `updated_at`
    - `last_accessed_at`
    fields because they are server-managed fields.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """

    timestamps = iter(
        [
            "2026-04-06T14:12:00.000000Z",
            "2026-04-06T14:13:00.000000Z",
            "2026-04-06T14:14:00.000000Z",
        ]
    )
    monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

    response = client.post(
        "/memories/batch",
        json=[
            {
                "content": "Learning FastAPI testing",
                "tags": ["python", "api"],
            },
            {
                "content": "Practicing SQL joins and query optimization",
                "tags": ["database", "sql"],
                "memory_type": "task_context",
            },
            {
                "content": "Building a CLI tool with argparse",
                "tags": ["python", "tooling"],
                "status": "superseded",
            },
        ],
    )

    expected = [
        expected_memory(
            1,
            "Learning FastAPI testing",
            ["python", "api"],
            created_at="2026-04-06T14:12:00.000000Z",
            updated_at="2026-04-06T14:12:00.000000Z",
            last_accessed_at=None,
        ),
        expected_memory(
            2,
            "Practicing SQL joins and query optimization",
            ["database", "sql"],
            created_at="2026-04-06T14:13:00.000000Z",
            updated_at="2026-04-06T14:13:00.000000Z",
            last_accessed_at=None,
            memory_type="task_context",
        ),
        expected_memory(
            3,
            "Building a CLI tool with argparse",
            ["python", "tooling"],
            created_at="2026-04-06T14:14:00.000000Z",
            updated_at="2026-04-06T14:14:00.000000Z",
            last_accessed_at=None,
            status="superseded",
        ),
    ]

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == expected


## GET /memories tests
def test_get_memories_empty_returns_empty_list(client: TestClient, data_file: Path):
    """
    Testing if a GET request to the /memories endpoint returns an empty list
    when there are no memories in the database.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
    """
    response = client.get("/memories")

    assert response.status_code == 200
    assert response.json() == []
    assert read_database(data_file) == []


def test_get_memories_returns_expanded_shape_without_updating_access_time(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a GET request to the /memories endpoint returns memories
    with the expanded shape.
    Including
    - `created_at`
    - `updated_at`
    - `last_accessed_at`
    fields without modifying the `last_accessed_at` timestamp.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamp = "2026-04-06T14:12:00.000000Z"
    monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )
    assert create_response.status_code == 200

    response = client.get("/memories")

    expected = [
        expected_memory(
            1,
            "Learning FastAPI testing",
            ["python", "api"],
            created_at=timestamp,
            updated_at=timestamp,
            last_accessed_at=None,
        )
    ]

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == expected


## GET /memories/{id} tests
def test_get_memory_by_id_updates_last_accessed_at(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a GET request to the /memories/{id} endpoint updates
    the `last_accessed_at` timestamp.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamps = iter(
        [
            "2026-04-06T14:12:00.000000Z",
            "2026-04-06T14:20:00.000000Z",
        ]
    )
    monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )
    assert create_response.status_code == 200

    response = client.get("/memories/1")

    expected = expected_memory(
        1,
        "Learning FastAPI testing",
        ["python", "api"],
        created_at="2026-04-06T14:12:00.000000Z",
        updated_at="2026-04-06T14:12:00.000000Z",
        last_accessed_at="2026-04-06T14:20:00.000000Z",
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == [expected]


def test_get_memory_by_id_not_found_returns_404(client: TestClient, data_file: Path):
    """
    Testing if a GET request to the /memories/{id} endpoint returns a 404 status
    code when the memory is not found.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
    """
    response = client.get("/memories/1")

    assert response.status_code == 404
    assert response.json() == {"detail": "Memory not found"}
    assert read_database(data_file) == []


## PATCH /memories/{id} tests
def test_patch_memory_by_id_updates_fields_and_increments_version(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a PATCH request to the /memories/{id} endpoint updates
    the memory fields and increments the version.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamps = iter(
        [
            "2026-04-06T14:12:00.000000Z",
            "2026-04-06T14:25:00.000000Z",
        ]
    )
    monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )
    assert create_response.status_code == 200

    response = client.patch(
        "/memories/1",
        json={
            "content": "Practicing SQL joins and query optimization",
            "tags": ["database", "sql"],
            "memory_type": "task_context",
            "status": "archived",
        },
    )

    expected = expected_memory(
        1,
        "Practicing SQL joins and query optimization",
        ["database", "sql"],
        created_at="2026-04-06T14:12:00.000000Z",
        updated_at="2026-04-06T14:25:00.000000Z",
        last_accessed_at=None,
        memory_type="task_context",
        status="archived",
        version=2,
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == [expected]


def test_patch_memory_by_id_partial_data_preserves_untouched_fields(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a PATCH request to the /memories/{id} endpoint with partial data
    updates only the provided fields and preserves the untouched fields.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamps = iter(
        [
            "2026-04-06T14:12:00.000000Z",
            "2026-04-06T14:30:00.000000Z",
        ]
    )
    monkeypatch.setattr(storage, "current_timestamp", lambda: next(timestamps))

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
            "memory_type": "instruction",
            "status": "active",
        },
    )
    assert create_response.status_code == 200

    response = client.patch(
        "/memories/1", json={"content": "Practicing FastAPI testing"}
    )

    expected = expected_memory(
        1,
        "Practicing FastAPI testing",
        ["python", "api"],
        created_at="2026-04-06T14:12:00.000000Z",
        updated_at="2026-04-06T14:30:00.000000Z",
        last_accessed_at=None,
        memory_type="instruction",
        status="active",
        version=2,
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == [expected]


def test_patch_memory_by_id_no_op_does_not_change_updated_at_or_version(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a PATCH request to the /memories/{id} endpoint with no changes
    does not update the `updated_at` timestamp or increment the version.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    create_timestamp = "2026-04-06T14:12:00.000000Z"
    monkeypatch.setattr(storage, "current_timestamp", lambda: create_timestamp)

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )
    assert create_response.status_code == 200

    monkeypatch.setattr(
        storage,
        "current_timestamp",
        lambda: (_ for _ in ()).throw(
            AssertionError("PATCH should not refresh timestamps")
        ),
    )

    response = client.patch(
        "/memories/1",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )

    expected = expected_memory(
        1,
        "Learning FastAPI testing",
        ["python", "api"],
        created_at=create_timestamp,
        updated_at=create_timestamp,
        last_accessed_at=None,
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == [expected]


def test_patch_memory_rejects_invalid_status(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a PATCH request to the /memories/{id} endpoint with an invalid
    `status` field returns a 422 error with the correct validation message.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamp = "2026-04-06T14:12:00.000000Z"
    monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )
    assert create_response.status_code == 200

    response = client.patch("/memories/1", json={"status": "pending"})

    assert response.status_code == 422
    body = response.json()
    assert any(
        error["loc"] == ["body", "status"] and "status must be one of" in error["msg"]
        for error in body["detail"]
    )
    assert read_database(data_file) == [
        expected_memory(
            1,
            "Learning FastAPI testing",
            ["python", "api"],
            created_at=timestamp,
            updated_at=timestamp,
            last_accessed_at=None,
        )
    ]


def test_patch_memory_rejects_server_managed_fields(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a PATCH request to the /memories/{id} endpoint with server-managed
    fields returns a 422 error with the correct validation message.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamp = "2026-04-06T14:12:00.000000Z"
    monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )
    assert create_response.status_code == 200

    response = client.patch(
        "/memories/1",
        json={
            "updated_at": "2026-04-06T15:00:00.000000Z",
            "version": 99,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert any(
        error["loc"] == ["body", "updated_at"] and error["type"] == "extra_forbidden"
        for error in body["detail"]
    )
    assert any(
        error["loc"] == ["body", "version"] and error["type"] == "extra_forbidden"
        for error in body["detail"]
    )
    assert read_database(data_file) == [
        expected_memory(
            1,
            "Learning FastAPI testing",
            ["python", "api"],
            created_at=timestamp,
            updated_at=timestamp,
            last_accessed_at=None,
        )
    ]


## DELETE /memories/{id} tests
def test_delete_memory_by_id_returns_deleted_memory_with_full_shape(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a DELETE request to the /memories/{id} endpoint returns the
    deleted memory with the full shape.
    Including:
    - `created_at`
    - `updated_at`
    - `last_accessed_at`
    fields and removes it from the database.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamp = "2026-04-06T14:12:00.000000Z"
    monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )
    assert create_response.status_code == 200

    response = client.delete("/memories/1")

    expected = expected_memory(
        1,
        "Learning FastAPI testing",
        ["python", "api"],
        created_at=timestamp,
        updated_at=timestamp,
        last_accessed_at=None,
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == []


## GET /search tests
def test_search_memories_returns_expanded_shape(
    client: TestClient, data_file: Path, monkeypatch
):
    """
    Testing if a GET request to the /search endpoint returns memories with
    the expanded shape.
    Including:
    - `created_at`
    - `updated_at`
    - `last_accessed_at`
    fields without modifying the `last_accessed_at` timestamp.

    Args:
        client (TestClient): The TestClient for making requests to the FastAPI app.
        data_file (Path): The Path for accessing the test database file.
        monkeypatch: The MonkeyPatch for modifying attributes during tests.
    """
    timestamp = "2026-04-06T14:12:00.000000Z"
    monkeypatch.setattr(storage, "current_timestamp", lambda: timestamp)

    create_response = client.post(
        "/memories",
        json={
            "content": "Learning FastAPI testing",
            "tags": ["python", "api"],
        },
    )
    assert create_response.status_code == 200

    response = client.get("/search", params={"query": "python"})

    expected = [
        expected_memory(
            1,
            "Learning FastAPI testing",
            ["python", "api"],
            created_at=timestamp,
            updated_at=timestamp,
            last_accessed_at=None,
        )
    ]

    assert response.status_code == 200
    assert response.json() == expected
    assert read_database(data_file) == expected
