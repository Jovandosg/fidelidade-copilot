import { useMemo } from "react";
import { api, type Customer } from "../api/client";
import { Chart } from "../components/Chart";
import { Card, Notice, Status } from "../components/ui";
import { PROFILE_COLORS } from "../format";
import { useAsync } from "../useAsync";

const RISK_LIMIAR = 40;
const HVS_LIMIAR = 60;
const PROFILES = ["A", "B", "C", "D", "E"];

export function groupByProfile(customers: Customer[]) {
  return PROFILES.map((p) => customers.filter((c) => c.profile === p));
}

export function ValueRiskPage({ onSelect }: { onSelect: (id: string) => void }) {
  const { data, loading, error } = useAsync(() => api.allCustomers(), []);
  const groups = useMemo(() => (data ? groupByProfile(data) : []), [data]);
  const priority = data?.filter((c) => c.hvs >= HVS_LIMIAR && c.risk_score >= RISK_LIMIAR).length ?? 0;

  return (
    <div className="space-y-4">
      <Notice>
        Cada ponto é um cliente sintético: eixo X = High-Value Score, eixo Y = risco de churn estimado. O quadrante
        superior direito (valor alto e risco alto) concentra a prioridade de retenção. Clique num ponto para abrir o perfil.
      </Notice>
      <Status loading={loading} error={error} />
      {data && (
        <Card title={`Mapa Valor × Risco — ${priority} clientes no quadrante prioritário (HVS ≥ ${HVS_LIMIAR} e risco ≥ ${RISK_LIMIAR})`}>
          <Chart
            type="scatter"
            height={480}
            series={groups.map((g, i) => ({ name: `Perfil ${PROFILES[i]}`, data: g.map((c) => [c.hvs, c.risk_score]) }))}
            options={{
              colors: PROFILES.map((p) => PROFILE_COLORS[p]),
              xaxis: { title: { text: "High-Value Score" }, min: 0, max: 100, tickAmount: 10 },
              yaxis: { title: { text: "Risco de churn (0–100)" }, min: 0 },
              markers: { size: 4 },
              legend: { position: "top" },
              annotations: {
                xaxis: [{ x: HVS_LIMIAR, borderColor: "#64748b", strokeDashArray: 4 }],
                yaxis: [{ y: RISK_LIMIAR, borderColor: "#64748b", strokeDashArray: 4, label: { text: "limiar de risco", style: { fontSize: "11px" } } }],
              },
              tooltip: { x: { formatter: (v: number) => `HVS ${v.toFixed(1)}` } },
              chart: {
                events: {
                  dataPointSelection: (_e, _c, cfg) => {
                    const c = cfg ? groups[cfg.seriesIndex]?.[cfg.dataPointIndex] : undefined;
                    if (c) onSelect(c.customer_id);
                  },
                },
              },
            }}
          />
        </Card>
      )}
    </div>
  );
}
