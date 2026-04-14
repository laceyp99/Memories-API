import json
from pathlib import Path


def read_database(data_file: Path) -> list[dict]:
	return json.loads(data_file.read_text(encoding="utf-8"))
