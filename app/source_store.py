import json
import os
from datetime import datetime
from app.config import CHROMA_PERSIST_DIR

SOURCES_FILE = os.path.join(os.path.dirname(CHROMA_PERSIST_DIR), "sources.json")


def _load() -> list[dict]:
    if not os.path.exists(SOURCES_FILE):
        return []
    try:
        with open(SOURCES_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save(sources: list[dict]):
    os.makedirs(os.path.dirname(SOURCES_FILE), exist_ok=True)
    with open(SOURCES_FILE, "w") as f:
        json.dump(sources, f, indent=2)


def add_source(name: str, source_type: str, chunks: int, url: str = ""):
    sources = _load()
    sources.append({
        "name": name,
        "type": source_type,
        "chunks": chunks,
        "url": url,
        "added_at": datetime.now().isoformat(),
    })
    _save(sources)


def get_all_sources() -> list[dict]:
    return _load()


def delete_source(name: str) -> bool:
    sources = _load()
    new_sources = [s for s in sources if s["name"] != name]
    if len(new_sources) == len(sources):
        return False
    _save(new_sources)
    return True


def clear_all_sources():
    _save([])
