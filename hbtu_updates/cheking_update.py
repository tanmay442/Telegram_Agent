import logging
from typing import Optional

try:
    from hbtu_updates.fetching_links import scrape_top_links
except ImportError:
    from fetching_links import scrape_top_links

logger = logging.getLogger(__name__)

PAGES_TO_SCRAPE = {
    "Conference & Events": {
        "url": "https://hbtu.ac.in/conference-events/",
        "selector": ".entry-content"
    },
    "Academic Circulars": {
        "url": "https://hbtu.ac.in/academic-circular/",
        "selector": ".entry-content"
    },
    "Examination Circulars": {
        "url": "https://hbtu.ac.in/examinations/",
        "selector": "#e-n-tab-content-9783400146"
    }
}


def check_for_updates(limit: int = 2) -> list[dict]:
    results = []
    for page_title, page_info in PAGES_TO_SCRAPE.items():
        logger.info("Checking: %s", page_title)
        data = scrape_top_links(
            url=page_info["url"],
            content_selector=page_info["selector"],
            limit=limit
        )
        for item in data:
            item['source'] = page_title
            results.append(item)

    return results