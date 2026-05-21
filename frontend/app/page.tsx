import Chat from './chat';

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center bg-zinc-50 p-4 dark:bg-black">
      <div className="flex h-[80vh] w-full max-w-2xl flex-col rounded-lg bg-white shadow dark:bg-zinc-900">
        <header className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <h1 className="font-semibold">Chat</h1>
        </header>
        <Chat />
      </div>
    </main>
  );
}
