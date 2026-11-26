"use client";

import { useState } from "react";
import type { SupabaseClient } from "@supabase/supabase-js";

export default function AuthForm({ supabase }: { supabase: SupabaseClient }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    const { error, data } =
      mode === "login"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (error) setMessage(error.message);
    else if (mode === "signup" && !data.session) setMessage("Revisa tu correo para confirmar la cuenta.");
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Correo"
        className="rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
      />
      <input
        type="password"
        required
        minLength={6}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Contraseña"
        className="rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded-md bg-slate-900 px-3 py-2 text-white disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900"
      >
        {mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
      </button>
      <button
        type="button"
        onClick={() => setMode(mode === "login" ? "signup" : "login")}
        className="text-sm text-slate-600 underline dark:text-slate-400"
      >
        {mode === "login" ? "¿No tienes cuenta? Regístrate" : "¿Ya tienes cuenta? Inicia sesión"}
      </button>
      {message && <p className="text-sm text-amber-700 dark:text-amber-400">{message}</p>}
    </form>
  );
}
