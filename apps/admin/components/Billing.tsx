"use client";

import { useState } from "react";
import { API_URL } from "@/lib/config";

type Props = { token: string; plan: string; notice: string | null };

export default function Billing({ token, plan, notice }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const premium = plan === "premium";

  async function go(path: "checkout" | "portal") {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/billing/${path}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail ?? "No se pudo continuar");
      window.location.href = data.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-slate-300 p-3 text-sm dark:border-slate-700">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p>
          Plan actual: <strong>{premium ? "Premium" : "Gratuito"}</strong>
        </p>
        <button
          onClick={() => go(premium ? "portal" : "checkout")}
          disabled={loading}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-white disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900"
        >
          {loading ? "Redirigiendo…" : premium ? "Administrar suscripción" : "Mejorar a Premium"}
        </button>
      </div>
      {notice && <p className="text-emerald-700 dark:text-emerald-400">{notice}</p>}
      {error && <p className="text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
