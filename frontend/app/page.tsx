import ChatApp from './chat-app';

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center bg-stone-100 p-4 text-stone-900 antialiased dark:bg-stone-950 dark:text-stone-100">
      <div className="flex h-[85vh] w-full max-w-5xl overflow-hidden rounded-2xl border border-stone-200/70 bg-white shadow-xl shadow-stone-300/30 dark:border-stone-800/70 dark:bg-stone-900 dark:shadow-black/30">
        <ChatApp />
      </div>
    </main>
  );
}
