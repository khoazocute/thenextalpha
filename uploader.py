"""Upload changed Markdown files to an OpenAI vector store."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class UploadResult:
    openai_file_id: str
    vector_store_file_id: str
    estimated_chunks: int


def estimate_chunks(markdown: str, chunk_tokens: int = 800) -> int:
    # A practical estimate for README/logging because OpenAI manages actual chunking internally.
    approx_tokens = max(1, math.ceil(len(markdown.split()) * 1.3))
    return max(1, math.ceil(approx_tokens / chunk_tokens))


def _wait_for_vector_store_file(client: OpenAI, vector_store_id: str, vector_store_file_id: str) -> Any:
    while True:
        item = client.vector_stores.files.retrieve(
            vector_store_id=vector_store_id,
            file_id=vector_store_file_id,
        )
        status = getattr(item, "status", None)
        if status in {"completed", "failed", "cancelled"}:
            return item
        time.sleep(2)


def remove_previous_file(client: OpenAI, vector_store_id: str, previous: dict[str, Any] | None) -> None:
    if not previous:
        return

    vector_store_file_id = previous.get("vector_store_file_id")
    openai_file_id = previous.get("openai_file_id")

    if vector_store_file_id:
        try:
            client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=vector_store_file_id,
            )
        except Exception as exc:  # best-effort cleanup should not block fresh upload
            print(f"Warning: could not delete previous vector store file {vector_store_file_id}: {exc}")

    if openai_file_id:
        try:
            client.files.delete(openai_file_id)
        except Exception as exc:
            print(f"Warning: could not delete previous OpenAI file {openai_file_id}: {exc}")


def upload_markdown_file(client: OpenAI, vector_store_id: str, path: Path, markdown: str) -> UploadResult:
    with path.open("rb") as handle:
        uploaded_file = client.files.create(file=handle, purpose="assistants")

    vector_store_file = client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=uploaded_file.id,
    )
    completed = _wait_for_vector_store_file(client, vector_store_id, vector_store_file.id)

    if getattr(completed, "status", None) != "completed":
        raise RuntimeError(f"OpenAI failed to process {path.name}: status={getattr(completed, 'status', None)}")

    return UploadResult(
        openai_file_id=uploaded_file.id,
        vector_store_file_id=vector_store_file.id,
        estimated_chunks=estimate_chunks(markdown),
    )
