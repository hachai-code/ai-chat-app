"""Tests for backend.main endpoints. Run from project root: pytest backend/test_main.py"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


# ---- Fake Anthropic client --------------------------------------------------
# Implements only the methods main.py actually calls. Avoids real network calls
# and lets us assert on the SSE body deterministically.


class _FakeUsage:
    input_tokens = 10
    output_tokens = 5


class _FakeFinalMessage:
    id = "msg_test_fake"
    usage = _FakeUsage()


class _FakeStream:
    def __init__(self, chunks):
        async def aiter():
            for chunk in chunks:
                yield chunk
        self.text_stream = aiter()

    async def get_final_message(self):
        return _FakeFinalMessage()


class _FakeStreamContext:
    def __init__(self, chunks):
        self._chunks = chunks

    async def __aenter__(self):
        return _FakeStream(self._chunks)

    async def __aexit__(self, *exc):
        return None


class FakeAnthropic:
    def __init__(self, chunks=("Hello", " world")):
        self._chunks = chunks
        self.messages = self  # client.messages.stream(...) -> self.stream(...)

    def stream(self, **kwargs):
        return _FakeStreamContext(self._chunks)

    async def close(self):
        return None


# ---- Fixtures ---------------------------------------------------------------


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
