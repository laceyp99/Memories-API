from fastapi.testclient import TestClient


def test_search_endpoint_is_removed(client: TestClient):
	response = client.get("/search", params={"query": "python"})

	assert response.status_code == 404
