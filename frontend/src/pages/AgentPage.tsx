import { useCallback, useEffect, useRef, useState } from "react";
import { api, streamSse, type AgentCitation, type AgentMeta, type GuardrailReport, type Proposal, type ProposedAction, type SseEvent } from "../api/client";
import { useAuth } from "../auth";
import { Card, Notice } from "../components/ui";
import { fmtBRL as brl } from "../format";

export const SimulatedBadge = () => (
  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-amber-800 ring-1 ring-amber-300">simulado</span>
);

const GUARD_TONE = { passed: "bg-emerald-100 text-emerald-800", fallback: "bg-amber-100 text-amber-800", blocked: "bg-red-100 text-red-800" } as const;
const GUARD_LABEL = { passed: "Guardrails: aprovado", fallback: "Guardrails: fallback por regras", blocked: "Guardrails: bloqueado" } as const;

export function GuardrailStatus({ report }: { report: GuardrailReport }) {
  return (
    <div className="space-y-1 text-sm" data-testid="guardrails">
      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${GUARD_TONE[report.status]}`}>{GUARD_LABEL[report.status]}</span>
      {report.input_flags.length > 0 && <div className="text-xs text-slate-600">Entrada: {report.input_flags.join(", ")}</div>}
      {report.output_violations.length > 0 && <div className="text-xs text-red-700">Violações: {report.output_violations.join(", ")}</div>}
      {report.checks.length > 0 && <div className="text-xs text-slate-500">Verificações: {report.checks.join(", ")}</div>}
    </div>
  );
}

// So links https viram <a>; qualquer outro esquema aparece como texto.
export function SourceList({ sources }: { sources: Pick<AgentCitation, "ref" | "url" | "title" | "version" | "consulted_at">[] }) {
  if (!sources.length) return <p className="text-sm text-slate-500">Nenhuma fonte citada.</p>;
  return (
    <ol className="space-y-1 text-sm">
      {sources.map((s) => (
        <li key={`${s.ref}-${s.url}`}>
          [{s.ref}] {s.url.startsWith("https://") ? <a className="text-azul underline" href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a> : s.title}
          <span className="text-xs text-slate-500"> · v{s.version} · consultada em {s.consulted_at}</span>
        </li>
      ))}
    </ol>
  );
}

interface AnswerState {
  text: string;
  meta?: AgentMeta;
  guardrails?: GuardrailReport;
  sources: AgentCitation[];
  action?: ProposedAction;
  proposal?: Proposal;
  done: boolean;
}

const EMPTY: AnswerState = { text: "", sources: [], done: false };

export function AgentPanel() {
  const { principal } = useAuth();
  const canAsk = principal?.role === "analista" || principal?.role === "gestor";
  const [question, setQuestion] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [state, setState] = useState<AnswerState>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const abort = useRef<AbortController | undefined>(undefined);

  useEffect(() => () => abort.current?.abort(), []);

  const apply = useCallback((e: SseEvent) => {
    const d = e.data as never;
    setState((s) => {
      switch (e.event) {
        case "meta": return { ...s, meta: d };
        case "guardrails": return { ...s, guardrails: d };
        case "sources": return { ...s, sources: d };
        case "proposed_action": return { ...s, action: d };
        case "delta": return { ...s, text: s.text + (d as { text: string }).text };
        case "proposal": return { ...s, proposal: d };
        case "done": return { ...s, done: true };
        default: return s;
      }
    });
  }, []);

  const run = async (path: string, body?: unknown) => {
    abort.current?.abort();
    const ctl = new AbortController();
    abort.current = ctl;
    setBusy(true); setError(undefined); setState(EMPTY);
    try {
      await streamSse("POST", path, apply, { body, signal: ctl.signal });
    } catch (e) {
      if (!ctl.signal.aborted) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (abort.current === ctl) setBusy(false);
    }
  };

  const idOk = /^C\d{6}$/.test(customerId.trim());
  const input = "rounded-md border border-slate-300 px-3 py-1.5 text-sm";
  const btn = "rounded-md bg-azul px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40";

  return (
    <Card title="Agente de retenção (simulado)">
      <div className="mb-3 flex items-center gap-2"><SimulatedBadge /><span className="text-xs text-slate-500">O agente só propõe: nenhuma ativação ocorre sem aprovação humana.</span></div>
      {!canAsk ? <Notice>Seu perfil ({principal?.role}) pode acompanhar a fila, mas não consultar o agente.</Notice> : (
        <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); void run("/agente/perguntar", { question: question.trim() }); }}>
          <label className="block text-sm text-slate-600" htmlFor="agent-question">Pergunta</label>
          <textarea id="agent-question" className={`${input} w-full`} rows={2} maxLength={500} value={question} onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ex.: Qual a melhor ação para C000001 considerando os níveis do programa?" />
          <div className="flex flex-wrap items-center gap-2">
            <button className={btn} type="submit" disabled={busy || question.trim().length < 3}>Perguntar</button>
            <input aria-label="ID do cliente" className={`${input} w-32`} placeholder="C000001" value={customerId} onChange={(e) => setCustomerId(e.target.value)} />
            <button className={btn} type="button" disabled={busy || !idOk} onClick={() => void run(`/nba/${customerId.trim()}/proposta`)}>Gerar proposta para aprovação</button>
          </div>
        </form>
      )}
      {error && <div role="alert" className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {busy && !state.text && <div role="status" className="mt-3 text-sm text-slate-500">Consultando o agente…</div>}
      {(state.text || state.guardrails) && (
        <div className="mt-4 space-y-3" aria-live="polite">
          <div className="flex flex-wrap items-center gap-2">
            {state.meta?.simulated !== false && <SimulatedBadge />}
            {state.meta && <span className="text-xs text-slate-500">provider: {state.meta.provider}{state.meta.fallback_used ? ` (fallback: ${state.meta.fallback_reason})` : ""}</span>}
          </div>
          <p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm" data-testid="agent-answer">{state.text}</p>
          {state.action && (
            <div className="text-sm" data-testid="proposed-action">Ação proposta: <strong>{state.action.action}</strong> · margem esperada {brl(state.action.expected_margin_brl)} · <em>requer aprovação humana</em></div>
          )}
          {state.proposal && <Notice>Proposta registrada como <strong>{state.proposal.status === "pending" ? "pendente" : state.proposal.status}</strong> e enviada à fila de aprovação.</Notice>}
          {state.guardrails && <GuardrailStatus report={state.guardrails} />}
          <div><h3 className="mb-1 text-xs font-semibold uppercase text-slate-500">Fontes citadas</h3>{state.done || state.sources.length ? <SourceList sources={state.sources} /> : null}</div>
        </div>
      )}
    </Card>
  );
}

const RECONNECT_MS = 1500;

export function ApprovalQueue() {
  const { principal } = useAuth();
  const isManager = principal?.role === "gestor";
  const [items, setItems] = useState<Proposal[]>([]);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string>();
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string>();

  useEffect(() => {
    const ctl = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const connect = async () => {
      try {
        setLive(true);
        await streamSse("GET", "/propostas/fila/stream", (e) => {
          if (e.event === "queue") { setItems((e.data as { items: Proposal[] }).items); setError(undefined); }
          else if (e.event === "error") setError((e.data as { detail: string }).detail);
        }, { signal: ctl.signal });
      } catch (e) {
        if (ctl.signal.aborted) return;
        setError(e instanceof Error ? e.message : String(e));
      }
      setLive(false);
      if (!ctl.signal.aborted) timer = setTimeout(() => void connect(), RECONNECT_MS);
    };
    void connect();
    return () => { ctl.abort(); clearTimeout(timer); };
  }, []);

  const decide = async (p: Proposal, decision: "approve" | "reject") => {
    setBusyId(p.proposal_id); setError(undefined);
    try {
      await api.decideProposal(p.proposal_id, decision, reasons[p.proposal_id] ?? "");
      setItems((cur) => cur.filter((i) => i.proposal_id !== p.proposal_id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyId(undefined);
    }
  };

  return (
    <Card title="Fila de aprovação de propostas do agente">
      <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
        <SimulatedBadge />
        <span role="status">{live ? "● Tempo real" : "○ Reconectando…"}</span>
        <span>{items.length} pendente(s)</span>
      </div>
      {!isManager && <div className="mb-3"><Notice>Somente o perfil gestor decide propostas.</Notice></div>}
      {error && <div role="alert" className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {items.length === 0 ? <p className="text-sm text-slate-500">Nenhuma proposta pendente.</p> : (
        <ul className="space-y-3">
          {items.map((p) => {
            const reason = reasons[p.proposal_id] ?? "";
            const valid = reason.trim().length >= 5;
            return (
              <li key={p.proposal_id} className="rounded-lg border border-slate-200 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2"><strong>{p.customer_id}</strong><span>{p.action}</span><span className="text-slate-500">margem {brl(p.expected_margin_brl)}</span>{p.simulated && <SimulatedBadge />}</div>
                <div className="mt-1 text-xs text-slate-500">por {p.requested_by} · {new Date(p.created_at).toLocaleString("pt-BR")}</div>
                <details className="mt-2"><summary className="cursor-pointer text-xs text-azul">Justificativa e fontes</summary>
                  <p className="mt-1 whitespace-pre-wrap text-xs">{p.rationale}</p>
                  <div className="mt-1"><SourceList sources={p.sources} /></div>
                </details>
                {isManager && (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <input aria-label={`Justificativa para ${p.customer_id}`} className="min-w-64 flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm" maxLength={500} placeholder="Justificativa (5–500 caracteres, sem dados pessoais)"
                      value={reason} onChange={(e) => setReasons((r) => ({ ...r, [p.proposal_id]: e.target.value }))} />
                    <button className="rounded-md bg-emerald-600 px-3 py-1 text-white disabled:opacity-40" disabled={!valid || busyId === p.proposal_id} onClick={() => void decide(p, "approve")}>Aprovar</button>
                    <button className="rounded-md bg-red-600 px-3 py-1 text-white disabled:opacity-40" disabled={!valid || busyId === p.proposal_id} onClick={() => void decide(p, "reject")}>Rejeitar</button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

export function AgentPage() {
  return (
    <div className="space-y-6">
      <AgentPanel />
      <ApprovalQueue />
    </div>
  );
}
