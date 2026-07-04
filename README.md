# TheNextAlpha

Daily job that scrapes OptiSigns support articles, converts them to Markdown, and syncs changed documents into a Google Gemini File Search store for an OptiBot-style assistant.

## Setup

```bash
pip install -r requirements.txt
cp .env.sample .env
python create_gemini_store.py
```

Fill `.env` with `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, the printed `GEMINI_FILE_SEARCH_STORE_NAME`, `SUPPORT_BASE_URL=https://support.optisigns.com`, and `MAX_ARTICLES=50`.

## Run Locally

```bash
python main.py
```

The job re-scrapes articles, writes clean Markdown to `data/articles`, detects `added`, `updated`, and `skipped` articles with SHA256 hashes, and uploads only added/updated files.

## Gemini Assistant

The assistant is configured with Gemini File Search through the API. Markdown files are uploaded programmatically; no UI drag-and-drop is used.

```bash
python ask_gemini.py
```

Sanity check question: `How do I add a YouTube video?`

System prompt:

```text
You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
```

## Upload And Chunking

Current Gemini File Search store: `fileSearchStores/thenextalphasupportdocs-7hb7sxfsodpn`.

Last successful Gemini upload: 50 Markdown files, estimated 165 chunks. Chunking uses whitespace chunks with 512 max tokens and 100 token overlap. See `data/gemini_upload_summary.json` and `data/last_run.json`.

## Docker

```bash
docker build -t thenextalpha .
docker run --env-file .env thenextalpha
```

## Daily Job

Logs: TODO

## Screenshot

Assistant answer screenshot: `screenshots/optibot-youtube-answer.png`
