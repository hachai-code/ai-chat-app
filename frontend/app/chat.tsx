'use client';

import { useState, useRef, useEffect, FormEvent } from 'react';
import { formatCost, type Message, type ModelId, type Usage } from './types';

const API_URL = `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/chat/stream`;

type Props = {
  conversationId: string;
  messages: Message[];
  totalCostUsd: number;
  onUpdateMessages: (id: string, updater: (prev: Message[]) => Message[]) => void;
  onAddUsage: (id: string, usage: Usage) => void;
  model: ModelId;
  systemPrompt: string;
};

export default function Chat({
  conversationId,
  messages,
  totalCostUsd,
  onUpdateMessages,
  onAddUsage,
  model,
  systemPrompt,
}: Props) {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenCount, setTokenCount] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);

  // Abort any in-flight stream when the component unmounts (parent uses a
  // `key` prop so switching conversations remounts and resets useState).
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

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

    // Capture id so streaming targets the right conversation even if user switches.
    const targetId = conversationId;
    const history: Message[] = [...messages, { role: 'user', content: trimmed }];
    onUpdateMessages(targetId, () => [...history, { role: 'assistant', content: '' }]);
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
        body: JSON.stringify({
          model,
          messages: history,
          ...(systemPrompt.trim() ? { system: systemPrompt } : {}),
        }),
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

          let msg: { type: string; [key: string]: unknown };
          try {
            msg = JSON.parse(payload);
          } catch {
            continue;
          }

          if (msg.type === 'content') {
            appendToAssistant(targetId, String(msg.text ?? ''));
            setTokenCount((n) => n + 1);
          } else if (msg.type === 'usage') {
            onAddUsage(targetId, {
              inputTokens: Number(msg.input_tokens ?? 0),
              outputTokens: Number(msg.output_tokens ?? 0),
              costUsd: Number(msg.cost_usd ?? 0),
            });
          } else if (msg.type === 'error') {
            setError(String(msg.message ?? 'unknown error'));
          }
        }
      }
    } catch (err) {
      const isAbort = (err as Error)?.name === 'AbortError';
      if (!isAbort) {
        setError(err instanceof Error ? err.message : 'unknown error');
      }
      // If we never received any tokens, drop the empty assistant placeholder.
      onUpdateMessages(targetId, (prev) => {
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

  function appendToAssistant(id: string, chunk: string) {
    onUpdateMessages(id, (prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      next[next.length - 1] = { ...last, content: last.content + chunk };
      return next;
    });
  }

  return (
    <div className="flex flex-1 flex-col min-w-0">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 space-y-6 overflow-y-auto px-6 py-6"
      >
        {messages.length === 0 ? (
          <p className="text-sm leading-relaxed text-stone-400">
            No messages yet — say hi.
          </p>
        ) : (
          messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-stone-100 px-4 py-2.5 text-[15px] leading-relaxed text-stone-800 dark:bg-stone-800 dark:text-stone-100">
                  {m.content}
                </div>
              </div>
            ) : (
              <article key={i} className="space-y-1">
                <div className="text-xs font-medium text-stone-500 dark:text-stone-400">
                  Assistant
                </div>
                <div className="whitespace-pre-wrap text-[15px] leading-relaxed text-stone-800 dark:text-stone-100">
                  {m.content ||
                    (isStreaming ? (
                      <span className="text-stone-400">…</span>
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
        <div className="mx-6 mb-3 flex items-start justify-between gap-3 rounded-xl border border-rose-200/70 bg-rose-50 px-4 py-2.5 text-sm leading-relaxed text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">
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

      <div className="flex h-6 items-center justify-between gap-3 border-t border-stone-200/70 px-6 text-xs text-stone-500 dark:border-stone-800/70">
        <span>
          {isStreaming ? (
            <span className="inline-flex items-center gap-2">
              <span className="size-1.5 animate-pulse rounded-full bg-emerald-400" />
              <span>
                Streaming · <span className="font-mono">{tokenCount}</span>{' '}
                {tokenCount === 1 ? 'token' : 'tokens'}
              </span>
            </span>
          ) : (
            <span className="text-stone-400">Ready</span>
          )}
        </span>
        {totalCostUsd > 0 && (
          <span className="font-mono text-stone-500 dark:text-stone-400">
            {formatCost(totalCostUsd)}
          </span>
        )}
      </div>

      <form
        onSubmit={handleSend}
        className="flex gap-2 border-t border-stone-200/70 p-4 dark:border-stone-800/70"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Send a message…"
          disabled={isStreaming}
          className="flex-1 rounded-xl border border-stone-200 bg-stone-50/50 px-4 py-2.5 text-sm leading-relaxed placeholder:text-stone-400 focus:border-slate-300 focus:bg-white focus:outline-none focus:ring-4 focus:ring-slate-100/70 disabled:opacity-50 dark:border-stone-700 dark:bg-stone-800/30 dark:placeholder:text-stone-500 dark:focus:border-slate-500/60 dark:focus:bg-stone-800/60 dark:focus:ring-slate-800/40"
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={handleStop}
            className="rounded-xl border border-stone-200 px-5 py-2.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className="rounded-xl bg-sky-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm shadow-sky-700/30 transition hover:bg-sky-700 disabled:opacity-40 dark:bg-sky-500 dark:text-stone-950 dark:shadow-none dark:hover:bg-sky-400"
          >
            Send
          </button>
        )}
      </form>
    </div>
  );
}
