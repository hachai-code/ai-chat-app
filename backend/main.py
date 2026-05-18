from enum import Enum

from fastapi import FastAPI, Request

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
