import { api } from "../api/client";
import { Chart } from "../components/Chart";
import { Card, Kpi, Notice, Status } from "../components/ui";
import { useAuth } from "../auth";
import { fmtNum } from "../format";
import { useAsync } from "../useAsync";

const dt = (s?: string | null) => (s ? new Date(s).toLocaleString("pt-BR") : "—");

function Runs() {
  const { data, loading, error } = useAsync(() => api.runs(10), []);
  return (
    <Card title="Execuções do pipeline">
      <Status loading={loading} error={error} />
      {data && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr><th className="py-2">Run</th><th>Início</th><th>Duração</th><th>Status</th><th>Código</th><th>Seed</th><th>Linhas</th></tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.run_id} className="border-t border-slate-100 align-top">
                  <td className="py-2 font-mono text-xs">{r.run_id.slice(0, 8)}</td>
                  <td>{dt(r.started_at)}</td>
                  <td>{r.duration_ms == null ? "—" : `${fmtNum(r.duration_ms / 1000)} s`}</td>
                  <td>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${r.status === "passed" ? "bg-green-100 text-green-800" : r.status === "running" ? "bg-amber-100 text-amber-900" : "bg-red-100 text-red-800"}`}>{r.status}</span>
                    {r.error && <div className="text-xs text-red-700">{r.error}</div>}
                  </td>
                  <td className="font-mono text-xs">{r.code_version.slice(0, 10)}</td>
                  <td>{r.seed}</td>
                  <td className="text-xs">{Object.entries(r.rows_by_entity).map(([k, v]) => `${k}: ${fmtNum(v)}`).join(" · ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function Quality() {
  const { data, loading, error } = useAsync(() => api.quality(), []);
  const failed = data?.results.filter((r) => !r.passed) ?? [];
  return (
    <Card title="Qualidade de dados (pandera, por regra)">
      <Status loading={loading} error={error} />
      {data && (
        <>
          <div className="mb-3 grid grid-cols-2 gap-3">
            <Kpi label="Regras avaliadas" value={fmtNum(data.total_rules)} />
            <Kpi label="Regras com falha" value={fmtNum(data.failed_rules)} />
          </div>
          {failed.length === 0 ? (
            <p className="text-sm text-green-700">Todas as regras passaram na última execução.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Entidade</th><th>Regra</th><th>Linhas</th></tr></thead>
              <tbody>
                {failed.map((r) => (
                  <tr key={`${r.entity}.${r.rule}`} className="border-t border-slate-100"><td className="py-2">{r.entity}</td><td>{r.rule}</td><td>{fmtNum(r.failed_rows)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </Card>
  );
}

function Drift() {
  const { data, loading, error } = useAsync(() => api.drift(), []);
  return (
    <Card title="Drift por feature (PSI)">
      <Status loading={loading} error={error} />
      {data && data.items.length === 0 && <p className="text-sm text-slate-500">Sem medição de drift ainda: ela exige ao menos duas execuções.</p>}
      {data && data.items.length > 0 && (
        <>
          <p className={`mb-2 text-sm ${data.alerts ? "font-medium text-red-700" : "text-green-700"}`}>
            {data.alerts ? `${data.alerts} feature(s) acima do limiar` : "Nenhum alerta de drift"}
          </p>
          <Chart
            type="bar" height={300}
            series={[{ name: "PSI", data: data.items.map((d) => Number(d.psi.toFixed(3))) }]}
            options={{
              xaxis: { categories: data.items.map((d) => d.feature) },
              colors: ["#1e6fd9"],
              dataLabels: { enabled: false },
              annotations: { yaxis: [{ y: data.items[0].threshold, borderColor: "#e5484d", label: { text: "limiar" } }] },
            }}
          />
        </>
      )}
    </Card>
  );
}

function Models() {
  const { data, loading, error } = useAsync(() => api.models(), []);
  return (
    <Card title="Modelos registrados">
      <Status loading={loading} error={error} />
      {data && (
        <div className="space-y-3">
          {data.map((m) => (
            <div key={`${m.model_name}@${m.model_version}`} className="rounded-lg border border-slate-200 p-3 text-sm">
              <div className="font-semibold text-azul">{m.model_name} <span className="font-mono text-xs text-slate-500">v{m.model_version}</span></div>
              <div className="text-xs text-slate-500">treino: {dt(m.trained_at)} · hash dos dados: <span className="font-mono">{m.data_hash.slice(0, 12)}</span></div>
              <div className="mt-1 text-xs">
                {Object.entries(m.metrics).map(([k, v]) => `${k}: ${typeof v === "number" ? fmtNum(v) : String(v)}`).join(" · ")}
              </div>
              <div className="mt-1 text-xs text-amber-800">{m.synthetic_notice}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function Audit() {
  const { data, loading, error } = useAsync(() => api.audit({ limit: 20 }), []);
  return (
    <Card title="Trilha de auditoria (somente auditor)">
      <Status loading={loading} error={error} />
      {data && data.items.length === 0 && <p className="text-sm text-slate-500">Nenhum evento registrado.</p>}
      {data && data.items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Quando</th><th>Quem</th><th>Ação</th><th>Cliente</th><th>Antes → Depois</th></tr></thead>
            <tbody>
              {data.items.map((a) => (
                <tr key={a.id} className="border-t border-slate-100 align-top">
                  <td className="py-2">{dt(a.occurred_at)}</td>
                  <td>{a.actor} <span className="text-xs text-slate-500">({a.actor_role})</span></td>
                  <td>{a.action}</td>
                  <td className="font-mono text-azul">{a.entity_id}</td>
                  <td className="font-mono text-xs">{JSON.stringify(a.before)} → {JSON.stringify(a.after)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export function HealthPage() {
  const { principal } = useAuth();
  return (
    <div className="space-y-4">
      <Notice>Métricas de modelo e qualidade referem-se a <strong>dados sintéticos</strong>; não indicam desempenho em produção.</Notice>
      <Runs />
      <div className="grid gap-4 lg:grid-cols-2"><Quality /><Drift /></div>
      <Models />
      {principal?.role === "auditor"
        ? <Audit />
        : <Notice tone="warn">A trilha de auditoria está disponível apenas para o perfil auditor.</Notice>}
    </div>
  );
}
