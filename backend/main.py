"""FastAPI backend for the chat app.

Exposes a streaming chat endpoint that proxies to the Anthropic API,
plus a handful of trivial utility endpoints. Streams responses as SSE,
retries on transient upstream errors, and logs request usage + cost as
JSON via structlog.
"""

import json
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Literal

import anthropic
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langfuse import get_client
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()

# Langfuse tracing. Disables itself (no-ops) when LANGFUSE_* env vars are
# absent, so the app runs fine without credentials. Created after load_dotenv
# so it picks up keys from .env.
langfuse = get_client()


structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
    cache_logger_on_first_use=True,
)

chat_logger = structlog.get_logger("chat")


# USD per 1M tokens — https://platform.claude.com/docs/en/about-claude/models
PRICING = {
    "claude-opus-4-7":   {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5":  {"input": 1.00, "output": 5.00},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the USD cost of one request given token counts and model id."""
    p = PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


DAILY_COST_LIMIT_USD = 5.0


class DailyCostCap:
    """In-memory tracker of cumulative spend for the current UTC day.

    Resets at UTC midnight and on process restart. Good enough for a single
    long-running instance; surviving restarts or spanning multiple instances
    would need shared storage (Redis, a DB, etc.).
    """

    def __init__(self, limit_usd: float):
        self.limit_usd = limit_usd
        self._day = int(time.time() // 86_400)
        self._spent = 0.0

    def _roll_day(self) -> None:
        today = int(time.time() // 86_400)
        if today != self._day:
            self._day = today
            self._spent = 0.0

    def exceeded(self) -> bool:
        self._roll_day()
        return self._spent >= self.limit_usd

    def add(self, cost_usd: float) -> None:
        self._roll_day()
        self._spent += cost_usd

    def reset(self) -> None:
        self._day = int(time.time() // 86_400)
        self._spent = 0.0


cost_cap = DailyCostCap(DAILY_COST_LIMIT_USD)


def _event(payload: dict) -> str:
    """Encode `payload` as one SSE event with a JSON body.

    This is the de-facto LLM streaming standard (OpenAI, Anthropic). JSON
    encoding escapes newlines automatically, so payload content can never
    collide with the SSE event terminator (``\\n\\n``).
    """
    return f"data: {json.dumps(payload)}\n\n"


RETRYABLE_ERRORS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create one shared Anthropic client for the app's lifetime."""
    app.state.anthropic = anthropic.AsyncAnthropic()
    try:
        yield
    finally:
        await app.state.anthropic.close()
        langfuse.flush()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ai-chat-app-delta-one.vercel.app",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Rate limiting, keyed by client IP. Note: behind a proxy (e.g. Render),
# get_remote_address sees the proxy IP, not the end user's.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _error_response(status: int, code: str, exc: Exception) -> JSONResponse:
    """Build a uniform JSON error body for FastAPI exception handlers."""
    return JSONResponse(status_code=status, content={"error": code, "message": str(exc)})


@app.exception_handler(anthropic.AuthenticationError)
async def handle_auth(_req: Request, exc: anthropic.AuthenticationError):
    return _error_response(401, "authentication_error", exc)


@app.exception_handler(anthropic.BadRequestError)
async def handle_bad_request(_req: Request, exc: anthropic.BadRequestError):
    return _error_response(400, "bad_request", exc)


@app.exception_handler(anthropic.RateLimitError)
async def handle_rate_limit(_req: Request, exc: anthropic.RateLimitError):
    return _error_response(429, "rate_limited", exc)


@app.exception_handler(anthropic.APIConnectionError)
async def handle_connection(_req: Request, exc: anthropic.APIConnectionError):
    return _error_response(503, "upstream_connection_error", exc)


@app.exception_handler(anthropic.APIStatusError)
async def handle_status_error(_req: Request, exc: anthropic.APIStatusError):
    return _error_response(502, "upstream_error", exc)


class ModelName(str, Enum):
    """Allowed Claude model identifiers (must match keys in ``PRICING``)."""

    opus = "claude-opus-4-7"
    sonnet = "claude-sonnet-4-6"
    haiku = "claude-haiku-4-5"


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/echo")
async def echo(request: Request):
    body = await request.json()
    return body


@app.get("/model")
async def model(model_name: ModelName):
    return {"model_name": model_name}


class MessageParam(BaseModel):
    """One turn of conversation history, matching Anthropic's message shape."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Body of a POST /chat/stream call from the frontend."""

    messages: list[MessageParam]
    system: str | None = None
    model: ModelName = ModelName.opus


# Cap per-request input size. Output is bounded by max_tokens below, but input
# (history + system prompt) is caller-controlled and otherwise unbounded, so a
# single giant request could burn a lot of credits. Estimated cheaply at the
# common ~4-chars-per-token ratio; an abuse guard only needs to be approximate.
MAX_INPUT_TOKENS = 20_000


def estimate_input_tokens(body: ChatRequest) -> int:
    """Rough input-token estimate from total character count."""
    chars = len(body.system or "") + sum(len(m.content) for m in body.messages)
    return chars // 4


@retry(
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def open_anthropic_stream(client: anthropic.AsyncAnthropic, kwargs: dict):
    """Open a streaming Anthropic request with retries on overload/5xx/network.

    Returns (manager, stream). The caller is responsible for closing the
    manager via ``__aexit__`` when done iterating the stream.
    """
    manager = client.messages.stream(**kwargs)
    stream = await manager.__aenter__()
    return manager, stream


@app.post("/chat/stream")
@limiter.limit("10/minute")
async def chat_stream(request: Request, body: ChatRequest):
    """Stream a Claude response as Server-Sent Events.

    The HTTP response opens with the Anthropic call so that auth / rate-limit /
    overload errors surface to FastAPI's exception handlers *before* headers
    are sent. Once streaming starts, each text delta is yielded as
    ``data: <chunk>\\n\\n``. After the model completes, the handler yields one
    ``data: __USAGE__: {json}\\n\\n`` event with real token counts + cost, then
    ``data: [DONE]\\n\\n``. Mid-stream errors become ``data: __ERROR__: ...``
    events so the response still terminates cleanly.
    """
    if cost_cap.exceeded():
        raise HTTPException(
            status_code=402,
            detail=f"Daily ${DAILY_COST_LIMIT_USD:.0f} cost limit reached. Try again tomorrow.",
        )

    if estimate_input_tokens(body) > MAX_INPUT_TOKENS:
        raise HTTPException(
            status_code=413,
            detail=f"Input exceeds the {MAX_INPUT_TOKENS}-token per-request limit.",
        )

    kwargs = {
        "model": body.model,
        "max_tokens": 1024,
        "messages": [m.model_dump() for m in body.messages],
    }
    if body.system:
        kwargs["system"] = body.system

    start = time.monotonic()
    manager, stream = await open_anthropic_stream(app.state.anthropic, kwargs)

    # Full prompt sent to the model (system + history), as a chat message list
    # so Langfuse renders it as a conversation and a failed request can be
    # debugged from the exact input.
    prompt_messages = [m.model_dump() for m in body.messages]
    if body.system:
        prompt_messages = [{"role": "system", "content": body.system}] + prompt_messages

    async def event_stream():
        reply_parts: list[str] = []
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="chat-response",
            model=body.model.value,
            input=prompt_messages,
        ) as gen:
            try:
                async for text in stream.text_stream:
                    reply_parts.append(text)
                    yield _event({"type": "content", "text": text})

                final = await stream.get_final_message()
                model_id = body.model.value
                cost = round(
                    calculate_cost(model_id, final.usage.input_tokens, final.usage.output_tokens),
                    6,
                )
                chat_logger.info(
                    "chat_request",
                    model=model_id,
                    input_tokens=final.usage.input_tokens,
                    output_tokens=final.usage.output_tokens,
                    cost_usd=cost,
                    latency_ms=int((time.monotonic() - start) * 1000),
                    request_id=final.id,
                )
                cost_cap.add(cost)
                # Pass cost explicitly (ingested cost overrides Langfuse's
                # model-price inference, which may not know these model ids).
                gen.update(
                    output="".join(reply_parts),
                    usage_details={
                        "input_tokens": final.usage.input_tokens,
                        "output_tokens": final.usage.output_tokens,
                    },
                    cost_details={"total": cost},
                )
                yield _event({
                    "type": "usage",
                    "input_tokens": final.usage.input_tokens,
                    "output_tokens": final.usage.output_tokens,
                    "cost_usd": cost,
                })
            except anthropic.APIStatusError as e:
                msg = "upstream error"
                try:
                    msg = e.body.get("error", {}).get("message", str(e))
                except Exception:
                    msg = str(e)
                chat_logger.warning(
                    "stream_aborted",
                    status=getattr(e, "status_code", None),
                    message=msg,
                )
                gen.update(level="ERROR", status_message=msg)
                yield _event({"type": "error", "message": msg})
            except Exception as e:
                chat_logger.warning("stream_aborted", message=str(e))
                gen.update(level="ERROR", status_message=str(e))
                yield _event({"type": "error", "message": str(e)})
            finally:
                yield "data: [DONE]\n\n"
                try:
                    await manager.__aexit__(None, None, None)
                except Exception:
                    pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def main():
    print("Hello from ai-chat-app!")


if __name__ == "__main__":
    main()