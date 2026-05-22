export type Message = { role: 'user' | 'assistant'; content: string };

export type ModelId =
  | 'claude-opus-4-7'
  | 'claude-sonnet-4-6'
  | 'claude-haiku-4-5';

export const MODELS: { id: ModelId; label: string }[] = [
  { id: 'claude-opus-4-7', label: 'Claude Opus 4.7' },
  { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
  { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5' },
];

export type Settings = {
  model: ModelId;
  systemPrompt: string;
};

export const DEFAULT_SETTINGS: Settings = {
  model: 'claude-haiku-4-5',
  systemPrompt: '',
};

export type Conversation = {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
  totalInputTokens?: number;
  totalOutputTokens?: number;
  totalCostUsd?: number;
};

export type Usage = {
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
};

export function formatCost(usd: number): string {
  if (usd === 0) return '$0.00';
  if (usd < 0.0001) return '<$0.0001';
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}
