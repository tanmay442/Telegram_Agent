try:
    from hbtu_updates.fetching_links import scrape_top_links
except ImportError:
    from fetching_links import scrape_top_links



def check_for_updates():
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

    results = []
    for page_title, page_info in pages_to_scrape.items():
        print(f"Processing: {page_title}")
        data = scrape_top_links(
            url=page_info["url"],
            content_selector=page_info["selector"],
            limit=2
        )
        data.append({'source': page_title})
        results.extend(data)

    return results

print(check_for_updates())

        
    
    
    
    
    
            
