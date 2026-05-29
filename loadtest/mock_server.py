"""Run the backend locally with a mocked Anthropic client for load testing.

No real API calls and no cost. The rate limit and daily cost cap are disabled
so they don't mask raw concurrency behaviour. Serves on :8001.

    uv run python loadtest/mock_server.py
"""

import asyncio

import anthropic

from backend import main


class _FakeStream:
    CHUNKS = ["token "] * 20  # a short streamed reply

    @property
    def text_stream(self):
        return self._aiter()

    async def _aiter(self):
        for chunk in self.CHUNKS:
            await asyncio.sleep(0.03)  # simulate per-token latency
            yield chunk

    async def get_final_message(self):
        usage = type("Usage", (), {"input_tokens": 10, "output_tokens": 20})()
        return type("Message", (), {"id": "msg_load", "usage": usage})()


class _FakeStreamContext:
    async def __aenter__(self):
        return _FakeStream()

    async def __aexit__(self, *exc):
        return None


class FakeAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = self

    def stream(self, **kwargs):
        return _FakeStreamContext()

    async def close(self):
        return None


# Make the app's lifespan build a fake client instead of a real one.
anthropic.AsyncAnthropic = FakeAnthropic

# Disable the guards so they don't mask raw concurrency results.
main.limiter.enabled = False
main.cost_cap.limit_usd = float("inf")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(main.app, host="127.0.0.1", port=8001, log_level="warning")
