'use client';

import { useEffect, useState, FormEvent } from 'react';
import { MODELS, type ModelId, type Settings } from './types';

type Props = {
  open: boolean;
  settings: Settings;
  onClose: () => void;
  onSave: (next: Settings) => void;
};

export default function SettingsPanel({ open, settings, onClose, onSave }: Props) {
  const [model, setModel] = useState<ModelId>(settings.model);
  const [systemPrompt, setSystemPrompt] = useState(settings.systemPrompt);

  // Sync form state when the panel (re)opens.
  useEffect(() => {
    if (open) {
      setModel(settings.model);
      setSystemPrompt(settings.systemPrompt);
    }
  }, [open, settings]);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSave({ model, systemPrompt });
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        onClick={onClose}
        aria-hidden
        className="absolute inset-0 bg-stone-900/40 backdrop-blur-sm"
      />
      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-2xl dark:border-stone-800 dark:bg-stone-900"
      >
        <h2 className="mb-5 text-base font-semibold">Settings</h2>

        <label className="block text-sm">
          <span className="mb-1.5 block font-medium text-stone-700 dark:text-stone-200">
            Model
          </span>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value as ModelId)}
            className="w-full rounded-xl border border-stone-200 bg-stone-50/50 px-3 py-2 text-sm focus:border-slate-300 focus:bg-white focus:outline-none focus:ring-4 focus:ring-slate-100/70 dark:border-stone-700 dark:bg-stone-800/30 dark:focus:border-slate-500/60 dark:focus:bg-stone-800/60 dark:focus:ring-slate-800/40"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mt-4 block text-sm">
          <span className="mb-1.5 block font-medium text-stone-700 dark:text-stone-200">
            System prompt
          </span>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Optional — instructions for the assistant"
            rows={5}
            className="w-full resize-none rounded-xl border border-stone-200 bg-stone-50/50 px-3 py-2 text-sm leading-relaxed placeholder:text-stone-400 focus:border-slate-300 focus:bg-white focus:outline-none focus:ring-4 focus:ring-slate-100/70 dark:border-stone-700 dark:bg-stone-800/30 dark:placeholder:text-stone-500 dark:focus:border-slate-500/60 dark:focus:bg-stone-800/60 dark:focus:ring-slate-800/40"
          />
        </label>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-stone-200 px-4 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:border-stone-700 dark:text-stone-200 dark:hover:bg-stone-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-sky-700/30 transition hover:bg-sky-700 dark:bg-sky-500 dark:text-stone-950 dark:shadow-none dark:hover:bg-sky-400"
          >
            Save
          </button>
        </div>
      </form>
    </div>
  );
}
