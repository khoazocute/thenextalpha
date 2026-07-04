"""Daily OptiBot knowledge-base sync job.

Runs once, then exits. This is the command used locally, in Docker, and by the daily cron job.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from openai import OpenAI

from gemini_uploader import upload_markdown_file as upload_gemini_markdown_file
from markdowner import write_article_markdown
from scraper import fetch_articles
from state import classify_article, load_state, save_state, sha256_text
from uploader import remove_previous_file, upload_markdown_file as upload_openai_markdown_file


ROOT = Path(__file__).resolve().parent
ARTICLES_DIR = ROOT / "data" / "articles"
STATE_PATH = ROOT / "data" / "state.json"
LAST_RUN_PATH = ROOT / "data" / "last_run.json"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _has_provider_upload(record: dict | None, provider: str) -> bool:
    if not record:
        return False
    if provider == "gemini":
        return bool(record.get("gemini_file_search_store_name"))
    return bool(record.get("openai_file_id") and record.get("vector_store_file_id"))


def _copy_existing_upload(record: dict, previous: dict | None, provider: str) -> None:
    if not previous:
        return
    if provider == "gemini" and _has_provider_upload(previous, provider):
        record["gemini_file_search_store_name"] = previous["gemini_file_search_store_name"]
        if previous.get("gemini_document_name"):
            record["gemini_document_name"] = previous["gemini_document_name"]
    elif provider == "openai" and _has_provider_upload(previous, provider):
        record["openai_file_id"] = previous["openai_file_id"]
        record["vector_store_file_id"] = previous["vector_store_file_id"]


def main() -> None:
    load_dotenv(ROOT / ".env", override=True, encoding="utf-8-sig")

    provider = os.getenv("AI_PROVIDER", "openai").strip().lower()
    base_url = os.getenv("SUPPORT_BASE_URL", "https://support.optisigns.com")
    max_articles = _env_int("MAX_ARTICLES", 50)

    openai_vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
    openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_store_name = os.getenv("GEMINI_FILE_SEARCH_STORE_NAME")

    openai_client = None
    gemini_client = None
    if provider == "openai" and openai_api_key and openai_vector_store_id:
        openai_client = OpenAI(api_key=openai_api_key)
    elif provider == "gemini" and gemini_api_key and gemini_store_name:
        gemini_client = genai.Client(api_key=gemini_api_key)

    state = load_state(STATE_PATH)
    articles = fetch_articles(base_url, max_articles)

    added = 0
    updated = 0
    skipped = 0
    pending_upload = 0
    uploaded = 0
    failed = 0
    estimated_chunks = 0
    changed_items: list[dict] = []

    for index, article in enumerate(articles, start=1):
        path, markdown = write_article_markdown(article, base_url, ARTICLES_DIR)
        content_hash = sha256_text(markdown)
        article_id = str(article.id)
        previous = state.get(article_id)
        status = classify_article(state, article.id, content_hash)
        has_upload = _has_provider_upload(previous, provider)
        client_ready = bool(openai_client or gemini_client)
        needs_upload = status != "skipped" or bool(client_ready and not has_upload)

        if status == "added":
            added += 1
        elif status == "updated":
            updated += 1
        else:
            skipped += 1
            if needs_upload:
                pending_upload += 1

        record = {
            "title": article.title,
            "url": article.url,
            "updated_at": article.updated_at,
            "hash": content_hash,
            "path": str(path.relative_to(ROOT)),
            "provider": provider,
        }

        if needs_upload and provider == "gemini" and gemini_client and gemini_store_name:
            try:
                print(f"[{index}/{len(articles)}] Uploading to Gemini: {path.name}", flush=True)
                result = upload_gemini_markdown_file(gemini_client, gemini_store_name, path, markdown)
                record["gemini_file_search_store_name"] = result.file_search_store_name
                if result.document_name:
                    record["gemini_document_name"] = result.document_name
                estimated_chunks += result.estimated_chunks
                uploaded += 1
                print(f"[{index}/{len(articles)}] Uploaded to Gemini: {path.name}", flush=True)
            except Exception as exc:
                failed += 1
                record["upload_error"] = str(exc)
                print(f"Upload failed for {path.name}: {exc}", flush=True)
        elif needs_upload and provider == "openai" and openai_client and openai_vector_store_id:
            try:
                print(f"[{index}/{len(articles)}] Uploading to OpenAI: {path.name}", flush=True)
                if status == "updated" or _has_provider_upload(previous, provider):
                    remove_previous_file(openai_client, openai_vector_store_id, previous)
                result = upload_openai_markdown_file(openai_client, openai_vector_store_id, path, markdown)
                record["openai_file_id"] = result.openai_file_id
                record["vector_store_file_id"] = result.vector_store_file_id
                estimated_chunks += result.estimated_chunks
                uploaded += 1
                print(f"[{index}/{len(articles)}] Uploaded to OpenAI: {path.name}", flush=True)
            except Exception as exc:
                failed += 1
                record["upload_error"] = str(exc)
                print(f"Upload failed for {path.name}: {exc}", flush=True)
        elif previous and _has_provider_upload(previous, provider):
            _copy_existing_upload(record, previous, provider)
        elif needs_upload:
            record["upload_skipped"] = f"Missing credentials/store for provider={provider}"

        state[article_id] = record
        save_state(STATE_PATH, state)

        if status != "skipped" or needs_upload:
            changed_items.append({"id": article.id, "title": article.title, "status": status, "path": record["path"]})

    summary = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "articles_seen": len(articles),
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "pending_upload": pending_upload,
        "uploaded": uploaded,
        "failed": failed,
        "estimated_chunks": estimated_chunks,
        "openai_vector_store_id": openai_vector_store_id if provider == "openai" else None,
        "gemini_file_search_store_name": gemini_store_name if provider == "gemini" else None,
        "changed_items": changed_items,
    }
    LAST_RUN_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Run completed")
    print(f"Provider: {provider}")
    print(f"Articles seen: {summary['articles_seen']}")
    print(f"Added: {added}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Pending upload: {pending_upload}")
    print(f"Uploaded: {uploaded}")
    print(f"Failed: {failed}")
    print(f"Estimated chunks: {estimated_chunks}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()


