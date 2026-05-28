"""Tests for backend.main endpoints. Run from project root: pytest backend/test_main.py"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app, cost_cap, limiter


# ---- Fake Anthropic client --------------------------------------------------
# Implements only the methods main.py actually calls. Avoids real network calls
# and lets us assert on the SSE body deterministically.


class _FakeUsage:
    def __init__(self, input_tokens=10, output_tokens=5):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeFinalMessage:
    def __init__(self, usage):
        self.id = "msg_test_fake"
        self.usage = usage


class _FakeStream:
    def __init__(self, chunks, usage):
        async def aiter():
            for chunk in chunks:
                yield chunk
        self.text_stream = aiter()
        self._usage = usage

    async def get_final_message(self):
        return _FakeFinalMessage(self._usage)


class _FakeStreamContext:
    def __init__(self, chunks, usage):
        self._chunks = chunks
        self._usage = usage

    async def __aenter__(self):
        return _FakeStream(self._chunks, self._usage)

    async def __aexit__(self, *exc):
        return None


class FakeAnthropic:
    def __init__(self, chunks=("Hello", " world"), input_tokens=10, output_tokens=5):
        self._chunks = chunks
        self._usage = _FakeUsage(input_tokens, output_tokens)
        self.messages = self  # client.messages.stream(...) -> self.stream(...)

    def stream(self, **kwargs):
        return _FakeStreamContext(self._chunks, self._usage)

    async def close(self):
        return None


# ---- Fixtures ---------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_limits():
    # Keep tests independent: each starts with a fresh rate-limit window and
    # a zeroed daily cost cap.
    limiter.reset()
    cost_cap.reset()


@pytest.fixture
def client():
    # TestClient without context manager skips lifespan, so no real Anthropic
    # client is created. Tests that need it set app.state.anthropic explicitly.
    return TestClient(app)


@pytest.fixture
def mocked_chat_client(client):
    app.state.anthropic = FakeAnthropic()
    return client


# ---- Tests ------------------------------------------------------------------


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Hello World"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_echo(client):
    payload = {"foo": "bar", "n": 42}
    r = client.post("/echo", json=payload)
    assert r.status_code == 200
    assert r.json() == payload


def test_model(client):
    r = client.get("/model", params={"model_name": "claude-haiku-4-5"})
    assert r.status_code == 200
    assert r.json() == {"model_name": "claude-haiku-4-5"}


def test_chat_stream(mocked_chat_client):
    r = mocked_chat_client.post(
        "/chat/stream",
        json={
            "model": "claude-haiku-4-5",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    body = r.text
    assert '"type": "content"' in body
    assert '"text": "Hello"' in body
    assert '"text": " world"' in body
    assert '"type": "usage"' in body
    assert "data: [DONE]\n\n" in body


def test_chat_stream_multiline_chunk_not_truncated(client):
    """A chunk containing \\n\\n must survive intact. JSON encoding escapes the
    newlines so the SSE event terminator can never collide with content
    (regression test for the dropped-paragraph bug)."""
    app.state.anthropic = FakeAnthropic(chunks=("para1\n\npara2",))
    r = client.post(
        "/chat/stream",
        json={
            "model": "claude-haiku-4-5",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert r.status_code == 200
    # Newlines are JSON-escaped inside the payload.
    assert r'"text": "para1\n\npara2"' in r.text
    # Raw \n\n must not appear adjacent to a data: line — JSON encoding
    # is precisely what prevents that.
    assert "para1\n\npara2" not in r.text


def test_chat_stream_rate_limited(client):
    app.state.anthropic = FakeAnthropic()
    payload = {
        "model": "claude-haiku-4-5",
        "messages": [{"role": "user", "content": "hi"}],
    }
    for _ in range(10):
        assert client.post("/chat/stream", json=payload).status_code == 200
    # 11th request within the window is rejected.
    assert client.post("/chat/stream", json=payload).status_code == 429


def test_chat_stream_rejects_oversized_input(client):
    # ~50k estimated tokens, well over the 20k limit. Rejected before any
    # Anthropic call, so no mock client is needed.
    huge = "x" * 200_000
    r = client.post(
        "/chat/stream",
        json={
            "model": "claude-haiku-4-5",
            "messages": [{"role": "user", "content": huge}],
        },
    )
    assert r.status_code == 413


def test_chat_stream_daily_cost_cap(client):
    # One request that "spends" >$5: 2M haiku output tokens = $10 (>$5 cap).
    app.state.anthropic = FakeAnthropic(output_tokens=2_000_000)
    payload = {
        "model": "claude-haiku-4-5",
        "messages": [{"role": "user", "content": "hi"}],
    }
    # First request succeeds and records the cost.
    assert client.post("/chat/stream", json=payload).status_code == 200
    # Daily budget now exceeded → next request refused.
    assert client.post("/chat/stream", json=payload).status_code == 402
