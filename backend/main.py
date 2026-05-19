from contextlib import asynccontextmanager
from enum import Enum
from typing import Literal

import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.anthropic = anthropic.AsyncAnthropic()
    try:
        yield
    finally:
        await app.state.anthropic.close()


app = FastAPI(lifespan=lifespan)


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


@app.post("/chat/stream")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    kwargs = {
        "model": body.model,
        "max_tokens": 1024,
        "messages": [m.model_dump() for m in body.messages],
    }
    if body.system:
        kwargs["system"] = body.system

    async def event_stream():
        async with app.state.anthropic.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"

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
