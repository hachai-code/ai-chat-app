from contextlib import asynccontextmanager
from enum import Enum
from typing import Literal

import anthropic
from fastapi import FastAPI, Request
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

    manager, stream = await open_anthropic_stream(app.state.anthropic, kwargs)

    async def event_stream():
        try:
            async for text in stream.text_stream:
                yield f"data: {text}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            await manager.__aexit__(None, None, None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def main():
    print("Hello from ai-chat-app!")


if __name__ == "__main__":
    main()

def generate_response(prompt):
    response = openai.Completion.create(
        engine="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=100,
        api_key=os.getenv("OPENAI_API_KEY")
        
    )
    return response.choices[0].text
