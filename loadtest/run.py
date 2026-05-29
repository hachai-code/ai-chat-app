"""Load test: N concurrent users, each a 3-turn conversation against :8001.

    uv run python loadtest/run.py
"""

import asyncio
import json
import sys
import time

import httpx

URL = "http://127.0.0.1:8001/chat/stream"
N_USERS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
TURNS = 3
MODEL = "claude-haiku-4-5"


async def conversation(client: httpx.AsyncClient, user_id: int):
    history = []
    latencies = []
    for turn in range(TURNS):
        history.append({"role": "user", "content": f"u{user_id} turn {turn}"})
        reply = ""
        t0 = time.monotonic()
        try:
            async with client.stream(
                "POST", URL, json={"model": MODEL, "messages": history}
            ) as r:
                if r.status_code != 200:
                    return {"user": user_id, "error": f"HTTP {r.status_code}"}
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        continue
                    msg = json.loads(payload)
                    if msg.get("type") == "content":
                        reply += msg["text"]
        except Exception as e:
            return {"user": user_id, "error": repr(e)}
        latencies.append(time.monotonic() - t0)
        history.append({"role": "assistant", "content": reply})
    return {"user": user_id, "latencies": latencies}


async def main():
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        t0 = time.monotonic()
        results = await asyncio.gather(
            *[conversation(client, i) for i in range(N_USERS)]
        )
        elapsed = time.monotonic() - t0

    errors = [r for r in results if "error" in r]
    ok = [r for r in results if "latencies" in r]
    all_lat = sorted(lat for r in ok for lat in r["latencies"])

    print(f"\n=== Load test: {N_USERS} users x {TURNS} turns ===")
    print(f"Wall time:        {elapsed:.1f}s")
    print(f"Conversations OK: {len(ok)}/{N_USERS}")
    print(f"Requests OK:      {len(all_lat)}/{N_USERS * TURNS}")
    print(f"Errors:           {len(errors)}")
    if all_lat:
        pct = lambda q: all_lat[min(len(all_lat) - 1, int(len(all_lat) * q))]
        print(f"Latency p50/p95/max: {pct(0.5):.2f}s / {pct(0.95):.2f}s / {all_lat[-1]:.2f}s")
    for e in errors[:10]:
        print("  ERROR:", e["error"])


if __name__ == "__main__":
    asyncio.run(main())
