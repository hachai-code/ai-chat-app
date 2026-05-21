'use client';

import { useState, useRef, useEffect, FormEvent } from 'react';

type Message = { role: 'user' | 'assistant'; content: string };

const API_URL = 'http://localhost:8000/chat/stream';

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenCount, setTokenCount] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottomRef.current = distanceFromBottom < 50;
  }

  useEffect(() => {
    if (!stickToBottomRef.current) return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const history: Message[] = [...messages, { role: 'user', content: trimmed }];
    setMessages([...history, { role: 'assistant', content: '' }]);
    setInput('');
    setIsStreaming(true);
    setError(null);
    setTokenCount(0);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'claude-haiku-4-5', messages: history }),
        signal: controller.signal,
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
        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';

        for (const event of events) {
          if (!event.startsWith('data: ')) continue;
          const payload = event.slice(6);
          if (payload === '[DONE]') continue;
          appendToAssistant(payload);
          setTokenCount((n) => n + 1);
        }
      }
    } catch (err) {
      const isAbort = (err as Error)?.name === 'AbortError';
      if (!isAbort) {
        setError(err instanceof Error ? err.message : 'unknown error');
      }
      // If we never received any tokens, drop the empty assistant placeholder.
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        return last?.role === 'assistant' && last.content === ''
          ? prev.slice(0, -1)
          : prev;
      });
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  function handleStop() {
    abortRef.current?.abort();
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
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 space-y-6 overflow-y-auto px-5 py-6"
      >
        {messages.length === 0 ? (
          <p className="text-sm leading-relaxed text-zinc-400">
            No messages yet — say hi.
          </p>
        ) : (
          messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-zinc-100 px-4 py-2.5 text-[15px] leading-relaxed text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100">
                  {m.content}
                </div>
              </div>
            ) : (
              <article key={i} className="space-y-1">
                <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  Assistant
                </div>
                <div className="whitespace-pre-wrap text-[15px] leading-relaxed text-zinc-800 dark:text-zinc-100">
                  {m.content ||
                    (isStreaming ? (
                      <span className="text-zinc-400">…</span>
                    ) : (
                      ''
                    ))}
                </div>
              </article>
            ),
          )
        )}
      </div>

      {error && (
        <div className="mx-5 mb-3 flex items-start justify-between gap-3 rounded-md border border-red-300/60 bg-red-50 px-3 py-2 text-sm leading-relaxed text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
          <span>Error: {error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-xs font-medium underline-offset-2 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="flex h-6 items-center border-t border-zinc-200/70 px-5 text-xs text-zinc-500 dark:border-zinc-800/70">
        {isStreaming ? (
          <span className="inline-flex items-center gap-2">
            <span className="size-1.5 animate-pulse rounded-full bg-emerald-500" />
            <span>
              Streaming · <span className="font-mono">{tokenCount}</span>{' '}
              {tokenCount === 1 ? 'token' : 'tokens'}
            </span>
          </span>
        ) : tokenCount > 0 ? (
          <span>
            <span className="font-mono">{tokenCount}</span>{' '}
            {tokenCount === 1 ? 'token' : 'tokens'}
          </span>
        ) : (
          <span className="text-zinc-400">Ready</span>
        )}
      </div>

      <form
        onSubmit={handleSend}
        className="flex gap-2 border-t border-zinc-200 p-3 dark:border-zinc-800"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Send a message…"
          disabled={isStreaming}
          className="flex-1 rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm leading-relaxed placeholder:text-zinc-400 focus:border-zinc-500 focus:outline-none disabled:opacity-50 dark:border-zinc-700 dark:placeholder:text-zinc-500 dark:focus:border-zinc-500"
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={handleStop}
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-800"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            Send
          </button>
        )}
      </form>
    </>
  );
}
