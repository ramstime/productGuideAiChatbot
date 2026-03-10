import json
import os
from app.config import CHROMA_PERSIST_DIR

CHAT_FILE = os.path.join(os.path.dirname(CHROMA_PERSIST_DIR), "chat_history.json")


def _load() -> list[dict]:
    if not os.path.exists(CHAT_FILE):
        return []
    try:
        with open(CHAT_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save(history: list[dict]):
    os.makedirs(os.path.dirname(CHAT_FILE), exist_ok=True)
    with open(CHAT_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_chat_history() -> list[dict]:
    return _load()


def append_messages(user_msg: str, assistant_msg: str):
    history = _load()
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": assistant_msg})
    _save(history)


def clear_chat_history():
    _save([])
