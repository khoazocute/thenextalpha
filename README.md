# TheNextAlpha

OptiBot mini-clone pipeline for the take-home test. It scrapes OptiSigns support articles, normalizes them into Markdown, uploads changed documents to a Gemini File Search store through API, and validates an assistant answer with cited `Article URL` lines.

## Setup

```bash
pip install -r requirements.txt
cp .env.sample .env
python create_gemini_store.py
```

Fill `.env` with:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=<your Gemini API key>
GEMINI_FILE_SEARCH_STORE_NAME=<printed by create_gemini_store.py>
SUPPORT_BASE_URL=https://support.optisigns.com
MAX_ARTICLES=50
```

## Run Locally

```bash
python main.py
```

`main.py` runs once and exits. It re-scrapes the Help Center through the Zendesk API, writes clean Markdown files to `data/articles`, computes SHA256 hashes, classifies articles as `added`, `updated`, or `skipped`, and uploads only changed files.

## Assistant Check

```bash
python ask_gemini.py
```

This asks the required sanity-check question: `How do I add a YouTube video?` The script calls Gemini with the `file_search` tool and the File Search store created by API. The answer must use uploaded docs and cite `Article URL` lines.

System prompt:

```text
You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
```

## Upload Strategy

Markdown files are uploaded programmatically through Gemini API; no UI drag-and-drop is used. Current upload summary: 50 Markdown files and 165 estimated chunks. Chunking uses whitespace chunks with 512 max tokens and 100 token overlap. See `data/gemini_upload_summary.json`.

## Docker

```bash
docker build -t thenextalpha .
docker run --env-file .env thenextalpha
```

## Daily Job

Deployed as a Render Cron Job. Logs: https://dashboard.render.com/cron/crn-d94khpho3t8c739688gg/logs?r=live

## Screenshot

Assistant answer screenshot: `screenshots/optibot-youtube-answer.png`
