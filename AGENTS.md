# AGENTS — Guidance for AI coding agents

This file documents the minimal, focused guidance an automated coding agent (or reviewer bot) needs to work productively in this repository.

Keep it short: link to the canonical docs for details rather than copying large sections. See [README.md](README.md) and the `/docs` folder for full policy and protocol descriptions.

## Quick actions

- **Environment (Windows PowerShell)**:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

- **Run API**:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

If you run into a port conflict, try an alternate port like `8010` or a more niche option like port `8192` (as also a nod to memory sizes).

- **Run MCP (stdio)**:

```powershell
python -m app.mcp_server
# or (if installed) the console script
memories-api-mcp
```

- **Run MCP inspector** (for streamable HTTP/dev UX):

```text
mcp dev app/mcp_server.py
```

- **Run tests and checks**:

```powershell
ruff format .
ruff check .
pytest
pre-commit run --all-files
```

CI: `.github/workflows/ci.yml` runs `python 3.12`, installs `.[dev]`, checks formatting (`ruff format --check .`), runs `ruff check .`, and runs `pytest`.

## Key responsibilities for agents

- Use the repository's test suite and formatting/linting hooks as the source of truth before suggesting or committing changes.
- Do not modify or commit local artifact files (SQLite files, `mcp_browser_clients.local.json`, `.env*`). CI will fail such changes (see `.github/workflows/ci.yml`).
- When changing MCP prompts, resources, or skill assets, run the skill smoke validator:

```text
python .github/skills/memories/scripts/validate_memories_skill.py
```

This script exercises the MCP prompt/resource builders and the in-process tool workflow against a temporary DB.

## Project layout (quick reference)

- **App entry & HTTP**: [app/main.py](app/main.py) — FastAPI app and HTTP routes.
- **MCP wiring**: [app/mcp_server.py](app/mcp_server.py) — FastMCP registration, prompts, resources, and tools.
- **Storage layer**: [app/storage.py](app/storage.py) — DB queries, deterministic retrieval, access-time updates.
- **DB helpers**: [app/db.py](app/db.py) — SQLite schema + `get_connection()` and `init_db()`.
- **Config & env**: [app/config.py](app/config.py) — `MEMORIES_DB_FILE` and `mcp_browser_clients.local.json` handling.
- **Package metadata / scripts**: [pyproject.toml](pyproject.toml) — project metadata, `memories-api-mcp` console script, ruff settings.
- **Skills & prompts**: `.github/skills/memories/` — MCP prompt, policy references, and validation scripts. See [SKILL.md](.github/skills/memories/SKILL.md).
- **Tests**: `tests/` — unit, integration, and contract tests. Tests use `tests/conftest.py` which sets `MEMORIES_DB_FILE` to a tmp file.

## Conventions and style

- **Python version**: `>=3.12` (CI uses 3.12).
- **Formatting & lint**: project uses `ruff` and `pre-commit` (see `.pre-commit-config.yaml` and `[tool.ruff]` in `pyproject.toml`).
- **Indentation**: tabs (see `tool.ruff.format.indent-style = "tab"`).
- **Line length**: 100 characters.

## Security & runtime notes

- The service is intended for local, single-user use. Do not bind the server to `0.0.0.0` or expose it publicly without adding authentication and transport security. See [README.md](README.md#security-model).
- `MEMORIES_DB_FILE` controls where the SQLite file is stored. Tests and the validate script set this to a temporary file automatically.
- Browser-based MCP clients require a local allowlist file: `mcp_browser_clients.local.json`. The repo provides `mcp_browser_clients.example.json` as a template.

## When editing core flows

- If you change the retrieval contract, DB schema, or `app/storage.py` behavior:
  - Update or add tests under `tests/` (unit + integration as appropriate).
  - Run `pytest` locally and fix failures before opening a PR.

- If you change MCP prompt/assets or resources:
  - Update the skill assets under `.github/skills/memories/`.
  - Run the skill smoke validator script above.

## Useful links

- Repository README: [README.md](README.md)
- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- CI workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)
- MCP skill: [.github/skills/memories/SKILL.md](.github/skills/memories/SKILL.md)
