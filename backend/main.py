import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Literal

import anthropic
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
import os
load_dotenv()


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
    p = PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


RETRYABLE_ERRORS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.anthropic = anthropic.AsyncAnthropic()
    try:
        yield
    finally:
        await app.state.anthropic.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _error_response(status: int, code: str, exc: Exception) -> JSONResponse:
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
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[MessageParam]
    system: str | None = None
    model: ModelName = ModelName.opus


@retry(
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def open_anthropic_stream(client: anthropic.AsyncAnthropic, kwargs: dict):
    manager = client.messages.stream(**kwargs)
    stream = await manager.__aenter__()
    return manager, stream


@app.post("/chat/stream")
async def chat_stream(body: ChatRequest):
    kwargs = {
        "model": body.model,
        "max_tokens": 1024,
        "messages": [m.model_dump() for m in body.messages],
    }
    if body.system:
        kwargs["system"] = body.system

    start = time.monotonic()
    manager, stream = await open_anthropic_stream(app.state.anthropic, kwargs)

    async def event_stream():
        try:
            async for text in stream.text_stream:
                yield f"data: {text}\n\n"
            yield "data: [DONE]\n\n"

            final = await stream.get_final_message()
            model_id = str(body.model)
            chat_logger.info(
                "chat_request",
                model=model_id,
                input_tokens=final.usage.input_tokens,
                output_tokens=final.usage.output_tokens,
                cost_usd=round(
                    calculate_cost(model_id, final.usage.input_tokens, final.usage.output_tokens),
                    6,
                ),
                latency_ms=int((time.monotonic() - start) * 1000),
                request_id=final.id,
            )
        finally:
            await manager.__aexit__(None, None, None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def main():
    print("Hello from ai-chat-app!")


if __name__ == "__main__":
    main()