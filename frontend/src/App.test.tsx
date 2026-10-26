import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
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

function mockApi() {
  vi.stubGlobal("fetch", vi.fn((url: URL) => {
    const p = url.pathname;
    const body =
      p === "/kpis" ? kpis
      : p === "/rotas" ? { total: 1, limit: 10, offset: 0, items: [{ route: "GRU-SSA", flights: 10, disrupted_flights: 2, avg_delay_minutes: 5, complaints: 1, revenue_brl: 1000, ivr: 20 }] }
      : p === "/nba" ? {
          total: 1, limit: 15, offset: 0, human_approval_notice: "Acoes com custo acima do limite exigem aprovacao humana.",
          summary: [{ nba_action: "Oferta de resgate de pontos", customers: 1, expected_margin_brl: 80, pending_approval: 1 }],
          items: [{ customer_id: "C000001", profile: "C", segment: "Frequente", hvs: 55, risk_score: 45, nba_action: "Oferta de resgate de pontos", nba_expected_margin_brl: 80, nba_requires_approval: true }],
        }
      : p.startsWith("/clientes/") ? customer()
      : { total: 1, limit: 15, offset: 0, items: [customer()] };
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) } as Response);
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("mostra a visao executiva com aviso de dados sinteticos e KPIs da API", async () => {
    mockApi();
    render(<App />);
    expect(await screen.findByText("Dados sinteticos gerados para o desafio.")).toBeInTheDocument();
    expect(screen.getByText("1.200")).toBeInTheDocument();
    expect(screen.getAllByTestId("chart").length).toBeGreaterThanOrEqual(3);
  });

  it("aba NBA exibe aviso de aprovacao humana e marca acoes que exigem aprovacao", async () => {
    mockApi();
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Próxima Melhor Ação" }));
    expect(await screen.findByText(/Aprovação humana obrigatória/)).toBeInTheDocument();
    expect(await screen.findByText("Requer aprovação")).toBeInTheDocument();
  });

  it("clicar numa linha da fila abre o perfil com a explicacao do HVS e do risco", async () => {
    mockApi();
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Fila de Risco" }));
    await userEvent.click(await screen.findByText("C000001"));
    expect(await screen.findByText(/Por que este HVS/)).toBeInTheDocument();
    expect(screen.getByText("atraso medio elevado")).toBeInTheDocument();
    expect(screen.getByText(/exige/)).toBeInTheDocument();
  });

  it("mostra erro quando a API falha", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({ detail: "Banco indisponivel" }) } as Response)));
    render(<App />);
    await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThan(0));
    expect(screen.getAllByRole("alert")[0]).toHaveTextContent("Banco indisponivel");
  });
});

describe("groupByProfile", () => {
  it("agrupa por perfil A-E mantendo ordem", () => {
    const g = groupByProfile([customer({ profile: "A" }), customer({ profile: "E" }), customer({ profile: "A" })]);
    expect(g.map((x) => x.length)).toEqual([2, 0, 0, 0, 1]);
  });
});
