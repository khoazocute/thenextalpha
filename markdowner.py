"""Convert support article HTML into clean Markdown files."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from scraper import Article


SLUG_MAX_LENGTH = 80


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:SLUG_MAX_LENGTH].strip("-") or "article"


def _clean_html(html: str, base_url: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    for link in soup.find_all("a", href=True):
        link["href"] = urljoin(base_url, link["href"])

    return str(soup)


def article_to_markdown(article: Article, base_url: str) -> str:
    cleaned_html = _clean_html(article.body, base_url)
    body_markdown = md(
        cleaned_html,
        heading_style="ATX",
        bullets="-",
        code_language="",
        strip=["span"],
    )
    body_markdown = re.sub(r"\n{3,}", "\n\n", body_markdown).strip()

    return f"""---
Title: {article.title}
Article URL: {article.url}
Article ID: {article.id}
Updated At: {article.updated_at}
---

# {article.title}

{body_markdown}
""".strip() + "\n"


def article_filename(article: Article) -> str:
    return f"{slugify(article.title)}-{article.id}.md"


def write_article_markdown(article: Article, base_url: str, output_dir: Path) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    content = article_to_markdown(article, base_url)
    path = output_dir / article_filename(article)
    path.write_text(content, encoding="utf-8")
    return path, content
