import asyncio
import aiohttp
import orjson
import random
from aiolimiter import AsyncLimiter

# CONFIG
RATE_LIMIT_CALLS = 10
RATE_LIMIT_PERIOD = 1.0
MAX_CONCURRENCY = 20
MAX_RETRIES = 5
INITIAL_BACKOFF = 0.5

async def fetch_with_retries(session, json_url):
    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        async with session.get(json_url) as resp:
            if resp.status == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else backoff
                await asyncio.sleep(wait + random.uniform(0, backoff * 0.1))
                backoff *= 2
                continue
            resp.raise_for_status()
            payload = await resp.read()
            data = orjson.loads(payload)
            barcodes = [v["barcode"] for v in data["product"]["variants"] if v.get("barcode")]
            return barcodes[0] if len(barcodes) == 1 else barcodes or None
    return None

async def fetch_barcodes(session, url, limiter, sem):
    json_url = url.rstrip('/') + '.json'
    async with limiter:
        async with sem:
            return await fetch_with_retries(session, json_url)

async def main(urls):
    limiter = AsyncLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD)
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=0, enable_http2=True)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [fetch_barcodes(session, url, limiter, sem) for url in urls]
        task_to_url = dict(zip(tasks, urls))  # for printing with URL

        results = []
        for idx, task in enumerate(asyncio.as_completed(tasks), start=1):
            try:
                result = await task
                url = task_to_url[task]
                print(f"[{idx}/{len(urls)}] ✅ {url} → {result}")
                results.append(result)
            except Exception as e:
                url = task_to_url.get(task, "unknown")
                print(f"[{idx}/{len(urls)}] ❌ {url} → ERROR: {e}")
                results.append(None)

        return results
