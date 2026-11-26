"use client";

import { useCallback, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import AuthForm from "@/components/AuthForm";
import Billing from "@/components/Billing";
import Chat from "@/components/Chat";
import { API_URL, APP } from "@/lib/config";
import { getSupabase } from "@/lib/supabase";

type Me = { email: string; role: string; plan: string };

export default function Home() {
  const supabase = getSupabase();
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!supabase) return setReady(true);
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setReady(true);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, [supabase]);

  const fetchMe = useCallback(async (token: string): Promise<Me | null> => {
    try {
      const r = await fetch(`${API_URL}/me`, { headers: { Authorization: `Bearer ${token}` } });
      return r.ok ? await r.json() : null;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    if (!session) return setMe(null);
    let cancelled = false;
    const token = session.access_token;
    const checkout = new URLSearchParams(window.location.search).get("checkout");
    if (checkout) window.history.replaceState({}, "", window.location.pathname);

    (async () => {
      let current = await fetchMe(token);
      if (cancelled) return;
      setMe(current);
      if (checkout === "cancel") return setNotice("El pago se canceló. No se hizo ningún cargo.");
      if (checkout !== "success") return;
      // El plan cambia cuando Stripe avisa por webhook: puede tardar unos segundos.
      setNotice("Pago recibido. Actualizando tu plan…");
      for (let i = 0; i < 8 && current?.plan !== "premium"; i++) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        if (cancelled) return;
        current = await fetchMe(token);
        setMe(current);
      }
      setNotice(
        current?.plan === "premium"
          ? "¡Listo! Tu plan Premium está activo."
          : "Aún no vemos la confirmación del pago. Recarga la página en unos minutos."
      );
    })();
    return () => {
      cancelled = true;
    };
  }, [session, fetchMe]);

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
        <>
          {me && <Billing token={session.access_token} plan={me.plan} notice={notice} />}
          <Chat token={session.access_token} onUnauthorized={signOut} />
        </>
      )}
    </main>
  );
}
