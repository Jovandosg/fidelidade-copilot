import type { components } from "./schema";

export type Kpis = components["schemas"]["Kpis"];
export type Customer = components["schemas"]["CustomerFeature"];
export type CustomerPage = components["schemas"]["CustomerPage"];
export type RoutePage = components["schemas"]["RoutePage"];
export type NbaPage = components["schemas"]["NbaPage"];
export type PipelineRun = components["schemas"]["PipelineRunOut"];
export type Quality = components["schemas"]["QualityOut"];
export type ModelInfo = components["schemas"]["ModelOut"];
export type DriftReport = components["schemas"]["DriftReport"];
export type AuditPage = components["schemas"]["AuditPage"];
export type ApprovalStatus = components["schemas"]["ApprovalStatus"];
export type ApprovalResult = components["schemas"]["ApprovalResult"];
export type Decision = components["schemas"]["ApprovalRequest"]["decision"];

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const MAX_LIMIT = 200;

type Params = Record<string, string | number | boolean | undefined>;

// O token fica so em memoria (e sessionStorage, gerido por auth.tsx); nunca vai para URL, log ou localStorage.
let token: string | undefined;
let onUnauthorized: (() => void) | undefined;

export const setToken = (t: string | undefined) => { token = t; };
export const setUnauthorizedHandler = (fn: (() => void) | undefined) => { onUnauthorized = fn; };

async function request<T>(method: "GET" | "POST", path: string, opts: { params?: Params; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  const url = new URL(path, API_URL);
  for (const [k, v] of Object.entries(opts.params ?? {})) if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(url, { method, headers, signal: opts.signal, body: opts.body === undefined ? undefined : JSON.stringify(opts.body) });
  if (!res.ok) {
    if (res.status === 401) onUnauthorized?.();
    const detail = await res.json().then((j) => (typeof j.detail === "string" ? j.detail : "")).catch(() => "");
    throw new Error(`Erro ${res.status} ao consultar ${path}${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export type SseEvent = { event: string; data: unknown };

export function parseSseBlock(block: string): SseEvent | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue;
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (!data.length) return null;
  try { return { event, data: JSON.parse(data.join("\n")) }; } catch { return null; }
}

// EventSource nao envia Authorization: le o stream via fetch para manter o JWT no header (nunca na URL).
export async function streamSse(method: "GET" | "POST", path: string, onEvent: (e: SseEvent) => void, opts: { body?: unknown; signal?: AbortSignal } = {}): Promise<void> {
  const headers: Record<string, string> = { Accept: "text/event-stream" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(new URL(path, API_URL), { method, headers, signal: opts.signal, body: opts.body === undefined ? undefined : JSON.stringify(opts.body) });
  if (!res.ok || !res.body) {
    if (res.status === 401) onUnauthorized?.();
    const detail = await res.json().then((j) => (typeof j.detail === "string" ? j.detail : "")).catch(() => "");
    throw new Error(`Erro ${res.status} ao consultar ${path}${detail ? `: ${detail}` : ""}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    buf += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const ev = parseSseBlock(buf.slice(0, i));
      buf = buf.slice(i + 2);
      if (ev) onEvent(ev);
    }
    if (done) break;
  }
}

export type AgentCitation = { ref: number; url: string; title: string; version: number; consulted_at: string; section: string; score: number };
export type GuardrailReport = { status: "passed" | "fallback" | "blocked"; input_flags: string[]; output_violations: string[]; checks: string[] };
export type ProposedAction = { customer_id: string; action: string; expected_margin_brl: number; requires_approval: true };
export type AgentMeta = { simulated: boolean; notice: string; provider: "rules" | "llm"; fallback_used: boolean; fallback_reason: string | null; tools_used: string[] };
export type Proposal = {
  proposal_id: string; created_at: string; customer_id: string; action: string; expected_margin_brl: number; rationale: string; sources: AgentCitation[];
  guardrails: Partial<GuardrailReport>; provider: "rules" | "llm"; simulated: boolean; status: "pending" | "approved" | "rejected"; requested_by: string;
  decided_by: string | null; decided_at: string | null; decision_reason: string | null;
};

export const get = <T>(path: string, params: Params = {}, signal?: AbortSignal) => request<T>("GET", path, { params, signal });

export const api = {
  kpis: (params: Params = {}) => get<Kpis>("/kpis", params),
  customers: (params: Params = {}) => get<CustomerPage>("/clientes", params),
  customer: (id: string) => get<Customer>(`/clientes/${encodeURIComponent(id)}`),
  routes: (params: Params = {}) => get<RoutePage>("/rotas", params),
  nba: (params: Params = {}) => get<NbaPage>("/nba", params),
  runs: (limit = 10) => get<PipelineRun[]>("/ops/runs", { limit }),
  quality: () => get<Quality>("/ops/quality"),
  models: () => get<ModelInfo[]>("/ops/models"),
  drift: () => get<DriftReport>("/ops/drift"),
  audit: (params: Params = {}) => get<AuditPage>("/audit", params),
  approvals: () => get<ApprovalStatus[]>("/nba/aprovacoes"),
  decide: (customerId: string, decision: Decision, reason: string) =>
    request<ApprovalResult>("POST", `/nba/${encodeURIComponent(customerId)}/aprovacao`, { body: { decision, reason } }),
  decideProposal: (id: string, decision: Decision, reason: string) =>
    request<Proposal>("POST", `/propostas/${encodeURIComponent(id)}/decisao`, { body: { decision, reason } }),
  // A API limita a pagina a 200 itens; percorre as paginas para o mapa valor x risco.
  async allCustomers(cap = 2000): Promise<Customer[]> {
    const first = await get<CustomerPage>("/clientes", { limit: MAX_LIMIT, offset: 0 });
    const items = [...first.items];
    for (let offset = MAX_LIMIT; offset < Math.min(first.total, cap); offset += MAX_LIMIT) {
      items.push(...(await get<CustomerPage>("/clientes", { limit: MAX_LIMIT, offset })).items);
    }
    return items;
  },
};
