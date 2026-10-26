import type { ReactNode } from "react";

export function Card({ title, children, className = "" }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}>
      {title && <h2 className="mb-3 text-sm font-semibold text-slate-600">{title}</h2>}
      {children}
    </section>
  );
}

export function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold text-azul">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function Status({ loading, error }: { loading: boolean; error?: string }) {
  if (error) return <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>;
  if (loading) return <div role="status" className="p-3 text-sm text-slate-500">Carregando…</div>;
  return null;
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn"; children: ReactNode }) {
  const cls = tone === "warn" ? "border-amber-300 bg-amber-50 text-amber-900" : "border-blue-200 bg-blue-50 text-blue-900";
  return <div className={`rounded-lg border p-3 text-sm ${cls}`}>{children}</div>;
}

export function Pager({ total, limit, offset, onChange }: { total: number; limit: number; offset: number; onChange: (o: number) => void }) {
  const last = Math.max(0, Math.ceil(total / limit) - 1);
  const page = Math.floor(offset / limit);
  const btn = "rounded-md border border-slate-300 px-3 py-1 text-sm disabled:opacity-40";
  return (
    <div className="mt-3 flex items-center gap-3 text-sm text-slate-600">
      <button className={btn} disabled={page === 0} onClick={() => onChange(Math.max(0, offset - limit))}>Anterior</button>
      <span>Página {page + 1} de {last + 1} · {total} registros</span>
      <button className={btn} disabled={page >= last} onClick={() => onChange(offset + limit)}>Próxima</button>
    </div>
  );
}
