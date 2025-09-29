import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def scrape_top_links(url, content_selector, limit=5):
    
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
            print(f"Warning: Could not find content area with selector '{content_selector}' on {url}")
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
        print(f"An error occurred while trying to fetch the URL {url}: {e}")
        
    return scraped_data

def write_links_to_file():
    """
    Main function to scrape links and save them to a text file.
    """
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
            "selector": "#e-n-tab-content-9783400146" # Specific selector for the correct tab
        }
    }

    # Open the file in write mode ('w') which will overwrite the file if it exists
    with open(output_filename, 'w', encoding='utf-8') as f:
        print(f"Scraping links and saving to '{output_filename}'...")
        
        for page_title, page_info in pages_to_scrape.items():
            #f.write(f"--- Links from: {page_title} ---\n")
            #print(f"Processing: {page_title}")

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
    
    print(f"\n✔️ All done! The links have been saved to '{output_filename}'.")


if __name__ == "__main__":
    write_links_to_file()
