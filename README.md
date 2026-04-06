# Memories API

A small FastAPI project for storing memories with tags in a JSON database.

## Project layout

```text
app/
	__init__.py
	config.py
	main.py
	schemas.py
	storage.py
tests/
	conftest.py
	test_memories.py
.github/workflows/ci.yml
data.json
pyproject.toml
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Run the API

```powershell
uvicorn app.main:app --reload
```

Interactive docs are available at `http://127.0.0.1:8000/docs`.

## Run tests

```powershell
pytest
```

## Format and lint

```powershell
ruff format .
ruff check .
```

## Example requests

Create a memory:

```bash
curl -X POST http://127.0.0.1:8000/memories \
	-H "Content-Type: application/json" \
	-d '{"content":"Learning FastAPI testing","tags":["python","api"]}'
```

Create multiple memories:

```bash
curl -X POST http://127.0.0.1:8000/memories/batch \
	-H "Content-Type: application/json" \
	-d '[
		{"content":"Learning FastAPI testing","tags":["python","api"]},
		{"content":"Practicing SQL joins","tags":["database","sql"]}
	]'
```

Get all memories:

```bash
curl http://127.0.0.1:8000/memories
```

Get one memory by id:

```bash
curl http://127.0.0.1:8000/memories/1
```

Update a memory:

```bash
curl -X PATCH http://127.0.0.1:8000/memories/1 \
	-H "Content-Type: application/json" \
	-d '{"content":"Practicing FastAPI testing"}'
```

Delete a memory:

```bash
curl -X DELETE http://127.0.0.1:8000/memories/1
```

Search memories by text or tag:

```bash
curl "http://127.0.0.1:8000/search?query=python"
```

## CI

GitHub Actions runs formatting, linting, and tests on every push and pull request using the workflow in `.github/workflows/ci.yml`.