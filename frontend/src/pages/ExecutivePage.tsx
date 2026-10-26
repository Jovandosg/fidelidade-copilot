import { api } from "../api/client";
import { Chart } from "../components/Chart";
import { Card, Kpi, Notice, Status } from "../components/ui";
import { PROFILE_COLORS, fmtBRL, fmtNum, fmtPct } from "../format";
import { useAsync } from "../useAsync";

export function ExecutivePage() {
  const kpis = useAsync(() => api.kpis(), []);
  const routes = useAsync(() => api.routes({ limit: 10, sort: "ivr", desc: true }), []);
  const k = kpis.data;

  return (
    <div className="space-y-4">
      <Status loading={kpis.loading} error={kpis.error} />
      {k && (
        <>
          <Notice>{k.notice}</Notice>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi label="Clientes" value={fmtNum(k.total_customers)} />
            <Kpi label="HVS médio" value={fmtNum(k.avg_hvs)} hint="High-Value Score (0–100)" />
            <Kpi
              label="Clientes em risco"
              value={fmtNum(k.high_risk_customers)}
              hint={`risco ≥ ${k.risk_threshold} (${fmtPct(k.high_risk_customers, k.total_customers)})`}
            />
            <Kpi label="Gasto 12m em risco" value={fmtBRL(k.spend_12m_at_risk_brl)} />
            <Kpi label="Margem esperada (NBA)" value={fmtBRL(k.nba_expected_margin_brl)} hint="estimativa, não garantia" />
            <Kpi label="NBA aguardando aprovação" value={fmtNum(k.nba_pending_approval)} hint="aprovação humana obrigatória" />
            <Kpi label="Risco médio" value={fmtNum(k.avg_risk_score)} />
            <Kpi label="IVR médio das rotas" value={`${fmtNum(k.avg_route_ivr)}%`} hint="% de voos irregulares" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Clientes por perfil de valor (A–E)">
              <Chart
                type="donut"
                series={k.profiles.map((p) => p.customers)}
                options={{
                  labels: k.profiles.map((p) => `Perfil ${p.key}`),
                  colors: k.profiles.map((p) => PROFILE_COLORS[p.key] ?? "#94a3b8"),
                  legend: { position: "bottom" },
                }}
              />
            </Card>
            <Card title="Clientes por segmento">
              <Chart
                type="bar"
                series={[{ name: "Clientes", data: k.segments.map((s) => s.customers) }]}
                options={{ xaxis: { categories: k.segments.map((s) => s.key) }, colors: ["#1e6fd9"], plotOptions: { bar: { borderRadius: 4 } } }}
              />
            </Card>
          </div>
        </>
      )}
      <Card title="Rotas com maior índice de voos irregulares (IVR %)">
        <Status loading={routes.loading} error={routes.error} />
        {routes.data && (
          <Chart
            type="bar"
            series={[{ name: "IVR (%)", data: routes.data.items.map((r) => r.ivr) }]}
            options={{
              xaxis: { categories: routes.data.items.map((r) => r.route) },
              plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
              colors: ["#e5484d"],
            }}
          />
        )}
      </Card>
    </div>
  );
}
