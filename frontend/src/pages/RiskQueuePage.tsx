import { useState } from "react";
import { api } from "../api/client";
import { Card, Notice, Pager, Status } from "../components/ui";
import { fmtNum, splitDrivers } from "../format";
import { useAsync } from "../useAsync";

const LIMIT = 15;

export function RiskQueuePage({ onSelect }: { onSelect: (id: string) => void }) {
  const [minRisk, setMinRisk] = useState(40);
  const [profile, setProfile] = useState("");
  const [offset, setOffset] = useState(0);
  const { data, loading, error } = useAsync(
    () => api.customers({ limit: LIMIT, offset, min_risk: minRisk, profile: profile || undefined, sort: "risk_score", desc: true }),
    [minRisk, profile, offset],
  );
  const field = "rounded-md border border-slate-300 bg-white px-2 py-1 text-sm";

  return (
    <div className="space-y-4">
      <Notice>Fila ordenada por risco estimado (modelo simples sobre dados sintéticos; não é previsão validada).</Notice>
      <Card>
        <div className="mb-3 flex flex-wrap items-end gap-4">
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Risco mínimo</span>
            <input
              type="number" min={0} max={100} value={minRisk} className={`${field} w-24`}
              onChange={(e) => { setMinRisk(Math.min(100, Math.max(0, Number(e.target.value) || 0))); setOffset(0); }}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Perfil</span>
            <select value={profile} className={field} onChange={(e) => { setProfile(e.target.value); setOffset(0); }}>
              <option value="">Todos</option>
              {["A", "B", "C", "D", "E"].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </label>
        </div>
        <Status loading={loading} error={error} />
        {data && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr><th className="py-2">Cliente</th><th>Perfil</th><th>HVS</th><th>Risco</th><th>Principais fatores</th><th>Ação sugerida</th></tr>
                </thead>
                <tbody>
                  {data.items.map((c) => (
                    <tr key={c.customer_id} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50" onClick={() => onSelect(c.customer_id)}>
                      <td className="py-2 font-mono text-azul">{c.customer_id}</td>
                      <td>{c.profile}</td>
                      <td>{fmtNum(c.hvs)}</td>
                      <td className="font-semibold">{fmtNum(c.risk_score)}</td>
                      <td>{splitDrivers(c.risk_drivers).join(", ")}</td>
                      <td className="max-w-xs truncate" title={c.nba_action}>{c.nba_action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data.items.length === 0 && <p className="py-4 text-sm text-slate-500">Nenhum cliente com esses filtros.</p>}
            <Pager total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>
    </div>
  );
}
