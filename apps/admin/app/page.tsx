"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import AuthForm from "@/components/AuthForm";
import Chat from "@/components/Chat";
import { API_URL, APP } from "@/lib/config";
import { getSupabase } from "@/lib/supabase";

type Me = { email: string; role: string; plan: string };

export default function Home() {
  const supabase = getSupabase();
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    if (!supabase) return setReady(true);
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setReady(true);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, [supabase]);

  useEffect(() => {
    if (!session) return setMe(null);
    fetch(`${API_URL}/me`, { headers: { Authorization: `Bearer ${session.access_token}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then(setMe)
      .catch(() => setMe(null));
  }, [session]);

  const signOut = () => supabase?.auth.signOut();

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-4 px-6 py-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{APP.title}</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">{APP.description}</p>
        </div>
        {session && (
          <div className="text-right text-sm">
            <p>{me?.email ?? session.user.email}</p>
            {me && (
              <p className="text-slate-500">
                rol: {me.role} · plan: {me.plan}
              </p>
            )}
            <button onClick={signOut} className="underline">
              Cerrar sesión
            </button>
          </div>
        )}
      </header>

      {!ready ? (
        <p className="text-sm text-slate-500">Cargando…</p>
      ) : !supabase ? (
        <p className="rounded-md border border-amber-400 p-4 text-sm">
          Falta configurar NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY (ver .env.example).
        </p>
      ) : !session ? (
        <AuthForm supabase={supabase} />
      ) : (
        <Chat token={session.access_token} onUnauthorized={signOut} />
      )}
    </main>
  );
}
