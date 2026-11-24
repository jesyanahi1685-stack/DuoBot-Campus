export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-4 px-6">
      <h1 className="text-3xl font-semibold">DuoBot Campus · Estudiantes</h1>
      <p className="text-slate-600 dark:text-slate-400">Analiza el desempeño de los estudiantes con gráficas y modelos de machine learning.</p>
      <p className="rounded-md border border-slate-300 p-4 text-sm dark:border-slate-700">
        Esqueleto inicial. Aquí irá el chat, con inicio de sesión y el servicio MCP conectado.
      </p>
    </main>
  );
}
