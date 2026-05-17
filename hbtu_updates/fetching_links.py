import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _clean_text(raw_text: str) -> str:
    return " ".join(raw_text.split()).strip()


def scrape_top_links(
    url: str,
    content_selector: str,
    limit: int = 2,
    fallback_selectors: list[str] | None = None,
) -> list[dict]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch URL %s: %s", url, exc)
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    selectors = [content_selector] + (fallback_selectors or [])

    content_area = None
    for selector in selectors:
        content_area = soup.select_one(selector)
        if content_area:
            break

    if not content_area:
        logger.warning("Selector lookup failed for %s, scanning full page", url)
        content_area = soup

    seen_links: set[str] = set()
    scraped_data: list[dict] = []
    for link_tag in content_area.select("a[href]"):
        href = (link_tag.get("href") or "").strip()
        text = _clean_text(link_tag.get_text(" ", strip=True))
        if not href or not text:
            continue
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue

        full_link = urljoin(url, href)
        if full_link in seen_links:
            continue
        seen_links.add(full_link)
        scraped_data.append({"text": text, "link": full_link})

        if len(scraped_data) >= limit:
            break

    return scraped_data
