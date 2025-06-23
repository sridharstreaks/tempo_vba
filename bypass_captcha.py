import asyncio
import re
from pydoll import Browser  # Adjust import as per actual API

# List of URLs to visit
urls = [
    'https://example.com/page1',
    'https://example.com/page2',
    # Add more URLs
]

# Your regex pattern
pattern = re.compile(r'^gtin.....([0-9]+)', re.MULTILINE)

async def fetch_gtin(url, browser):
    page = await browser.new_page()
    await page.goto(url)
    content = await page.content()
    # Optionally: handle CAPTCHA detection and solve if supported
    match = pattern.search(content)
    gtin = match.group(1) if match else None
    await page.close()
    return url, gtin

async def main():
    async with Browser(headless=True) as browser:  # Adjust context manager as per API
        tasks = [fetch_gtin(url, browser) for url in urls]
        results = await asyncio.gather(*tasks)
        for url, gtin in results:
            print(f"{url}: {gtin}")

if __name__ == "__main__":
    asyncio.run(main())
