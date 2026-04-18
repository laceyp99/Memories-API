import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def get_database_file_path() -> Path:
	configured_path = os.getenv("MEMORIES_DB_FILE") or os.getenv("MEMORIES_DATA_FILE")
	if configured_path:
		return Path(configured_path)
	return ROOT_DIR / "data.db"


def get_data_file_path() -> Path:
	return get_database_file_path()
