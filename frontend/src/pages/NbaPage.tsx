import { useState } from "react";
import { api } from "../api/client";
import { Chart } from "../components/Chart";
import { Card, Notice, Pager, Status } from "../components/ui";
import { fmtBRL, fmtNum } from "../format";
import { useAsync } from "../useAsync";

const LIMIT = 15;

export function NbaPage({ onSelect }: { onSelect: (id: string) => void }) {
  const [approval, setApproval] = useState<"" | "true" | "false">("");
  const [offset, setOffset] = useState(0);
  const { data, loading, error } = useAsync(
    () => api.nba({ limit: LIMIT, offset, requires_approval: approval === "" ? undefined : approval === "true" }),
    [approval, offset],
  );

  return (
    <div className="space-y-4">
      <Notice tone="warn">
        <strong>Aprovação humana obrigatória:</strong>{" "}
        {data?.human_approval_notice ?? "ações com custo acima do limite só podem ser executadas após aprovação de uma pessoa."}{" "}
        As ações abaixo são sugestões geradas por regras sobre dados sintéticos; nenhuma é executada automaticamente.
      </Notice>
      <Status loading={loading} error={error} />
      {data && (
        <>
          <Card title="Margem esperada por ação sugerida (R$, estimativa)">
            <Chart
              type="bar"
              height={280}
              series={[{ name: "Margem esperada", data: data.summary.map((s) => Math.round(s.expected_margin_brl)) }]}
              options={{
                xaxis: { categories: data.summary.map((s) => s.nba_action.split("(")[0].trim()) },
                plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
                colors: ["#1e6fd9"],
                dataLabels: { enabled: false },
              }}
            />
          </Card>
          <Card>
            <label className="mb-3 block text-sm">
              <span className="mb-1 block text-slate-600">Aprovação</span>
              <select
                value={approval} className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
                onChange={(e) => { setApproval(e.target.value as typeof approval); setOffset(0); }}
              >
                <option value="">Todas</option>
                <option value="true">Exigem aprovação humana</option>
                <option value="false">Baixo custo</option>
              </select>
            </label>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr><th className="py-2">Cliente</th><th>Perfil</th><th>Risco</th><th>Ação sugerida</th><th>Margem esperada</th><th>Aprovação</th></tr>
                </thead>
                <tbody>
                  {data.items.map((n) => (
                    <tr key={n.customer_id} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50" onClick={() => onSelect(n.customer_id)}>
                      <td className="py-2 font-mono text-azul">{n.customer_id}</td>
                      <td>{n.profile}</td>
                      <td>{fmtNum(n.risk_score)}</td>
                      <td className="max-w-md truncate" title={n.nba_action}>{n.nba_action}</td>
                      <td>{fmtBRL(n.nba_expected_margin_brl)}</td>
                      <td>{n.nba_requires_approval ? <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">Requer aprovação</span> : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pager total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </Card>
        </>
      )}
    </div>
  );
}
