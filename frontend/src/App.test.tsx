import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { AuthProvider, parseToken, type Role } from "./auth";
import { setToken } from "./api/client";
import { groupByProfile } from "./pages/ValueRiskPage";
import type { Customer } from "./api/client";

const customer = (over: Partial<Customer> = {}): Customer => ({
  customer_id: "C000001", trips_12m: 5, spend_12m_brl: 1000, avg_ticket_brl: 200, recency_days: 10, preferred_route: "GRU-SSA",
  value_score: 50, segment: "Frequente", recommended_action: "x", points_balance: 100, margin_12m_brl: 300, disruptions_12m: 1,
  complaints_12m: 0, hvs_clv: 60, hvs_margin: 50, hvs_stability: 40, hvs_cost_to_serve: 20, hvs: 55, profile: "C", risk_score: 45,
  risk_drivers: "atraso medio elevado", nba_action: "Oferta de resgate de pontos", nba_expected_margin_brl: 80, nba_requires_approval: true, ...over,
});

const kpis = {
  synthetic_data: true, notice: "Dados sinteticos gerados para o desafio.", total_customers: 1200, avg_hvs: 53.4, avg_risk_score: 29.6,
  risk_threshold: 40, high_risk_customers: 89, spend_12m_at_risk_brl: 500000, nba_expected_margin_brl: 900000, nba_pending_approval: 282,
  avg_route_ivr: 18.2, profiles: [{ key: "A", customers: 268 }, { key: "B", customers: 258 }], segments: [{ key: "Frequente", customers: 700 }],
};

const route = { route: "GRU-SSA", flights: 10, disrupted_flights: 2, avg_delay_minutes: 5, complaints: 1, revenue_brl: 1000, ivr: 20 };
const SECRET_TOKEN_MARK = "sig-nao-vazar";

