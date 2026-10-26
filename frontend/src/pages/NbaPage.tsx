import { useState } from "react";
import { api, type ApprovalStatus, type Decision } from "../api/client";
import { useAuth } from "../auth";
import { Chart } from "../components/Chart";
import { Card, Notice, Pager, Status } from "../components/ui";
import { fmtBRL, fmtNum } from "../format";
import { useAsync } from "../useAsync";

const LIMIT = 15;
const LABEL: Record<Decision, string> = { approve: "Aprovada", reject: "Rejeitada" };

export function NbaPage({ onSelect }: { onSelect: (id: string) => void }) {
  const { principal } = useAuth();
  const canDecide = principal?.role === "gestor";
  const canSeeDecisions = principal?.role === "gestor" || principal?.role === "auditor";

  const [approval, setApproval] = useState<"" | "true" | "false">("");
  const [offset, setOffset] = useState(0);
  const [version, setVersion] = useState(0);
  const [draft, setDraft] = useState<{ id: string; decision: Decision }>();
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string>();
  const [saved, setSaved] = useState<string>();

  const { data, loading, error } = useAsync(
    () => api.nba({ limit: LIMIT, offset, requires_approval: approval === "" ? undefined : approval === "true" }),
    [approval, offset],
  );
  const decisions = useAsync<ApprovalStatus[]>(() => (canSeeDecisions ? api.approvals() : Promise.resolve([])), [canSeeDecisions, version]);
  const byCustomer = new Map((decisions.data ?? []).map((d) => [d.customer_id, d]));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft) return;
    setSaving(true);
    setSaveError(undefined);
    try {
      await api.decide(draft.id, draft.decision, reason.trim());
      setSaved(`Decisão registrada para ${draft.id} (${LABEL[draft.decision].toLowerCase()}) na trilha de auditoria.`);
      setDraft(undefined);
      setReason("");
      setVersion((v) => v + 1);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <Notice tone="warn">
        <strong>Aprovação humana obrigatória:</strong>{" "}
        {data?.human_approval_notice ?? "ações com custo acima do limite só podem ser executadas após aprovação de uma pessoa."}{" "}
        As ações abaixo são sugestões geradas por regras sobre dados sintéticos; nenhuma é executada automaticamente.
        {" "}{canDecide ? "Cada decisão é registrada na trilha de auditoria com seu usuário." : "Apenas o perfil gestor pode aprovar ou rejeitar."}
      </Notice>
      {saved && <div role="status" className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">{saved}</div>}
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
          {draft && (
            <Card title={`${draft.decision === "approve" ? "Aprovar" : "Rejeitar"} ação para ${draft.id}`}>
              <form onSubmit={submit} className="space-y-2">
                <label className="block text-sm">
                  <span className="mb-1 block text-slate-600">Justificativa (5–500 caracteres; não inclua dados pessoais)</span>
                  <textarea
                    value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} rows={2} required minLength={5}
                    className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                  />
                </label>
                {saveError && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-2 text-sm text-red-700">{saveError}</div>}
                <div className="flex gap-2">
                  <button type="submit" disabled={saving || reason.trim().length < 5} className="rounded-full bg-azul px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40">Confirmar</button>
                  <button type="button" onClick={() => { setDraft(undefined); setSaveError(undefined); }} className="rounded-full px-4 py-1.5 text-sm text-slate-600 ring-1 ring-slate-300">Cancelar</button>
                </div>
              </form>
            </Card>
          )}
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
            {decisions.error && <div role="alert" className="mb-2 text-sm text-red-700">{decisions.error}</div>}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr><th className="py-2">Cliente</th><th>Perfil</th><th>Risco</th><th>Ação sugerida</th><th>Margem esperada</th><th>Aprovação</th></tr>
                </thead>
                <tbody>
                  {data.items.map((n) => {
                    const d = byCustomer.get(n.customer_id);
                    return (
                      <tr key={n.customer_id} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50" onClick={() => onSelect(n.customer_id)}>
                        <td className="py-2 font-mono text-azul">{n.customer_id}</td>
                        <td>{n.profile}</td>
                        <td>{fmtNum(n.risk_score)}</td>
                        <td className="max-w-md truncate" title={n.nba_action}>{n.nba_action}</td>
                        <td>{fmtBRL(n.nba_expected_margin_brl)}</td>
                        <td onClick={(e) => e.stopPropagation()}>
                          {!n.nba_requires_approval ? "—" : d ? (
                            <span
                              className={`rounded px-2 py-0.5 text-xs font-medium ${d.decision === "approve" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}
                              title={`por ${d.actor} em ${new Date(d.occurred_at).toLocaleString("pt-BR")}`}
                            >
                              {LABEL[d.decision]}
                            </span>
                          ) : (
                            <span className="flex items-center gap-2">
                              <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">Requer aprovação</span>
                              {canDecide && (
                                <>
                                  <button className="text-xs text-green-700 underline" onClick={() => { setDraft({ id: n.customer_id, decision: "approve" }); setSaved(undefined); }}>Aprovar</button>
                                  <button className="text-xs text-red-700 underline" onClick={() => { setDraft({ id: n.customer_id, decision: "reject" }); setSaved(undefined); }}>Rejeitar</button>
                                </>
                              )}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
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
