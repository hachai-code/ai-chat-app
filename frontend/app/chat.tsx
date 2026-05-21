'use client';

import { useState, FormEvent } from 'react';

type Message = { role: 'user' | 'assistant'; content: string };

const API_URL = 'http://localhost:8000/chat/stream';

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const history: Message[] = [...messages, { role: 'user', content: trimmed }];
    // Append user message + empty assistant placeholder that will fill in.
    setMessages([...history, { role: 'assistant', content: '' }]);
    setInput('');
    setIsStreaming(true);

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'claude-haiku-4-5', messages: history }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by a blank line ("\n\n").
        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';

        for (const event of events) {
          if (!event.startsWith('data: ')) continue;
          const payload = event.slice(6);
          if (payload === '[DONE]') continue;
          appendToAssistant(payload);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'unknown error';
      appendToAssistant(`\n[error: ${message}]`);
    } finally {
      setIsStreaming(false);
    }
  }

  function appendToAssistant(chunk: string) {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      next[next.length - 1] = { ...last, content: last.content + chunk };
      return next;
    });
  }

  return (
    <>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <p className="text-sm text-zinc-500">No messages yet — say hi.</p>
        ) : (
          messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                m.role === 'user'
                  ? 'ml-auto bg-blue-600 text-white'
                  : 'mr-auto bg-zinc-200 dark:bg-zinc-800'
              }`}
            >
              {m.content || (m.role === 'assistant' && isStreaming ? '…' : '')}
            </div>
          ))
        )}
      </div>
      <form
        onSubmit={handleSend}
        className="flex gap-2 border-t border-zinc-200 p-3 dark:border-zinc-800"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={isStreaming}
          className="flex-1 rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 dark:border-zinc-700"
        />
        <button
          type="submit"
          disabled={!input.trim() || isStreaming}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </>
  );
}
