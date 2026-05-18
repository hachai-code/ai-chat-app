from enum import Enum
from typing import AsyncIterator

import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()


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


class ChatRequest(BaseModel):
    message: str
    model: ModelName = ModelName.opus


@app.post("/chat/stream", response_class=StreamingResponse)
async def chat_stream(body: ChatRequest) -> AsyncIterator[str]:
    async with anthropic.AsyncAnthropic() as client:
        async with client.messages.stream(
            model=body.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": body.message}],
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {text}\n\n"
    yield "data: [DONE]\n\n"


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
