import type { Conversation } from './types';

const KEY = 'chat-app:v1';

export type StoredState = {
  conversations: Record<string, Conversation>;
  currentId: string | null;
};

export function loadState(): StoredState | null {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredState;
  } catch {
    return null;
  }
}

export function saveState(state: StoredState): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(KEY, JSON.stringify(state));
}
