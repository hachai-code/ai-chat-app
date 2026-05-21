import Chat from './chat';

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center bg-zinc-100 p-4 text-zinc-900 antialiased dark:bg-zinc-950 dark:text-zinc-100">
      <div className="flex h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <header className="border-b border-zinc-200 px-5 py-3 dark:border-zinc-800">
          <h1 className="text-sm font-semibold tracking-tight">Chat</h1>
        </header>
        <Chat />
      </div>
    </main>
  );
}
