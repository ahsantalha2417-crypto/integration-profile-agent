"""Fetch partner API documentation and reduce it to plain text for the model."""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

MAX_CHARS = 60_000  # keep prompts a reasonable size


def html_to_text(html: str, max_chars: int = MAX_CHARS) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "svg"]):
        tag.decompose()
    lines = (line.strip() for line in soup.get_text("\n").splitlines())
    text = "\n".join(line for line in lines if line)
    return text[:max_chars]


def fetch_docs(url: str, timeout: int = 20) -> str:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "integration-profile-agent/0.1"})
    resp.raise_for_status()
    if "html" in resp.headers.get("content-type", ""):
        return html_to_text(resp.text)
    return resp.text[:MAX_CHARS]
