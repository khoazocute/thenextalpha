"""Create a Gemini File Search store and print its resource name."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from gemini_uploader import create_file_search_store


ROOT = Path(__file__).resolve().parent


def main() -> None:
    load_dotenv(ROOT / ".env", override=True, encoding="utf-8-sig")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Missing GEMINI_API_KEY in .env")

    display_name = os.getenv("GEMINI_FILE_SEARCH_STORE_DISPLAY_NAME", "thenextalpha-support-docs")
    embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2")

    client = genai.Client(api_key=api_key)
    store_name = create_file_search_store(client, display_name, embedding_model)

    print("Created Gemini File Search store:")
    print(store_name)
    print("\nPut this into .env:")
    print(f"GEMINI_FILE_SEARCH_STORE_NAME={store_name}")


if __name__ == "__main__":
    main()


