import asyncio
import time
import httpx

URLS = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
]


async def fetch(client: httpx.AsyncClient, url: str) -> int:
    response = await client.get(url, timeout=10)
    return response.status_code


async def concurrent() -> None:
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        statuses = await asyncio.gather(*(fetch(client, url) for url in URLS))
        elapsed = time.perf_counter() - start
    print(f"Concurrent: {statuses}  — {elapsed:.2f}s")


async def sequential() -> None:
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        statuses = [await fetch(client, url) for url in URLS]
        elapsed = time.perf_counter() - start
    print(f"Sequential: {statuses}  — {elapsed:.2f}s")


async def main() -> None:
    await sequential()
    await concurrent()


asyncio.run(main())

