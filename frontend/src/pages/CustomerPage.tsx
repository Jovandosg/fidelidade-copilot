import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Chart } from "../components/Chart";
import { Card, Kpi, Notice, Status } from "../components/ui";
import { fmtBRL, fmtNum, splitDrivers } from "../format";
import { useAsync } from "../useAsync";

export function CustomerPage({ customerId, onSelect }: { customerId?: string; onSelect: (id: string) => void }) {
  const [input, setInput] = useState(customerId ?? "");
  useEffect(() => setInput(customerId ?? ""), [customerId]);
  const { data: c, loading, error } = useAsync(
    () => (customerId ? api.customer(customerId) : Promise.resolve(undefined)),
    [customerId],
  );

  return (
    <div className="space-y-4">
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => { e.preventDefault(); if (input.trim()) onSelect(input.trim().toUpperCase()); }}
      >
        <label className="text-sm">
          <span className="mb-1 block text-slate-600">ID do cliente (sintético)</span>
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="C000001" className="rounded-md border border-slate-300 bg-white px-2 py-1 font-mono text-sm" />
        </label>
        <button className="rounded-md bg-azul px-3 py-1 text-sm font-medium text-white">Abrir</button>
      </form>
      {!customerId && <Notice>Selecione um cliente na Fila de Risco ou no Mapa, ou digite um ID.</Notice>}
      {customerId && <Status loading={loading} error={error} />}
      {c && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi label="Cliente" value={c.customer_id} hint={`${c.segment} · rota preferida ${c.preferred_route}`} />
            <Kpi label="Perfil de valor" value={c.profile} hint={`HVS ${fmtNum(c.hvs)}`} />
            <Kpi label="Risco de churn" value={fmtNum(c.risk_score)} hint="estimativa do modelo" />
            <Kpi label="Gasto 12m" value={fmtBRL(c.spend_12m_brl)} hint={`${c.trips_12m} viagens · margem ${fmtBRL(c.margin_12m_brl)}`} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Por que este HVS? Componentes (0–100)">
              <Chart
                type="bar"
                height={260}
                series={[{ name: "Componente", data: [c.hvs_clv, c.hvs_margin, c.hvs_stability, c.hvs_cost_to_serve] }]}
                options={{
                  xaxis: { categories: ["CLV (peso +0,4)", "Margem (+0,3)", "Estabilidade (+0,3)", "Custo de servir (−0,2)"], max: 100 },
                  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4 } },
                  colors: ["#0b3d91", "#1e6fd9", "#5aa2f0", "#f5a524"],
                  legend: { show: false },
                }}
              />
              <p className="mt-2 text-xs text-slate-500">
                HVS = 0,4·CLV + 0,3·margem + 0,3·estabilidade − 0,2·custo de servir (limitado a 0–100). Resultado: {fmtNum(c.hvs)}.
              </p>
            </Card>
            <Card title="Por que este risco?">
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {splitDrivers(c.risk_drivers).map((d) => <li key={d}>{d}</li>)}
              </ul>
              <dl className="mt-4 grid grid-cols-2 gap-2 text-sm text-slate-600">
                <dt>Recência</dt><dd>{c.recency_days} dias</dd>
                <dt>Interrupções 12m</dt><dd>{c.disruptions_12m}</dd>
                <dt>Reclamações 12m</dt><dd>{c.complaints_12m}</dd>
                <dt>Saldo de pontos</dt><dd>{fmtNum(c.points_balance)}</dd>
              </dl>
            </Card>
          </div>
          <Card title="Próxima melhor ação (sugestão)">
            <p className="font-medium">{c.nba_action}</p>
            <p className="mt-1 text-sm text-slate-600">Margem esperada: {fmtBRL(c.nba_expected_margin_brl)} (estimativa)</p>
            <div className="mt-3">
              {c.nba_requires_approval
                ? <Notice tone="warn">Esta ação tem custo acima do limite: exige <strong>aprovação humana</strong> antes de qualquer contato.</Notice>
                : <Notice>Ação de baixo custo; ainda assim é uma sugestão a ser revisada pela equipe de CRM.</Notice>}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
