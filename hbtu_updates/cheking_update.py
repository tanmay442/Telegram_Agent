import logging

from hbtu_updates.cache_db import filter_new_links, get_cached_links, set_cached_links
from hbtu_updates.fetching_links import scrape_top_links

logger = logging.getLogger(__name__)

PAGES_TO_SCRAPE = {
    "Conference & Events": {
        "url": "https://hbtu.ac.in/conference-events/",
        "selector": ".entry-content",
        "fallback_selectors": [".site-content", "main"],
    },
    "Academic Circulars": {
        "url": "https://hbtu.ac.in/academic-circular/",
        "selector": ".entry-content",
        "fallback_selectors": [".site-content", "main"],
    },
    "Examination Circulars": {
        "url": "https://hbtu.ac.in/examinations/",
        "selector": "#e-n-tab-content-9783400146",
        "fallback_selectors": [".entry-content", ".site-content", "main"],
    },
}

CACHE_TTL_SECONDS = 1800


def _get_page_links(page_title: str, page_info: dict, limit: int) -> list[dict]:
    cached = get_cached_links(page_title, max_age_seconds=CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    scraped = scrape_top_links(
        url=page_info["url"],
        content_selector=page_info["selector"],
        fallback_selectors=page_info.get("fallback_selectors"),
        limit=limit,
    )
    set_cached_links(page_title, scraped)
    return scraped


def get_latest_updates(limit: int = 5) -> list[dict]:
    results: list[dict] = []
    for page_title, page_info in PAGES_TO_SCRAPE.items():
        logger.info("Checking: %s", page_title)
        data = _get_page_links(page_title, page_info, limit)
        for item in data:
            item["source"] = page_title
            results.append(item)
    return results


def check_for_updates(limit: int = 5) -> list[dict]:
    latest = get_latest_updates(limit=limit)
    return filter_new_links(latest)
