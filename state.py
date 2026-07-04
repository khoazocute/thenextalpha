"""Load, compare, and save article sync state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


State = dict[str, dict[str, Any]]


def load_state(path: Path) -> State:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def classify_article(state: State, article_id: int, content_hash: str) -> str:
    existing = state.get(str(article_id))
    if existing is None:
        return "added"
    if existing.get("hash") != content_hash:
        return "updated"
    return "skipped"
