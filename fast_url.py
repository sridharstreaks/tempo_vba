import asyncio
import aiohttp
import orjson
import random
from aiolimiter import AsyncLimiter

# ─── CONFIG ────────────────────────────────────────────────────────────────
RATE_LIMIT_CALLS = 10        # max requests
RATE_LIMIT_PERIOD = 1.0      # per N seconds
MAX_CONCURRENCY = 100        # max in-flight requests
MAX_RETRIES = 5
INITIAL_BACKOFF = 0.5        # seconds
# ──────────────────────────────────────────────────────────────────────────

async def fetch_with_retries(session: aiohttp.ClientSession, json_url: str):
    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        async with session.get(json_url) as resp:
            if resp.status == 429:
                # honor Retry-After header if present
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else backoff
                # add a little jitter
                await asyncio.sleep(wait + random.uniform(0, backoff * 0.1))
                backoff *= 2
                continue

            resp.raise_for_status()
            payload = await resp.read()
            data = orjson.loads(payload)
            variants = data["product"]["variants"]
            barcodes = [v["barcode"] for v in variants if v.get("barcode")]

            if len(barcodes) == 1:
                return barcodes[0]
            return barcodes or None

    # gave up after retries
    return None

async def fetch_barcodes(session, url, limiter, sem):
    json_url = url.rstrip('/') + '.json'
    async with limiter:      # enforce rate limit
        async with sem:      # enforce concurrency limit
            return await fetch_with_retries(session, json_url)

async def main(urls):
    limiter = AsyncLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD)
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=0, enable_http2=True)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [fetch_barcodes(session, url, limiter, sem) for url in urls]
        # run them all, collecting results (exceptions are returned)
        return await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    import sys

    # load URLs (one per line) from stdin or a file
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        urls = sys.stdin.read().splitlines()

    results = asyncio.run(main(urls))

    # Output: index, URL, barcode(s)
    for idx, (url, bc) in enumerate(zip(urls, results), start=1):
        print(f"{idx}. {url} → {bc}")
