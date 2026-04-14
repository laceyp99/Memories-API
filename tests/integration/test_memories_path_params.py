from pathlib import Path

from fastapi.testclient import TestClient
from helpers.database_helpers import read_database


def test_get_memory_by_id_rejects_non_integer_id(client: TestClient, data_file: Path):
	response = client.get("/memories/abc")

	assert response.status_code == 422
	body = response.json()
	assert any(error["loc"] == ["path", "memory_id"] for error in body["detail"])
	assert read_database(data_file) == []


def test_patch_memory_by_id_rejects_non_integer_id(client: TestClient, data_file: Path):
	response = client.patch("/memories/abc", json={"content": "Updated content"})

	assert response.status_code == 422
	body = response.json()
	assert any(error["loc"] == ["path", "memory_id"] for error in body["detail"])
	assert read_database(data_file) == []


def test_delete_memory_by_id_rejects_non_integer_id(client: TestClient, data_file: Path):
	response = client.delete("/memories/abc")

	assert response.status_code == 422
	body = response.json()
	assert any(error["loc"] == ["path", "memory_id"] for error in body["detail"])
	assert read_database(data_file) == []
