import asyncio
import aiohttp
import orjson

SEMAPHORE_LIMIT = 300  # Tune this based on bandwidth & server limits

async def fetch_barcodes(session: aiohttp.ClientSession, url: str, sem: asyncio.Semaphore):
    json_url = url.rstrip('/') + '.json'
    async with sem:
        async with session.get(json_url) as resp:
            resp.raise_for_status()
            payload = await resp.read()

    try:
        data = orjson.loads(payload)
        variants = data["product"]["variants"]
        barcodes = [v["barcode"] for v in variants if v.get("barcode")]

        # Return str if only one, else list
        if len(barcodes) == 1:
            return barcodes[0]
        return barcodes if barcodes else None
    except Exception as e:
        # Log or handle error (optional)
        return None

async def main(urls):
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    timeout = aiohttp.ClientTimeout(total=30)
    conn = aiohttp.TCPConnector(limit=0, enable_http2=True)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        tasks = [fetch_barcodes(session, url, sem) for url in urls]

        results = []
        BATCH_SIZE = 10000
        for i in range(0, len(tasks), BATCH_SIZE):
            batch = tasks[i:i + BATCH_SIZE]
            results.extend(await asyncio.gather(*batch, return_exceptions=True))

        return results

if __name__ == "__main__":
    # Example list of URLs
    urls = [
        "https://example.com/products/medela-magnetronsterilisatiezakje-quick-clean-5-stuks",
        # Add thousands/lakhs here
    ]

    barcodes = asyncio.run(main(urls))

    for i, bc in enumerate(barcodes):
        print(f"{i+1}: {bc}")
