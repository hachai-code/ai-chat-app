'use client';

import type { Conversation } from './types';

type Props = {
  conversations: Conversation[];
  currentId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
};

export default function Sidebar({ conversations, currentId, onSelect, onNew }: Props) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-stone-200/70 bg-stone-50/50 dark:border-stone-800/70 dark:bg-stone-900/50 md:flex">
      <div className="border-b border-stone-200/70 p-3 dark:border-stone-800/70">
        <button
          type="button"
          onClick={onNew}
          className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200 dark:hover:bg-stone-700"
        >
          + New chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {conversations.length === 0 ? (
          <p className="px-3 py-2 text-xs text-stone-400">No conversations yet.</p>
        ) : (
          conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => onSelect(c.id)}
              className={`block w-full truncate rounded-lg px-3 py-2 text-left text-sm transition ${
                c.id === currentId
                  ? 'bg-stone-200 text-stone-900 dark:bg-stone-700 dark:text-stone-100'
                  : 'text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-800'
              }`}
            >
              {c.title || 'New chat'}
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
