#!/usr/bin/env python3
"""Example: query memories via the HTTP API."""

import json

import requests

URL = "http://localhost:8000/memories"

# Example create a memory - adjust as needed
create_data = {"content": "Remember to buy milk", "tags": ["shopping", "reminder"]}
create_resp = requests.post(URL, json=create_data)
print(create_resp.status_code)
try:
	print(json.dumps(create_resp.json(), indent=2))
except Exception:
	print(create_resp.text)

# Example query parameters - adjust as needed
query_params = {"memory_type": "preference", "limit": 5}
resp = requests.get(URL, params=query_params)
print(resp.status_code)
try:
	print(json.dumps(resp.json(), indent=2))
except Exception:
	print(resp.text)

# Example update to a memory - adjust as needed
update_data = {"content": "Updated memory content", "tags": ["updated", "example"]}
memory_id = 1  # Replace with the actual memory ID you want to update
update_resp = requests.put(f"{URL}/{memory_id}", json=update_data)
print(update_resp.status_code)
try:
	print(json.dumps(update_resp.json(), indent=2))
except Exception:
	print(update_resp.text)

# Example delete a memory - adjust as needed
delete_resp = requests.delete(f"{URL}/{memory_id}")
print(delete_resp.status_code)
try:
	print(json.dumps(delete_resp.json(), indent=2))
except Exception:
	print(delete_resp.text)
