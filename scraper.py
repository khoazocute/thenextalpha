"""Fetch OptiSigns support articles from the public Zendesk Help Center API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass(frozen=True)
class Article:
    id: int
    title: str
    url: str
    body: str
    updated_at: str


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _get_json(url: str) -> dict:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_articles(base_url: str, max_articles: int) -> list[Article]:
    """Return up to max_articles public support articles from the Help Center API."""
    api_url = f"{base_url.rstrip('/')}/api/v2/help_center/en-us/articles.json?per_page=100"
    articles: list[Article] = []

    while api_url and len(articles) < max_articles:
        payload = _get_json(api_url)
        for item in payload.get("articles", []):
            if item.get("draft"):
                continue

            body = item.get("body") or ""
            url = item.get("html_url") or ""
            title = item.get("title") or f"article-{item.get('id')}"
            updated_at = item.get("updated_at") or ""

            articles.append(
                Article(
                    id=int(item["id"]),
                    title=title,
                    url=url,
                    body=body,
                    updated_at=updated_at,
                )
            )

            if len(articles) >= max_articles:
                break

        api_url = payload.get("next_page")

    return articles
