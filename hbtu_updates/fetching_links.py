import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


def scrape_top_links(url: str, content_selector: str, limit: int = 2) -> list[dict]:
    scraped_data = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        content_area = soup.select_one(content_selector)

        if not content_area:
            logger.warning(f"Could not find content area with selector '{content_selector}' on {url}")
            return []

        links = content_area.find_all('a', limit=limit)

        for link_tag in links:
            text = link_tag.get_text(strip=True)
            href = link_tag.get('href')

            if text and href:
                full_link = urljoin(url, href)
                scraped_data.append({
                    'text': text,
                    'link': full_link
                })

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {e}")

    return scraped_data


def write_links_to_file() -> None:
    output_filename = 'hbtu_updates/hbtu_links.txt'

    pages_to_scrape = {
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

    with open(output_filename, 'w', encoding='utf-8') as f:
        logger.info("Scraping links and saving to file...")

        for page_title, page_info in pages_to_scrape.items():
            data = scrape_top_links(
                url=page_info["url"],
                content_selector=page_info["selector"],
                limit=5
            )

            if data:
                for item in data:
                    f.write(f"('{item['text']}', '{item['link']}')\n")
            else:
                f.write("No links were found on this page.\n\n")

    logger.info("Links saved to '%s'.", output_filename)