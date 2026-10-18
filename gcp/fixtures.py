"""Read the canonical JSON-compatible JavaScript fixture without executing it."""
import json
import re
from pathlib import Path


def load_fixture(path: Path | None = None) -> dict:
    path = path or Path(__file__).resolve().parent.parent / "retail_data.js"
    if not path.exists():
        path = Path(__file__).with_name("static") / "retail_data.js"
    match = re.search(r"const RETAIL_DATA\s*=\s*(\{.*\})\s*;?\s*$", path.read_text(encoding="utf-8"), re.S)
    if not match:
        raise ValueError("retail_data.js must contain one JSON-compatible RETAIL_DATA object")
    return json.loads(match.group(1))
