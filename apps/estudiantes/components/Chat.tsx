"use client";

import { useState } from "react";
import { API_URL } from "@/lib/config";

type Msg = { role: "user" | "assistant"; content: string };

export default function Chat({ token, onUnauthorized }: { token: string; onUnauthorized: () => void }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    const next: Msg[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ messages: next }),
      });
      if (res.status === 401) return onUnauthorized();
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail ?? "No se pudo obtener respuesta");
      setMessages([...next, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-3">
      <div className="flex min-h-[320px] flex-1 flex-col gap-2 overflow-y-auto rounded-md border border-slate-300 p-3 dark:border-slate-700">
        {messages.length === 0 && (
          <p className="text-sm text-slate-500">Prueba con: “¿Cuál es mi plan?” o “¿Qué rol tengo?”</p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] whitespace-pre-wrap rounded-md px-3 py-2 text-sm ${
              m.role === "user"
                ? "self-end bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                : "self-start bg-slate-100 dark:bg-slate-800"
            }`}
          >
            {m.content}
          </div>
        ))}
        {loading && <p className="text-sm text-slate-500">Pensando…</p>}
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <form onSubmit={send} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          maxLength={4000}
          placeholder="Escribe tu pregunta…"
          className="flex-1 rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
