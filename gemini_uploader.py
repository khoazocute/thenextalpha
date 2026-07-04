"""Upload changed Markdown files to a Gemini File Search store."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai


@dataclass(frozen=True)
class GeminiUploadResult:
    file_search_store_name: str
    document_name: str | None
    estimated_chunks: int


def estimate_chunks(markdown: str, chunk_tokens: int = 512) -> int:
    approx_tokens = max(1, math.ceil(len(markdown.split()) * 1.3))
    return max(1, math.ceil(approx_tokens / chunk_tokens))


def wait_for_operation(client: genai.Client, operation: Any, poll_seconds: int = 5) -> Any:
    while not getattr(operation, "done", False):
        time.sleep(poll_seconds)
        operation = client.operations.get(operation)
    return operation


def create_file_search_store(client: genai.Client, display_name: str, embedding_model: str) -> str:
    store = client.file_search_stores.create(
        config={
            "display_name": display_name,
            "embedding_model": embedding_model,
        }
    )
    return store.name


def upload_markdown_file(
    client: genai.Client,
    file_search_store_name: str,
    path: Path,
    markdown: str,
) -> GeminiUploadResult:
    operation = client.file_search_stores.upload_to_file_search_store(
        file=str(path),
        file_search_store_name=file_search_store_name,
        config={
            "display_name": path.name,
            "chunking_config": {
                "white_space_config": {
                    "max_tokens_per_chunk": 512,
                    "max_overlap_tokens": 100,
                }
            },
        },
    )
    operation = wait_for_operation(client, operation)

    if getattr(operation, "error", None):
        raise RuntimeError(f"Gemini failed to index {path.name}: {operation.error}")

    response = getattr(operation, "response", None)
    document_name = getattr(response, "name", None) if response else None

    return GeminiUploadResult(
        file_search_store_name=file_search_store_name,
        document_name=document_name,
        estimated_chunks=estimate_chunks(markdown),
    )

