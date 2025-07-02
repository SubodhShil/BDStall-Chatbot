import requests
from bs4 import BeautifulSoup
import os

import asyncio
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


BASE_URL = "https://www.bdstall.com/laptop/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_product_links():
    print("Fetching URL:", BASE_URL)
    res = requests.get(BASE_URL, headers=HEADERS)
    print("Status code:", res.status_code)
    soup = BeautifulSoup(res.text, "html.parser")
    links = []

    # Find all anchor tags with detail links directly
    all_anchors = soup.find_all("a", href=True)
    detail_links = []

    for a in all_anchors:
        href = a.get("href")
        if href and "/details/" in href:
            # Ensure the link is absolute
            if href.startswith("http"):
                full_url = href
            else:
                full_url = "https://www.bdstall.com" + href
            detail_links.append(full_url)

    print(f"Found {len(detail_links)} product links")

    # Remove duplicates and limit to 40 links
    unique_links = list(dict.fromkeys(detail_links))[:40]
    print(f"Returning {len(unique_links)} unique product links")

    if unique_links:
        print("Sample links:")
        for i, link in enumerate(unique_links[:5]):
            print(f"  {i+1}. {link}")

    return unique_links


async def scrape_product(crawler, url, output_dir):
    print(f"Scraping: {url}")

    # Create a filename from the URL
    file_name = url.strip("/").split("/")[-1] + ".md"
    file_path = os.path.join(output_dir, file_name)

    # Skip if already scraped
    if os.path.exists(file_path):
        print(f"Skipping {file_name} - already exists")
        return

    run_conf = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    try:
        result = await crawler.arun(url, config=run_conf)

        # saving the markdown file
        if result and result.markdown:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result.markdown)
            print(f"✓ Saved {file_path}")
        else:
            print(f"✗ No markdown content found for {url}")
    except Exception as e:
        print(f"Error scraping {url}: {e}")


async def main():
    # Get product links
    product_links = get_product_links()

    if not product_links:
        print("No product links found to scrape.")
        return

    # Create output directory
    output_dir = "bdstall_markdown"
    os.makedirs(output_dir, exist_ok=True)

    # Configure browser
    browser_conf = BrowserConfig(headless=True)

    # Scrape each product
    async with AsyncWebCrawler(config=browser_conf) as crawler:
        print(f"Starting to scrape {len(product_links)} products...")

        # Option 1: Scrape one by one (slower but more reliable)
        for url in product_links:
            await scrape_product(crawler, url, output_dir)

        # Option 2: Scrape concurrently (faster but might hit rate limits)
        # Uncomment this and comment out the for-loop above to use this method
        # tasks = [scrape_product(crawler, url, output_dir) for url in product_links]
        # await asyncio.gather(*tasks)

        print("Scraping completed!")


if __name__ == "__main__":
    # Get product links only
    # print(get_product_links())

    # Run full scraping process
    asyncio.run(main())
