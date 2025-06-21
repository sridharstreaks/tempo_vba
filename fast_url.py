import asyncio
import aiohttp
import orjson  # or ujson — faster than the built-in json

# Tunable concurrency limit; start around 100-500 and benchmark
SEMAPHORE_LIMIT = 300

async def fetch_value(session: aiohttp.ClientSession, url: str, sem: asyncio.Semaphore):
    json_url = url.rstrip('/') + '.json'
    async with sem:  # bound total concurrency
        async with session.get(json_url) as resp:
            resp.raise_for_status()
            payload = await resp.read()
    # Parse once, then extract the key you care about:
    data = orjson.loads(payload)
    return data['someNestedKey']  # adjust to your path

async def main(urls):
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    # Use a single session for connection reuse + keep-alive
    timeout = aiohttp.ClientTimeout(total=30)
    conn = aiohttp.TCPConnector(limit=0, enable_http2=True)  # unlimited conn, use HTTP/2
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        tasks = [fetch_value(session, u, sem) for u in urls]
        # Gather in batches to avoid huge spike of coroutines
        results = []
        BATCH = 10_000
        for i in range(0, len(tasks), BATCH):
            batch = tasks[i:i + BATCH]
            results.extend(await asyncio.gather(*batch, return_exceptions=True))
        return results

if __name__ == '__main__':
    import sys
    urls = sys.stdin.read().splitlines()   # or however you load them
    values = asyncio.run(main(urls))
    # post-process values here (filter out errors, etc.)