function makeToken(role: Role, over: Record<string, unknown> = {}, sub = "ana.teste") {
  const b64 = (o: unknown) => btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  const exp = Math.floor(Date.now() / 1000) + 3600;
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64({ sub, role, iss: "ancora-azul", iat: exp - 3600, exp, ...over })}.${SECRET_TOKEN_MARK}`;
}

type Call = { method: string; path: string; auth?: string; body?: string };
let calls: Call[] = [];

function mockApi(opts: { status?: number; detail?: string } = {}) {
  calls = [];
  vi.stubGlobal("fetch", vi.fn((url: URL, init?: RequestInit) => {
    const p = url.pathname;
    const headers = (init?.headers ?? {}) as Record<string, string>;
    calls.push({ method: init?.method ?? "GET", path: p, auth: headers.Authorization, body: init?.body as string | undefined });
    if (opts.status) return Promise.resolve({ ok: false, status: opts.status, json: () => Promise.resolve({ detail: opts.detail ?? "erro" }) } as Response);
    const body =
      p === "/kpis" ? kpis
      : p === "/rotas" ? { total: 1, limit: 10, offset: 0, items: [route] }
      : p === "/nba/aprovacoes" ? []
      : p.startsWith("/nba/") && init?.method === "POST" ? { audit_id: 1, occurred_at: "2026-01-01T00:00:00Z", customer_id: "C000001", decision: "approve", before: {}, after: {} }
      : p === "/nba" ? {
          total: 1, limit: 15, offset: 0, human_approval_notice: "Acoes com custo acima do limite exigem aprovacao humana.",
          summary: [{ nba_action: "Oferta de resgate de pontos", customers: 1, expected_margin_brl: 80, pending_approval: 1 }],
          items: [{ customer_id: "C000001", profile: "C", segment: "Frequente", hvs: 55, risk_score: 45, nba_action: "Oferta de resgate de pontos", nba_expected_margin_brl: 80, nba_requires_approval: true }],
        }
      : p === "/ops/runs" ? [{ run_id: "abcdef123456", started_at: "2026-01-01T00:00:00Z", finished_at: "2026-01-01T00:00:05Z", duration_ms: 5000, status: "passed", code_version: "62647e0abc", seed: 20261014, contract_version: "1.1.0", rows_by_entity: { customers: 1200 }, error: null }]
      : p === "/ops/quality" ? { run_id: "abcdef123456", total_rules: 105, failed_rules: 1, results: [{ entity: "customers", rule: "hvs_range", passed: false, failed_rows: 3 }, { entity: "customers", rule: "ok", passed: true, failed_rows: 0 }] }
      : p === "/ops/drift" ? { run_id: "abcdef123456", computed_at: "2026-01-01T00:00:00Z", alerts: 1, items: [{ feature: "hvs", psi: 0.31, threshold: 0.25, alert: true }] }
      : p === "/ops/models" ? [{ model_name: "hvs", model_version: "1", run_id: "abcdef123456", trained_at: "2026-01-01T00:00:00Z", data_hash: "0123456789abcdef", metrics: { roc_auc: 0.58 }, params: {}, synthetic_notice: "Metricas sobre dados sinteticos." }]
      : p === "/audit" ? { total: 1, limit: 20, offset: 0, items: [{ id: 1, occurred_at: "2026-01-01T00:00:00Z", actor: "maria.gestora", actor_role: "gestor", action: "nba.approve", entity: "nba_recommendation", entity_id: "C000001", before: { status: "pending" }, after: { status: "approved" }, request_id: null }] }
      : p.startsWith("/clientes/") ? customer()
      : { total: 1, limit: 15, offset: 0, items: [customer()] };
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) } as Response);
  }));
}

function renderAs(role: Role | null, token = role ? makeToken(role) : undefined) {
  if (token) sessionStorage.setItem("ancora.token", token);
  return render(<AuthProvider><App /></AuthProvider>);
}

beforeEach(() => { sessionStorage.clear(); setToken(undefined); });
afterEach(() => vi.unstubAllGlobals());

describe("login", () => {
  it("sem token mostra a tela de entrada e nao chama a API", () => {
    mockApi();
    renderAs(null);
    expect(screen.getByText("Entrar com token de acesso")).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("rejeita token malformado, com role invalida ou expirado", async () => {
    mockApi();
    renderAs(null);
    for (const bad of ["abc", makeToken("gestor", { role: "root" }), makeToken("gestor", { exp: 1 })]) {
      await userEvent.clear(screen.getByLabelText("Token (JWT)")); await userEvent.click(screen.getByLabelText("Token (JWT)"));
      await userEvent.paste(bad);
      await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
      expect(await screen.findByRole("alert")).toBeInTheDocument();
    }
    expect(calls).toHaveLength(0);
    expect(sessionStorage.getItem("ancora.token")).toBeNull();
  });

  it("entra com token valido, mostra usuario/perfil e envia Authorization sem expor o token na URL", async () => {
    mockApi();
    renderAs(null);
    await userEvent.click(screen.getByLabelText("Token (JWT)"));
    await userEvent.paste(makeToken("analista"));
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Dados sinteticos gerados para o desafio.")).toBeInTheDocument();
    expect(screen.getByText("analista")).toBeInTheDocument();
    expect(calls.every((c) => c.auth?.startsWith("Bearer "))).toBe(true);
    expect(calls.some((c) => c.path.includes(SECRET_TOKEN_MARK))).toBe(false);
  });

  it("401 da API encerra a sessao e volta ao login com aviso", async () => {
    mockApi({ status: 401, detail: "Token invalido" });
    renderAs("gestor");
    expect(await screen.findByText(/Sessão encerrada/)).toBeInTheDocument();
    expect(sessionStorage.getItem("ancora.token")).toBeNull();
  });

  it("sair limpa o token", async () => {
    mockApi();
    renderAs("gestor");
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(screen.getByText("Entrar com token de acesso")).toBeInTheDocument();
    expect(sessionStorage.getItem("ancora.token")).toBeNull();
  });

  it("parseToken le sub/role/exp e recusa lixo", () => {
    expect(parseToken(makeToken("auditor"))).toMatchObject({ sub: "ana.teste", role: "auditor" });
    expect(parseToken("a.b.c")).toBeNull();
    expect(parseToken(makeToken("gestor", { role: "admin" }))).toBeNull();
  });
});

describe("App", () => {
  it("mostra a visao executiva com aviso de dados sinteticos e KPIs da API", async () => {
    mockApi();
    renderAs("analista");
    expect(await screen.findByText("Dados sinteticos gerados para o desafio.")).toBeInTheDocument();
    expect(screen.getByText("1.200")).toBeInTheDocument();
    expect(screen.getAllByTestId("chart").length).toBeGreaterThanOrEqual(3);
  });

  it("exibe as cinco abas do dashboard", async () => {
    mockApi();
    renderAs("analista");
    for (const name of ["Executivo", "Proteger (Radar)", "Crescer (NBA)", "Rotas (IVR)", "Saúde da plataforma"]) {
      expect(await screen.findByRole("button", { name })).toBeInTheDocument();
    }
  });

  it("aba Rotas lista rotas por IVR", async () => {
    mockApi();
    renderAs("analista");
    await userEvent.click(screen.getByRole("button", { name: "Rotas (IVR)" }));
    expect(await screen.findByText("Top 15 rotas por IVR (%)")).toBeInTheDocument();
    expect(await screen.findByRole("cell", { name: "GRU-SSA" })).toBeInTheDocument();
  });

  it("aba Proteger abre o perfil com a explicacao do HVS e do risco", async () => {
    mockApi();
    renderAs("analista");
    await userEvent.click(screen.getByRole("button", { name: "Proteger (Radar)" }));
    await userEvent.click((await screen.findAllByText("C000001"))[0]);
    expect(await screen.findByText(/Por que este HVS/)).toBeInTheDocument();
    expect(screen.getByText("atraso medio elevado")).toBeInTheDocument();
  });

  it("mostra erro quando a API falha (nao-401)", async () => {
    mockApi({ status: 503, detail: "Banco indisponivel" });
    renderAs("gestor");
    await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThan(0));
    expect(screen.getAllByRole("alert")[0]).toHaveTextContent("Banco indisponivel");
  });
});

describe("Crescer: aprovacao", () => {
  async function openNba(role: Role) {
    mockApi();
    renderAs(role);
    await userEvent.click(screen.getByRole("button", { name: "Crescer (NBA)" }));
    expect(await screen.findByText(/Aprovação humana obrigatória/)).toBeInTheDocument();
    expect(await screen.findByText("Requer aprovação")).toBeInTheDocument();
  }

  it("analista ve o aviso mas nao tem botoes nem consulta decisoes", async () => {
    await openNba("analista");
    expect(screen.queryByRole("button", { name: "Aprovar" })).toBeNull();
    expect(calls.some((c) => c.path === "/nba/aprovacoes")).toBe(false);
  });

  it("auditor consulta decisoes mas nao decide", async () => {
    await openNba("auditor");
    expect(screen.queryByRole("button", { name: "Aprovar" })).toBeNull();
    await waitFor(() => expect(calls.some((c) => c.path === "/nba/aprovacoes")).toBe(true));
  });

  it("gestor aprova com justificativa obrigatoria e o POST leva token e corpo corretos", async () => {
    await openNba("gestor");
    await userEvent.click(screen.getByRole("button", { name: "Aprovar" }));
    const confirm = screen.getByRole("button", { name: "Confirmar" });
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Justificativa/), "Dentro do orcamento");
    await userEvent.click(confirm);
    expect(await screen.findByText(/Decisão registrada para C000001/)).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST")!;
    expect(post.path).toBe("/nba/C000001/aprovacao");
    expect(post.auth).toMatch(/^Bearer /);
    expect(JSON.parse(post.body!)).toEqual({ decision: "approve", reason: "Dentro do orcamento" });
  });
});

describe("Saude da plataforma", () => {
  async function openHealth(role: Role) {
    mockApi();
    renderAs(role);
    await userEvent.click(screen.getByRole("button", { name: "Saúde da plataforma" }));
    expect(await screen.findByText("Execuções do pipeline")).toBeInTheDocument();
  }

  it("mostra execucoes, qualidade, drift e modelos com ressalva sintetica", async () => {
    await openHealth("analista");
    expect(await screen.findByText("hvs_range")).toBeInTheDocument();
    expect(await screen.findByText(/1 feature\(s\) acima do limiar/)).toBeInTheDocument();
    expect(await screen.findByText("Metricas sobre dados sinteticos.")).toBeInTheDocument();
    expect(screen.getByText("passed")).toBeInTheDocument();
  });

  it("auditoria so aparece para o auditor (e nao consulta /audit para os demais)", async () => {
    await openHealth("gestor");
    expect(screen.getByText(/apenas para o perfil auditor/)).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/audit")).toBe(false);
  });

  it("auditor ve a trilha com antes e depois", async () => {
    await openHealth("auditor");
    expect(await screen.findByText("maria.gestora")).toBeInTheDocument();
    expect(screen.getByText(/"pending"/)).toBeInTheDocument();
  });
});

describe("groupByProfile", () => {
  it("agrupa por perfil A-E mantendo ordem", () => {
    const g = groupByProfile([customer({ profile: "A" }), customer({ profile: "E" }), customer({ profile: "A" })]);
    expect(g.map((x) => x.length)).toEqual([2, 0, 0, 0, 1]);
  });
});
