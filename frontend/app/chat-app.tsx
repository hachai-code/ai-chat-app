'use client';

import { useCallback, useEffect, useState } from 'react';
import Chat from './chat';
import Sidebar from './sidebar';
import { loadState, saveState } from './storage';
import type { Conversation, Message } from './types';

function newConversation(): Conversation {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: 'New chat',
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

export default function ChatApp() {
  const [conversations, setConversations] = useState<Record<string, Conversation>>({});
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage on mount, or seed with a fresh conversation.
  useEffect(() => {
    const saved = loadState();
    if (saved && Object.keys(saved.conversations).length > 0) {
      setConversations(saved.conversations);
      setCurrentId(saved.currentId ?? Object.keys(saved.conversations)[0]);
    } else {
      const c = newConversation();
      setConversations({ [c.id]: c });
      setCurrentId(c.id);
    }
    setHydrated(true);
  }, []);

  // Persist on any change (skip the initial render before hydration).
  useEffect(() => {
    if (!hydrated) return;
    saveState({ conversations, currentId });
  }, [conversations, currentId, hydrated]);

  const sortedConversations = Object.values(conversations).sort(
    (a, b) => b.updatedAt - a.updatedAt,
  );
  const current = currentId ? conversations[currentId] : null;

  const handleNew = useCallback(() => {
    const c = newConversation();
    setConversations((prev) => ({ ...prev, [c.id]: c }));
    setCurrentId(c.id);
  }, []);

  const handleSelect = useCallback((id: string) => {
    setCurrentId(id);
  }, []);

  const handleUpdateMessages = useCallback(
    (id: string, updater: (prev: Message[]) => Message[]) => {
      setConversations((prev) => {
        const conv = prev[id];
        if (!conv) return prev;
        const next = updater(conv.messages);
        // Auto-derive title from the first user message (only while still "New chat")
        const firstUser = next.find((m) => m.role === 'user');
        const title =
          conv.title === 'New chat' && firstUser
            ? firstUser.content.slice(0, 40).trim() || 'New chat'
            : conv.title;
        return {
          ...prev,
          [id]: { ...conv, messages: next, title, updatedAt: Date.now() },
        };
      });
    },
    [],
  );

  return (
    <div className="flex flex-1 min-w-0">
      {!hydrated ? (
        <div className="flex flex-1 items-center justify-center text-sm text-stone-400">
          Loading…
        </div>
      ) : (
        <>
          <Sidebar
            conversations={sortedConversations}
            currentId={currentId}
            onSelect={handleSelect}
            onNew={handleNew}
          />
          {current ? (
            <Chat
              conversationId={current.id}
              messages={current.messages}
              onUpdateMessages={handleUpdateMessages}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center text-sm text-stone-400">
              Click + New chat to begin.
            </div>
          )}
        </>
      )}
    </div>
  );
}
