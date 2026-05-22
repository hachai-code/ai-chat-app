'use client';

import { useCallback, useEffect, useState } from 'react';
import Chat from './chat';
import Sidebar from './sidebar';
import SettingsPanel from './settings-panel';
import { loadState, saveState } from './storage';
import {
  DEFAULT_SETTINGS,
  type Conversation,
  type Message,
  type Settings,
  type Usage,
} from './types';

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
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [hydrated, setHydrated] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // localStorage is client-only; we have to read it after mount. The rule
  // would prefer a sync-external-store pattern, but for a single one-shot
  // read on mount this is the standard React idiom.
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    const saved = loadState();
    if (saved && Object.keys(saved.conversations).length > 0) {
      setConversations(saved.conversations);
      setCurrentId(saved.currentId ?? Object.keys(saved.conversations)[0]);
      if (saved.settings) setSettings({ ...DEFAULT_SETTINGS, ...saved.settings });
    } else {
      const c = newConversation();
      setConversations({ [c.id]: c });
      setCurrentId(c.id);
    }
    setHydrated(true);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  // Persist on any change (skip the initial render before hydration).
  useEffect(() => {
    if (!hydrated) return;
    saveState({ conversations, currentId, settings });
  }, [conversations, currentId, settings, hydrated]);

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

  const handleAddUsage = useCallback((id: string, usage: Usage) => {
    setConversations((prev) => {
      const conv = prev[id];
      if (!conv) return prev;
      return {
        ...prev,
        [id]: {
          ...conv,
          totalInputTokens: (conv.totalInputTokens ?? 0) + usage.inputTokens,
          totalOutputTokens: (conv.totalOutputTokens ?? 0) + usage.outputTokens,
          totalCostUsd: (conv.totalCostUsd ?? 0) + usage.costUsd,
        },
      };
    });
  }, []);

  const handleUpdateMessages = useCallback(
    (id: string, updater: (prev: Message[]) => Message[]) => {
      setConversations((prev) => {
        const conv = prev[id];
        if (!conv) return prev;
        const next = updater(conv.messages);
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
            onOpenSettings={() => setSettingsOpen(true)}
          />
          {current ? (
            <Chat
              key={current.id}
              conversationId={current.id}
              messages={current.messages}
              totalCostUsd={current.totalCostUsd ?? 0}
              onUpdateMessages={handleUpdateMessages}
              onAddUsage={handleAddUsage}
              model={settings.model}
              systemPrompt={settings.systemPrompt}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center text-sm text-stone-400">
              Click + New chat to begin.
            </div>
          )}
          {settingsOpen && (
            <SettingsPanel
              settings={settings}
              onClose={() => setSettingsOpen(false)}
              onSave={setSettings}
            />
          )}
        </>
      )}
    </div>
  );
}
