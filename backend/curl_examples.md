curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "system": "Reply in one short sentence.",
    "model": "claude-haiku-4-5",
    "messages": [
      {"role": "user", "content": "What is a token?"}
    ]
  }'

curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "system": "Reply in one short sentence.",
    "model": "claude-haiku-4-5",
    "messages": [
      {"role": "user", "content": "What is a token?"},
      {"role": "assistant", "content": "A token is the smallest unit of text that an AI processes, roughly equivalent to a word or small fraction of a word."},
      {"role": "user", "content": "Give an example."}
    ]
  }'

curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "system": "Reply in one short sentence.",
    "model": "claude-haiku-4-5",
    "messages": [
      {"role": "user", "content": "What is a token?"},
      {"role": "assistant", "content": "A token is the smallest unit of text that an AI processes, roughly equivalent to a word or small fraction of a word."},
      {"role": "user", "content": "Give an example."},
      {"role": "assistant", "content": "The sentence \"Hello, how are you?\" breaks into approximately 6 tokens: \"Hello\" / \",\" / \"how\" / \"are\" / \"you\" / \"?\"."},
      {"role": "user", "content": "How does that relate to max_tokens?"}
    ]
  }'
