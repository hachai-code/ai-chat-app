import Chat from './chat';

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center bg-stone-100 p-4 text-stone-900 antialiased dark:bg-stone-950 dark:text-stone-100">
      <div className="flex h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-stone-200/70 bg-white shadow-xl shadow-stone-300/30 dark:border-stone-800/70 dark:bg-stone-900 dark:shadow-black/30">
        <header className="border-b border-stone-200/70 px-6 py-4 dark:border-stone-800/70">
          <h1 className="text-sm font-semibold tracking-tight">Chat</h1>
        </header>
        <Chat />
      </div>
    </main>
  );
}
