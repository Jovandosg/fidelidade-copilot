import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, type Role } from "./auth";
import { parseSseBlock, setToken, streamSse } from "./api/client";
import { AgentPage, SourceList } from "./pages/AgentPage";

const enc = new TextEncoder();
const sse = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

// Entrega o corpo em pedacos arbitrarios para exercitar o parser de fronteiras de evento.
function streamBody(text: string, size = 17) {
  const chunks: Uint8Array[] = [];
  const bytes = enc.encode(text);
  for (let i = 0; i < bytes.length; i += size) chunks.push(bytes.slice(i, i + size));
  let i = 0;
  return { getReader: () => ({ read: () => Promise.resolve(i < chunks.length ? { done: false, value: chunks[i++] } : { done: true, value: undefined }) }) };
}

function makeToken(role: Role) {
  const b64 = (o: unknown) => btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  const exp = Math.floor(Date.now() / 1000) + 3600;
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64({ sub: "ana.teste", role, iss: "ancora-azul", iat: exp - 3600, exp })}.sig`;
}

const proposal = {
  proposal_id: "11111111-1111-1111-1111-111111111111", created_at: "2026-01-01T00:00:00Z", customer_id: "C000001", action: "Oferta de resgate de pontos", expected_margin_brl: 44,
  rationale: "Justificativa [1]", sources: [{ ref: 1, url: "https://www.voeazul.com.br/regras", title: "Regras publicas", version: 1, consulted_at: "2026-01-01", section: "s", score: 1 }],
  guardrails: { status: "passed" }, provider: "rules", simulated: true, status: "pending", requested_by: "ana", decided_by: null, decided_at: null, decision_reason: null,
};
const guard = { status: "passed", input_flags: [], output_violations: [], checks: ["schema", "citation"] };
const ANSWER = [
  sse("meta", { simulated: true, notice: "n", provider: "rules", fallback_used: false, fallback_reason: null, tools_used: [] }),
  sse("guardrails", guard), sse("sources", proposal.sources),
  sse("proposed_action", { customer_id: "C000001", action: "Oferta de resgate de pontos", expected_margin_brl: 44, requires_approval: true }),
  sse("delta", { text: "Recomendo oferta " }), sse("delta", { text: "conforme [1]." }), sse("done", {}),
].join("");

type Call = { method: string; path: string; auth?: string; body?: string };
let calls: Call[] = [];

function mockApi(queueItems: unknown[] = [proposal]) {
  calls = [];
  vi.stubGlobal("fetch", vi.fn((url: URL, init?: RequestInit) => {
    const headers = (init?.headers ?? {}) as Record<string, string>;
    calls.push({ method: init?.method ?? "GET", path: url.pathname, auth: headers.Authorization, body: init?.body as string | undefined });
    if (url.pathname === "/agente/perguntar" || url.pathname.endsWith("/proposta"))
      return Promise.resolve({ ok: true, status: 200, body: streamBody(ANSWER) } as unknown as Response);
    if (url.pathname === "/propostas/fila/stream") {
      const signal = init?.signal;
      let sent = false;
      const body = { getReader: () => ({ read: () => new Promise((resolve, reject) => {
        if ((signal as AbortSignal | undefined)?.aborted) return reject(new DOMException("abort", "AbortError"));
        if (!sent) { sent = true; return resolve({ done: false, value: enc.encode(sse("queue", { pending: queueItems.length, items: queueItems })) }); }
        signal?.addEventListener("abort", () => reject(new DOMException("abort", "AbortError")));
      }) }) };
      return Promise.resolve({ ok: true, status: 200, body } as unknown as Response);
    }
    if (url.pathname.endsWith("/decisao")) return Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve({ ...proposal, status: "approved" }) } as Response);
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ detail: "x" }) } as Response);
  }));
}

function renderAs(role: Role) {
  const t = makeToken(role);
  sessionStorage.setItem("ancora.token", t);
  setToken(t);
  return render(<AuthProvider><AgentPage /></AuthProvider>);
}

beforeEach(() => { sessionStorage.clear(); setToken(undefined); });
afterEach(() => vi.unstubAllGlobals());

describe("SSE client", () => {
  it("parses blocks, ignores comments and invalid JSON", () => {
    expect(parseSseBlock('event: delta\ndata: {"text":"a"}')).toEqual({ event: "delta", data: { text: "a" } });
    expect(parseSseBlock(": keepalive")).toBeNull();
    expect(parseSseBlock("event: x\ndata: {nao-json")).toBeNull();
  });

  it("reassembles events split across chunks and sends JWT only in the header", async () => {
    mockApi();
    setToken("tok-abc");
    const got: string[] = [];
    await streamSse("POST", "/agente/perguntar", (e) => got.push(e.event), { body: { question: "oi" } });
    expect(got).toEqual(["meta", "guardrails", "sources", "proposed_action", "delta", "delta", "done"]);
    expect(calls[0].auth).toBe("Bearer tok-abc");
  });
});

describe("Painel do agente", () => {
  it("streams the answer with simulated badge, sources and guardrail status", async () => {
    mockApi();
    renderAs("analista");
    await userEvent.type(screen.getByLabelText("Pergunta"), "Qual a melhor acao para C000001?");
    await userEvent.click(screen.getByRole("button", { name: "Perguntar" }));
    expect(await screen.findByTestId("agent-answer")).toHaveTextContent("Recomendo oferta conforme [1].");
    expect(screen.getByTestId("guardrails")).toHaveTextContent("Guardrails: aprovado");
    expect(screen.getByTestId("proposed-action")).toHaveTextContent(/requer aprovação humana/);
    expect(screen.getAllByText("simulado").length).toBeGreaterThan(1);
    const link = (await screen.findAllByRole("link", { name: "Regras publicas" }))[0];
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(calls.find((c) => c.path === "/agente/perguntar")?.body).toBe(JSON.stringify({ question: "Qual a melhor acao para C000001?" }));
  });

  it("validates the customer id before creating a proposal and calls the proposal endpoint", async () => {
    mockApi();
    renderAs("analista");
    const btn = screen.getByRole("button", { name: /Gerar proposta/ });
    expect(btn).toBeDisabled();
    await userEvent.type(screen.getByLabelText("ID do cliente"), "C000001");
    await userEvent.click(btn);
    await waitFor(() => expect(calls.some((c) => c.path === "/nba/C000001/proposta" && c.method === "POST")).toBe(true));
  });

  it("auditor cannot ask the agent but sees the live queue", async () => {
    mockApi();
    renderAs("auditor");
    expect(screen.queryByRole("button", { name: "Perguntar" })).not.toBeInTheDocument();
    expect(await screen.findByText("C000001")).toBeInTheDocument();
    expect(screen.getByText(/Somente o perfil gestor decide/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aprovar" })).not.toBeInTheDocument();
  });

  it("manager approves with a justification and the item leaves the queue", async () => {
    mockApi();
    renderAs("gestor");
    await screen.findByText("C000001");
    const approve = screen.getByRole("button", { name: "Aprovar" });
    expect(approve).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Justificativa para C000001"), "Dentro da politica");
    await userEvent.click(approve);
    await waitFor(() => expect(screen.getByText("Nenhuma proposta pendente.")).toBeInTheDocument());
    const post = calls.find((c) => c.path.endsWith("/decisao"));
    expect(post?.body).toBe(JSON.stringify({ decision: "approve", reason: "Dentro da politica" }));
  });
});

describe("SourceList", () => {
  it("only links https URLs", () => {
    render(<SourceList sources={[{ ref: 1, url: "javascript:alert(1)", title: "Ruim", version: 1, consulted_at: "2026-01-01" }]} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText(/Ruim/)).toBeInTheDocument();
  });
});
