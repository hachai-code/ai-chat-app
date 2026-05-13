def main():
    print("Hello from ai-chat-app!")


if __name__ == "__main__":
    main()

def generate_response(prompt):
    response = openai.Completion.create(
        engine="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=100
    api_key=os.getenv("OPENAI_API_KEY"),
        
    )
    return response.choices[0].text