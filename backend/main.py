from fastapi import FastAPI, Request

app = FastAPI()


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
