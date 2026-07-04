"""Ask the Gemini File Search-backed assistant a sample question."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai


ROOT = Path(__file__).resolve().parent
SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 \"Article URL:\" lines per reply."""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    load_dotenv(ROOT / ".env", override=True, encoding="utf-8-sig")
    api_key = os.getenv("GEMINI_API_KEY")
    store_name = os.getenv("GEMINI_FILE_SEARCH_STORE_NAME")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    if not api_key:
        raise SystemExit("Missing GEMINI_API_KEY in .env")
    if not store_name:
        raise SystemExit("Missing GEMINI_FILE_SEARCH_STORE_NAME in .env")

    client = genai.Client(api_key=api_key)
    question = "How do I add a YouTube video?"
    print(f"Asking Gemini: {question}", flush=True)
    print("Waiting for File Search response...", flush=True)

    interaction = client.interactions.create(
        model=model,
        input=f"{SYSTEM_PROMPT}\n\nUser question: {question}",
        tools=[{
            "type": "file_search",
            "file_search_store_names": [store_name],
        }],
    )

    cited_files: list[str] = []
    for step in interaction.steps:
        if step.type != "model_output":
            continue
        for content_block in step.content:
            if content_block.type == "text":
                print(content_block.text)
                for annotation in content_block.annotations or []:
                    if annotation.type == "file_citation" and annotation.file_name not in cited_files:
                        cited_files.append(annotation.file_name)

    if cited_files:
        print("\nCited files:")
        for file_name in cited_files[:3]:
            print(f"- {file_name}")


if __name__ == "__main__":
    main()
