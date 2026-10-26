import { api } from "../api/client";
import { Chart } from "../components/Chart";
import { Card, Notice, Status } from "../components/ui";
import { fmtNum } from "../format";
import { useAsync } from "../useAsync";

export function RoutesPage() {
  const { data, loading, error } = useAsync(() => api.routes({ limit: 50, sort: "ivr", desc: true }), []);
  const top = data?.items.slice(0, 15) ?? [];

  return (
    <div className="space-y-4">
      <Notice>
        IVR = percentual de voos irregulares (atrasos/cancelamentos) por rota, calculado sobre dados sintéticos. Use para priorizar
        rotas onde a recuperação de clientes (Proteger) é mais urgente.
      </Notice>
      <Status loading={loading} error={error} />
      {data && (
        <>
          <Card title="Top 15 rotas por IVR (%)">
            <Chart
              type="bar" height={420}
              series={[{ name: "IVR (%)", data: top.map((r) => r.ivr) }]}
              options={{
                xaxis: { categories: top.map((r) => r.route) },
                plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
                colors: ["#e5484d"],
                dataLabels: { enabled: false },
              }}
            />
          </Card>
          <Card title={`Rotas (${data.total})`}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr><th className="py-2">Rota</th><th>Voos</th><th>Irregulares</th><th>IVR (%)</th><th>Atraso médio (min)</th><th>Reclamações</th></tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <tr key={r.route} className="border-t border-slate-100">
                      <td className="py-2 font-mono text-azul">{r.route}</td>
                      <td>{fmtNum(r.flights)}</td>
                      <td>{fmtNum(r.disrupted_flights)}</td>
                      <td>{fmtNum(r.ivr)}</td>
                      <td>{fmtNum(r.avg_delay_minutes)}</td>
                      <td>{fmtNum(r.complaints)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
